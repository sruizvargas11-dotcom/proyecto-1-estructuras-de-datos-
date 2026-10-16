"""Reproduce acciones aceptadas sin importar ni instanciar VistaConsola."""
from bitacora_partida import BitacoraPartida
from controlador.inicio_partida import nueva_partida
from controlador.controlador_juego import ControladorJuego
from estructuras.array_circular import ArrayCircular


class PuertoReproduccion:
    def __init__(self, acciones):
        self.acciones = acciones
        self.indice = 0
        self.ultimos = ArrayCircular(20)

    def leer_comando(self):
        if self.indice == len(self.acciones):
            return 'Q'
        texto = self.acciones[self.indice][1]
        self.indice += 1
        return texto

    def agregar_mensaje(self, tiempo, texto):
        self.ultimos.agregarValor((tiempo, texto))

    def mostrar_estado(self, partida):
        pass

    def mostrar_fin(self, partida):
        pass

    def mostrar_ayuda(self):
        pass

    def mostrar_inventario(self, *args):
        pass


def reproducir(fuente, ruta, cache=None, cache_size=25):
    try:
        log = BitacoraPartida.abrir(ruta)
        acciones = log.leer_acciones()
    except KeyError as error:
        raise ValueError(f'Bitácora incompleta: falta {error.args[0]}.') from error
    sesion = nueva_partida(fuente, log.cripta_id, cache, semilla=log.semilla,
                           cache_size=cache_size)
    try:
        log.verificar_compatibilidad(sesion.partida.version_cripta,
                                    sesion.partida.version_catalogo)
        permitidas = ('mover', 'atacar', 'esperar', 'recoger', 'soltar',
                     'equipar', 'usar', 'abrir', 'pergamino')
        for tiempo, accion in acciones:
            if tiempo < 0 or accion.split(' ')[0] not in permitidas:
                raise ValueError('Bitácora con acción no reproducible.')
        puerto = PuertoReproduccion(acciones)
        controlador = ControladorJuego(sesion, puerto)
        controlador.jugar()
        if list(sesion.acciones) != acciones:
            raise ValueError('Replay divergente: acciones o tiempos no coinciden.')
        return sesion.partida
    finally:
        sesion.red.cerrar(5)
