"""Historial de retroceso: 5 deltas (Historial propio) vs 5 copias completas."""
from bench.medicion import Fila, medir

RETROCESOS = 5
TAMANOS_ESTADO = (50, 500)     # cuántos valores tiene el estado del juego


class _Celda:
    """Una posición del estado del juego, para poder registrarla con DeltaAtributos."""
    def __init__(self, valor):
        self.valor = valor


def _con_deltas(tam):
    """Registra 5 cambios pequeños y los deshace con el Historial propio."""
    from modelo.historial import Historial
    from modelo.reloj import Reloj
    from modelo.deltas import DeltaAtributos

    estado = [_Celda(i) for i in range(tam)]
    historial = Historial()
    reloj = Reloj(42, historial)
    for i in range(RETROCESOS):
        historial.iniciar_accion(reloj)
        historial.registrar(DeltaAtributos(estado[i], "valor"))
        estado[i].valor = -1
        historial.confirmar_accion()
    for _ in range(RETROCESOS):
        historial.revertir()


def _con_copias(tam):
    """Alternativa: guarda una copia completa del estado en cada paso."""
    estado = list(range(tam))
    copias = []
    for i in range(RETROCESOS):
        copias.append(list(estado))
        estado[i] = -1
    for _ in range(RETROCESOS):
        estado = copias.pop()


def correr():
    filas = []
    for tam in TAMANOS_ESTADO:
        filas.append(Fila("historial", "deltas", tam, medir(_con_deltas, tam),
                          f"valores_guardados={RETROCESOS}"))
        filas.append(Fila("historial", "copias", tam, medir(_con_copias, tam),
                          f"valores_guardados={RETROCESOS * tam}"))
    return filas
