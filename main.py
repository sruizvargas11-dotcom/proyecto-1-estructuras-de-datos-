"""Entrada de CRIPTA.

    python main.py --offline              juega con los datos locales
    python main.py                        juega contra el servicio HTTP
    python main.py --offline --solo-mapa  solo carga y verifica el mapa (bloque 1)
"""
import argparse
from controlador.controlador_red import cargar_cripta
from vista.vista_consola import informar
from pathlib import Path


def crear_fuente(argumentos):
    if '--offline' in argumentos:
        from adaptadores.datos_offline import DatosOffline
        return DatosOffline(argumentos[argumentos.index('--offline-dir') + 1]
                            if '--offline-dir' in argumentos else None)
    from adaptadores.datos_http import DatosHTTP
    return DatosHTTP()


def main(argumentos=None):
    parser = argparse.ArgumentParser(description='CRIPTA')
    parser.add_argument('--offline', action='store_true', help='Usar los archivos locales')
    parser.add_argument('--cripta', help='Identificador; si se omite, la consola permite elegir')
    parser.add_argument('--cache-dir', help='Carpeta alternativa para la caché')
    parser.add_argument('--solo-mapa', action='store_true',
                        help='Solo cargar y verificar el mapa, sin jugar')
    parser.add_argument('--cache-size', type=int, default=25,
                        help='Fichas de catálogo en memoria (LRU), por defecto 25')
    parser.add_argument('--hilos', action='store_true',
                        help='Precarga de salas en segundo plano')
    parser.add_argument('--bench', action='store_true',
                        help='ejecuta cargas sintéticas y reporta tiempos')
    parser.add_argument('--offline-dir', help='Carpeta de datos locales (requiere --offline)')
    parser.add_argument('--partidas-dir', default='partidas', help='Guardados y bitácoras')
    parser.add_argument('--replay', metavar='LOG', help='Reproducir una bitácora sin vista interactiva')
    opciones = parser.parse_args(argumentos)
    if opciones.replay and opciones.bench:
        parser.error('--replay y --bench son modos excluyentes')
    if opciones.offline_dir and not opciones.offline:
        parser.error('--offline-dir requiere --offline')
    if opciones.bench:
        from bench.runner import main_bench
        main_bench()
        return 0
    try:
        args_fuente = ['--offline'] if opciones.offline else []
        if opciones.offline_dir:
            args_fuente += ['--offline-dir', opciones.offline_dir]
        fuente = crear_fuente(args_fuente)
        if opciones.replay:
            from controlador.reproduccion import reproducir
            partida = reproducir(fuente, opciones.replay, opciones.cache_dir, opciones.cache_size)
            informar(f'Replay verificado: {partida.cripta_id}, t={partida.tiempo}, '
                     f'{partida.acciones_jugador} acciones, {partida.estado}')
            return 0
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
                from vista.vista_consola import seleccionar_cripta
                cripta_id = seleccionar_cripta(respuesta['criptas'])
                if cripta_id is None:
                    return 0
        if opciones.solo_mapa:
            cripta, desde_cache = cargar_cripta(fuente, cripta_id, opciones.cache_dir)
            informar(f'Cripta cargada: {cripta.id} | {len(cripta)} salas')
            informar('Origen del mapa: ' + ('caché' if desde_cache else 'fuente de datos'))
            informar(f'Sala inicial: {cripta.sala_inicial_id} | Salida: {cripta.sala_salida_id}')
            return 0
        return jugar(fuente, cripta_id, opciones)
    except (OSError, ValueError, RuntimeError) as error:
        informar(f'No se pudo cargar la cripta: {error}')
        return 1


def jugar(fuente, cripta_id, opciones):
    """Partida nueva: semilla automática, bitácora y bucle principal."""
    from controlador.controlador_juego import ControladorJuego
    from controlador.despacho_red import DespachoEnHilos
    from controlador.inicio_partida import nueva_partida, ruta_bitacora_por_defecto
    from controlador.semilla import generar_semilla
    from vista.vista_consola import VistaConsola

    semilla = generar_semilla()
    sesion = nueva_partida(
        fuente, cripta_id, opciones.cache_dir, semilla=semilla,
        ruta_bitacora=ruta_bitacora_por_defecto(cripta_id, semilla,
                          str(Path(opciones.partidas_dir) / 'bitacoras')),
        cache_size=opciones.cache_size,
        despachador=DespachoEnHilos() if opciones.hilos else None)
    informar(f'Partida en {cripta_id} | semilla {semilla} | H para ver los comandos')
    ControladorJuego(sesion, VistaConsola(),
                      str(Path(opciones.partidas_dir) / 'partida.sav')).jugar()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
