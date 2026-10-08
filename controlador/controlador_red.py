"""Carga inicial del bloque 1. La fuente decide si los datos vienen de HTTP o disco."""
from modelo.mundo.cripta_modelo import CriptaModelo
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from persistencia.esqueleto import PersistenciaEsqueleto
from persistencia.version import PersistenciaVersiones


def _exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(f"Datos de cripta inválidos: {mensaje}")


def _generales(fuente, cripta_id):
    d = fuente.datos_cripta(cripta_id)
    _exigir(isinstance(d, dict), 'datos generales deben ser un objeto')
    requeridos = ('id', 'version', 'salas_total', 'paginas', 'sala_inicial',
                  'sala_salida', 'llave_salida', 'presupuesto_solicitudes', 'inventario_max')
    _exigir(all(k in d for k in requeridos), 'faltan campos generales')
    _exigir(d['id'] == cripta_id, 'identificador distinto al solicitado')
    _exigir(isinstance(d['version'], str) and bool(d['version'].strip()), 'versión vacía')
    for campo in ('salas_total', 'paginas'):
        _exigir(type(d[campo]) is int and d[campo] > 0, f'{campo} debe ser entero positivo')
    _exigir(d['paginas'] <= d['salas_total'], 'más páginas que salas')
    for campo in ('sala_inicial', 'sala_salida'):
        _exigir(type(d[campo]) is int, f'{campo} debe ser entero')
    for campo in ('presupuesto_solicitudes', 'inventario_max'):
        _exigir(type(d[campo]) is int and d[campo] >= 0, f'{campo} inválido')
    _exigir(d['llave_salida'] is None or isinstance(d['llave_salida'], str), 'llave inválida')
    return d


def _construir(fuente, d):
    c = CriptaModelo(d['id'], d['version'], d['sala_inicial'], d['sala_salida'],
                     d['llave_salida'], d['presupuesto_solicitudes'], d['inventario_max'])
    for pagina in range(1, d['paginas'] + 1):
        respuesta = fuente.esqueleto_cripta(c.id, pagina)
        _exigir(isinstance(respuesta, dict), f'página {pagina} inválida')
        _exigir(type(respuesta.get('pagina')) is int and respuesta['pagina'] == pagina,
                'número de página inesperado')
        _exigir(type(respuesta.get('total_paginas')) is int
                and respuesta['total_paginas'] == d['paginas'], 'total de páginas cambió')
        salas = respuesta.get('salas')
        _exigir(isinstance(salas, list) and bool(salas), f'página {pagina} sin salas')
        for x in salas:
            _exigir(isinstance(x, dict), 'sala inválida')
            _exigir(type(x.get('id')) is int and isinstance(x.get('nombre'), str),
                    'ID o nombre de sala inválido')
            salidas = x.get('salidas')
            _exigir(isinstance(salidas, dict), 'salidas deben ser un objeto JSON')
            sala = Sala(x['id'], x['nombre'])
            # Orden canónico: la respuesta no determina el orden de las direcciones.
            _exigir(all(dir in ('N', 'S', 'E', 'O') for dir in salidas), 'dirección inválida')
            for direccion in ('O', 'E', 'S', 'N'):
                if direccion not in salidas:
                    continue
                s = salidas[direccion]
                _exigir(isinstance(s, dict) and type(s.get('sala')) is int, 'destino inválido')
                cerrada = s.get('cerrada', False)
                llave = s.get('llave')
                cierre = s.get('cierre_automatico')
                _exigir(type(cerrada) is bool, 'cerrada debe ser booleano')
                _exigir(llave is None or isinstance(llave, str), 'llave inválida')
                _exigir(cierre is None or (type(cierre) is int and cierre >= 0), 'cierre inválido')
                sala.salidas.insertar_al_inicio(Salida(direccion, s['sala'], cerrada, llave, cierre))
            c.agregar_sala(sala)
            _exigir(len(c) <= d['salas_total'], 'más salas que las declaradas')
    _exigir(len(c) == d['salas_total'], 'cantidad de salas incompleta')
    c.finalizar_carga()  # También rechaza IDs duplicados.
    _exigir(c.sala_por_id(c.sala_inicial_id) is not None, 'sala inicial inexistente')
    _exigir(c.sala_por_id(c.sala_salida_id) is not None, 'sala de salida inexistente')
    for sala in c.recorrer_salas():
        for salida in sala.salidas.recorrer_valores():
            _exigir(c.sala_por_id(salida.sala_destino_id) is not None, 'conexión a sala inexistente')
    version_final = fuente.version_cripta(c.id)
    _exigir(isinstance(version_final, dict) and version_final.get('version') == c.version,
            'la versión cambió durante la descarga; vuelva a intentar la carga')
    return c


def cargar_esqueleto_completo(fuente, cripta_id):
    """Devuelve un modelo completo desde la fuente, sin usar ni modificar caché."""
    return _construir(fuente, _generales(fuente, cripta_id))


def cargar_cripta(fuente, cripta_id, carpeta_cache=None):
    """Devuelve (modelo, desde_cache). Nunca publica una descarga parcial.

    Se consultan generales incluso con caché para conocer versión y presupuesto
    actuales. Con caché vigente no se piden páginas ni contenido de salas.
    """
    persistencia = PersistenciaEsqueleto(carpeta_cache)
    # Validar el identificador antes de pasarlo a la fuente o al sistema de archivos.
    _exigir(isinstance(cripta_id, str) and bool(cripta_id.strip())
            and cripta_id not in ('.', '..') and not any(c in cripta_id for c in '/\\:'),
            'identificador inválido')
    versiones = PersistenciaVersiones(carpeta_cache)
    d = _generales(fuente, cripta_id)
    c = persistencia.cargar_esqueleto(cripta_id, d['version'])
    if c is not None and (
        len(c) == d['salas_total'] and c.sala_inicial_id == d['sala_inicial']
        and c.sala_salida_id == d['sala_salida'] and c.llave_salida == d['llave_salida']
        and c.presupuesto_solicitudes == d['presupuesto_solicitudes']
        and c.inventario_max == d['inventario_max']
    ):
        # Reparar el registro auxiliar si el guardado anterior terminó entre archivos.
        if versiones.version_cripta_local(c.id) != c.version:
            versiones.guardar_version_cripta(c.id, c.version)
        return c, True
    c = _construir(fuente, d)
    persistencia.guardar_esqueleto(c)
    versiones.guardar_version_cripta(c.id, c.version)
    return c, False
