"""Entrada de CRIPTA.

    python main.py --offline              juega con los datos locales
    python main.py                        juega contra el servicio HTTP
    python main.py --offline --solo-mapa  solo carga y verifica el mapa (bloque 1)
    python main.py --replay partida.log   reproduce una bitácora sin interacción
"""
import argparse
from controlador.controlador_red import cargar_cripta
from controlador.reporte_red import motivo_error, motivo_partida, registrar_reporte


def crear_fuente(argumentos):
    if '--offline' in argumentos:
        from adaptadores.datos_offline import DatosOffline
        return DatosOffline()
    from adaptadores.datos_http import DatosHTTP
    return DatosHTTP()


def main(argumentos=None):
    parser = argparse.ArgumentParser(description='CRIPTA')
    parser.add_argument('--offline', action='store_true', help='Usar los archivos locales')
    parser.add_argument('--cripta', help='Identificador; por defecto se usa la primera de la lista')
    parser.add_argument('--cache-dir', help='Carpeta alternativa para la caché')
    parser.add_argument('--solo-mapa', action='store_true',
                        help='Solo cargar y verificar el mapa, sin jugar')
    parser.add_argument('--cache-size', type=int, default=25,
                        help='Fichas de catálogo en memoria (LRU), por defecto 25')
    parser.add_argument('--hilos', action='store_true',
                        help='Precarga de salas en segundo plano')
    parser.add_argument('--replay', metavar='LOG',
                        help='Reproducir una bitácora de partida sin interacción')
    parser.add_argument('--silencioso', action='store_true',
                        help='Con --replay: no listar cada acción, solo el resultado')
    parser.add_argument('--reportes', metavar='ARCHIVO',
                        help='Historial de reportes de red (por defecto partidas/reportes_red.txt)')
    opciones = parser.parse_args(argumentos)
    fuente = None
    try:
        fuente = crear_fuente(['--offline'] if opciones.offline else [])
        if opciones.replay:
            return reproducir(fuente, opciones)
        cripta_id = opciones.cripta
        if cripta_id is None:
            respuesta = fuente.listar_criptas()
            if not isinstance(respuesta, dict) or not isinstance(respuesta.get('criptas'), list):
                raise ValueError('El listado de criptas es inválido.')
            if not respuesta['criptas']:
                raise ValueError('No hay criptas disponibles.')
            for cripta in respuesta['criptas']:
                if (not isinstance(cripta, dict) or not isinstance(cripta.get('id'), str)
                        or not isinstance(cripta.get('nombre'), str)):
                    raise ValueError('El listado contiene una cripta inválida.')
            if opciones.solo_mapa:
                cripta_id = respuesta['criptas'][0]['id']
            else:
                from vista.vista_consola import VistaConsola
                cripta_id = VistaConsola().elegir_cripta(respuesta['criptas'])
        if opciones.solo_mapa:
            cripta, desde_cache = cargar_cripta(fuente, cripta_id, opciones.cache_dir)
            print(f'Cripta cargada: {cripta.id} | {len(cripta)} salas')
            print('Origen del mapa: ' + ('caché' if desde_cache else 'fuente de datos'))
            print(f'Sala inicial: {cripta.sala_inicial_id} | Salida: {cripta.sala_salida_id}')
            return 0
        return jugar(fuente, cripta_id, opciones)
    except (OSError, ValueError, RuntimeError) as error:
        print(f'No se pudo cargar la cripta: {error}')
        if fuente is not None and not opciones.solo_mapa and not getattr(error, 'reportado', False):
            _mostrar_reporte(fuente, None, 'replay' if opciones.replay else 'partida',
                             motivo_error(error), opciones)
        return 1


def _mostrar_reporte(fuente, sesion, modo, motivo, opciones, bitacora=None):
    print('')
    print(registrar_reporte(fuente, sesion, modo, motivo, ruta=opciones.reportes,
                            bitacora=bitacora))


def jugar(fuente, cripta_id, opciones):
    """Partida nueva: semilla automática, bitácora y bucle principal."""
    from controlador.controlador_juego import ControladorJuego
    from controlador.despacho_red import DespachoEnHilos
    from controlador.inicio_partida import nueva_partida, ruta_bitacora_por_defecto
    from controlador.semilla import generar_semilla
    from vista.vista_consola import VistaConsola

    semilla = generar_semilla()
    ruta_log = ruta_bitacora_por_defecto(cripta_id, semilla)
    sesion = nueva_partida(
        fuente, cripta_id, opciones.cache_dir, semilla=semilla,
        ruta_bitacora=ruta_log,
        cache_size=opciones.cache_size,
        despachador=DespachoEnHilos() if opciones.hilos else None)
    vista = VistaConsola()
    vista.mostrar_inicio(cripta_id, semilla)
    try:
        ControladorJuego(sesion, vista).jugar()
    except Exception as error:
        _mostrar_reporte(fuente, sesion, 'partida', motivo_error(error), opciones, ruta_log)
        error.reportado = True
        raise
    _mostrar_reporte(fuente, sesion, 'partida', motivo_partida(sesion.partida.estado),
                     opciones, ruta_log)
    return 0


def reproducir(fuente, opciones):
    """--replay: sin vista interactiva. Códigos de salida: 0 idéntico,
    2 versión incompatible, 3 la reproducción divergió del log."""
    from bitacora_partida import ErrorVersionIncompatible
    from controlador.controlador_replay import ErrorReplayDivergente, reproducir as replay

    print(f'Reproduciendo {opciones.replay}')
    try:
        resultado = replay(opciones.replay, fuente, opciones.cache_dir,
                           escribir=None if opciones.silencioso else print)
    except ErrorVersionIncompatible as error:
        print(f'Replay detenido: {error}')
        _mostrar_reporte(fuente, error.sesion, 'replay',
                         f'replay detenido, versión incompatible: {error}', opciones,
                         opciones.replay)
        return 2
    except ErrorReplayDivergente as error:
        print(f'Replay divergente: {error}')
        _mostrar_reporte(fuente, error.sesion, 'replay', f'replay divergente: {error}',
                         opciones, opciones.replay)
        return 3
    partida = resultado.partida
    print('')
    print(f'Resultado: {partida.estado} | t={partida.tiempo} | '
          f'{len(resultado.acciones)} acciones reproducidas')
    for campo, valor in partida.resumen_puntaje():
        print(f'  {campo}: {valor}')
    if resultado.verificado:
        print(f'Estado final idéntico al registrado en la bitácora '
              f'({len(resultado.lineas_estado)} líneas comparadas): reproducción idéntica.')
    else:
        print('La bitácora no trae el estado final (la partida original no terminó '
              'de forma controlada); se reprodujeron todas sus acciones sin errores.')
    verificacion = ('idéntico a la partida original' if resultado.verificado
                    else 'sin estado final para comparar')
    _mostrar_reporte(fuente, resultado.sesion, 'replay',
                     f'replay completo, {verificacion}; {motivo_partida(partida.estado)}',
                     opciones, opciones.replay)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
