import threading

from estructuras.vector_dinamico import Vector


def _ejecutar(tarea, entregar):
    try:
        respuesta = tarea()
    except Exception as error:   # se re-lanza en el hilo principal al incorporar
        entregar(None, error)
    else:
        entregar(respuesta, None)


class DespachoInmediato:
    def enviar(self, tarea, entregar):
        _ejecutar(tarea, entregar)

    def cerrar(self, tiempo_maximo=None):
        return None


class DespachoEnHilos:
    def __init__(self):
        self._hilos = Vector()

    def enviar(self, tarea, entregar):
        hilo = threading.Thread(target=_ejecutar, args=(tarea, entregar), daemon=True)
        self._hilos.agregarValor(hilo)
        hilo.start()

    def cerrar(self, tiempo_maximo=None):
        """Espera a que terminen los hilos lanzados (al salir del juego)."""
        for hilo in self._hilos:
            hilo.join(tiempo_maximo)
        self._hilos = Vector()
