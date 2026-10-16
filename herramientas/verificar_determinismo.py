"""Compara partidas y replays con diez patrones de latencia y cachés vacías.

Recibe una fábrica de fuentes y una secuencia de comandos, de modo que
se pueda repetir el ensayo con distintos datos de cripta.
"""
from pathlib import Path
import json

from adaptadores.datos_simulado import DatosSimulado, suma_verificacion
from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.controlador_replay import reproducir
from controlador.despacho_red import DespachoEnHilos
from controlador.estado_final import lineas_estado
from controlador.inicio_partida import nueva_partida


class VistaGuion:
    def __init__(self, comandos):
        self.comandos = iter(comandos)
        self.mensajes = []

    def leer_comando(self):
        return next(self.comandos, 'Q')

    def agregar_mensaje(self, tiempo, texto):
        self.mensajes.append((tiempo, texto))

    def mostrar_estado(self, partida):
        pass

    def mostrar_inventario(self, partida, objetos, criterio):
        pass

    def mostrar_ayuda(self):
        pass

    def mostrar_fin(self, partida):
        pass


def serializar(lineas, mensajes):
    estado = ('\n'.join(lineas) + '\n').encode('utf-8')
    textos = json.dumps(mensajes, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return estado, textos


def verificar(fabrica_fuente, cripta_id, comandos, carpeta, patrones=10, semilla=3):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=False)
    filas = []
    base = base_replay = None
    for patron in range(-1, patrones):
        nombre = 'offline' if patron == -1 else f'latencia-{patron}'
        raiz = carpeta / nombre
        fuente = fabrica_fuente()
        if patron >= 0:
            fuente = DatosSimulado(fuente, patron)
        ruta = raiz / 'partida.log'
        sesion = nueva_partida(fuente, cripta_id, str(raiz / 'cache'), semilla=semilla,
                               ruta_bitacora=str(ruta),
                               despachador=None if patron == -1 else DespachoEnHilos())
        vista = VistaGuion(comandos)
        controlador = ControladorJuego(sesion, vista)
        controlador.jugar()
        estado, mensajes = serializar(lineas_estado(sesion.partida), vista.mensajes)
        actual = (estado, mensajes, ruta.read_bytes())
        if base is None:
            base = actual
        if actual != base:
            raise AssertionError(f'Partida divergente: {nombre}')
        # Reproduce cada log con un patrón distinto y una caché independiente.
        replay = reproducir(str(ruta), DatosSimulado(fabrica_fuente(), patron + patrones + 1),
                            str(raiz / 'cache-replay'), despachador=DespachoEnHilos())
        estado_replay, mensajes_replay = serializar(replay.lineas_estado, replay.mensajes)
        if not replay.verificado or estado_replay != estado:
            raise AssertionError(f'Replay divergente: {nombre}')
        if base_replay is None:
            base_replay = mensajes_replay
        if mensajes_replay != base_replay:
            raise AssertionError(f'Mensajes del replay divergentes: {nombre}')
        filas.append({
            'patron': nombre, 'patron_replay': patron + patrones + 1,
            'estado': suma_verificacion(estado.decode('utf-8')),
            'mensajes': suma_verificacion(mensajes.decode('utf-8')),
            'mensajes_replay': suma_verificacion(mensajes_replay.decode('utf-8')),
            'log': suma_verificacion(actual[2].decode('utf-8')),
            'acciones': len(sesion.acciones), 'resultado': sesion.partida.estado,
            'contadores': dict(controlador.contadores()), 'replay_verificado': replay.verificado,
            'inventario': dict(sesion.partida.jugador.inventario.contadores()),
            'red': dict(sesion.red.contadores()),
            'lru': dict(sesion.red._fichas.contadores_operaciones()),
        })
    return filas

class FuenteEnsayo(DatosOffline):
    """Solo para el ensayo: vida 300 leída por igual en partida y replay."""
    def datos_cripta(self, cripta_id):
        datos = super().datos_cripta(cripta_id)
        datos['jugador']['vida_max'] = 300
        return datos


def main():
    import argparse
    import platform
    import tempfile
    from adaptadores.datos_offline import DatosOffline
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cripta', required=True)
    parser.add_argument('--guion', required=True, help='JSON: lista de comandos')
    parser.add_argument('--offline-dir')
    parser.add_argument('--ensayo', action='store_true', help='vida 300, solo en memoria')
    parser.add_argument('--salida', required=True)
    args = parser.parse_args()
    comandos = json.loads(Path(args.guion).read_text(encoding='utf-8-sig'))
    if not isinstance(comandos, list) or not all(isinstance(c, str) for c in comandos):
        parser.error('El guion debe ser una lista de cadenas.')
    def fuente():
        return FuenteEnsayo(args.offline_dir) if args.ensayo else DatosOffline(args.offline_dir)
    with tempfile.TemporaryDirectory() as temporal:
        filas = verificar(fuente, args.cripta, comandos, Path(temporal) / 'corridas')
    evidencia = {'python': platform.python_version(), 'sistema': platform.platform(),
                 'semilla': 3, 'ensayo_vida_300': args.ensayo, 'cripta': args.cripta,
                 'comandos': comandos, 'filas': filas}
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(filas)} partidas y replays idénticos; evidencia: {salida}')


if __name__ == '__main__':
    main()
