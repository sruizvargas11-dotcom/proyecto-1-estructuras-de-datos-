"""Entrada de CRIPTA: carga y verifica el mapa inicial del bloque 1."""
import argparse
from controlador.controlador_red import cargar_cripta


def crear_fuente(argumentos):
    if '--offline' in argumentos:
        from adaptadores.datos_offline import DatosOffline
        return DatosOffline()
    from adaptadores.datos_http import DatosHTTP
    return DatosHTTP()


def main(argumentos=None):
    parser = argparse.ArgumentParser(description='Carga inicial de CRIPTA')
    parser.add_argument('--offline', action='store_true', help='Usar los archivos locales')
    parser.add_argument('--cripta', help='Identificador; por defecto se usa la primera de la lista')
    parser.add_argument('--cache-dir', help='Carpeta alternativa para la caché')
    opciones = parser.parse_args(argumentos)
    try:
        fuente = crear_fuente(['--offline'] if opciones.offline else [])
        cripta_id = opciones.cripta
        if cripta_id is None:
            respuesta = fuente.listar_criptas()
            if not isinstance(respuesta, dict) or not isinstance(respuesta.get('criptas'), list):
                raise ValueError('El listado de criptas es inválido.')
            if not respuesta['criptas']:
                raise ValueError('No hay criptas disponibles.')
            print('Criptas disponibles:')
            for cripta in respuesta['criptas']:
                if (not isinstance(cripta, dict) or not isinstance(cripta.get('id'), str)
                        or not isinstance(cripta.get('nombre'), str)):
                    raise ValueError('El listado contiene una cripta inválida.')
                print(f"- {cripta['id']}: {cripta['nombre']}")
            cripta_id = respuesta['criptas'][0]['id']
        cripta, desde_cache = cargar_cripta(fuente, cripta_id, opciones.cache_dir)
        print(f'Cripta cargada: {cripta.id} | {len(cripta)} salas')
        print('Origen del mapa: ' + ('caché' if desde_cache else 'fuente de datos'))
        print(f'Sala inicial: {cripta.sala_inicial_id} | Salida: {cripta.sala_salida_id}')
        print('Bloque 1: mapa listo. El bucle de juego aún no está implementado.')
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f'No se pudo cargar la cripta: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
