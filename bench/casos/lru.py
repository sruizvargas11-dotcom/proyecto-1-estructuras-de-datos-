"""Búsquedas de caché: ListaLRU de tamaño 25 vs lista plana sin política."""
import random
from bench.medicion import Fila, medir

CAPACIDAD = 25
BUSQUEDAS = 1000
CLAVES_DISTINTAS = 40      # más claves que capacidad: obliga a expulsar


def _claves():
    rnd = random.Random(42)
    return [rnd.randrange(CLAVES_DISTINTAS) for _ in range(BUSQUEDAS)]


def _con_lru(claves):
    """Busca cada clave; si falla, la inserta. Devuelve los aciertos."""
    from estructuras.listalru import ListaLRU
    cache = ListaLRU(CAPACIDAD)
    aciertos = 0
    for clave in claves:
        if cache.buscar(clave) is not None:
            aciertos += 1
        else:
            cache.insertar(clave, clave)
    return aciertos


def _con_lista_plana(claves):
    """Alternativa: guarda todo lo visto y busca linealmente (sin expulsar)."""
    vistas = []
    aciertos = 0
    for clave in claves:
        encontrada = False
        for v in vistas:
            if v == clave:
                encontrada = True
                break
        if encontrada:
            aciertos += 1
        else:
            vistas.append(clave)
    return aciertos


def correr():
    claves = _claves()
    filas = []
    for nombre, funcion in (("ListaLRU", _con_lru), ("lista_plana", _con_lista_plana)):
        aciertos = funcion(claves)
        ms = medir(funcion, claves)
        filas.append(Fila("cache", nombre, BUSQUEDAS, ms, f"aciertos={aciertos}; fallos={len(claves)-aciertos}",
                          (("aciertos", aciertos), ("fallos", len(claves)-aciertos))))
    return filas
