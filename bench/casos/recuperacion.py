"""Recuperación de fichas liberadas: leerlas del disco vs tenerlas en memoria.

Reproduce lo que hace ControladorRed.resolver_catalogo (LRU -> disco), pero
con fichas sintéticas y sin red: PersistenciaCatalogo ya las tiene guardadas,
y la única diferencia entre variantes es si siguen en la ListaLRU o no.
"""
import tempfile
from bench.medicion import Fila, medir

FICHAS = 25
CAPACIDAD_MEMORIA = FICHAS   # entran todas: nunca hay que desalojar
CAPACIDAD_DISCO = 10         # Una caché pequeña obliga a recuperar del disco las fichas desalojadas.


def _fichas_sinteticas():
    return [(f"tipo_{i}", {"id": f"tipo_{i}", "nombre": f"Ficha {i}", "clase": "objeto"})
            for i in range(FICHAS)]


def _preparar_disco(carpeta):
    """Deja todas las fichas guardadas en disco, como tras resolver_catalogo desde la red."""
    from persistencia.catalogo import PersistenciaCatalogo
    pers = PersistenciaCatalogo(carpeta, "v1")
    for tipo_id, ficha in _fichas_sinteticas():
        pers.guardar_ficha(tipo_id, ficha)
    return pers


def _desde_memoria(pers, capacidad):
    """Llena una ListaLRU con espacio de sobra: las fichas siguen en memoria."""
    from estructuras.listalru import ListaLRU
    cache = ListaLRU(capacidad)
    for tipo_id, ficha in _fichas_sinteticas():
        cache.insertar(tipo_id, ficha)
    for tipo_id, _ in _fichas_sinteticas():
        cache.buscar(tipo_id)


def _desde_disco(pers, capacidad):
    """Con una LRU chica, las fichas más viejas ya fueron desalojadas y hay
    que recuperarlas de la caché persistente en disco."""
    from estructuras.listalru import ListaLRU
    cache = ListaLRU(capacidad)
    for tipo_id, ficha in _fichas_sinteticas():
        cache.insertar(tipo_id, ficha)
    for tipo_id, _ in _fichas_sinteticas():
        if cache.buscar(tipo_id) is None:
            cache.insertar(tipo_id, pers.cargar_ficha(tipo_id))


def correr():
    carpeta = tempfile.mkdtemp()
    pers = _preparar_disco(carpeta)
    return [
        Fila("recuperacion", "en_memoria", FICHAS, medir(_desde_memoria, pers, CAPACIDAD_MEMORIA)),
        Fila("recuperacion", "desde_disco", FICHAS, medir(_desde_disco, pers, CAPACIDAD_DISCO)),
    ]
