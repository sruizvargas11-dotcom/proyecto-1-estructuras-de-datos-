"""Historial de retroceso: 5 deltas (Historial propio) vs 5 copias completas."""
from bench.medicion import Fila, medir
from modelo.historial import Historial
from modelo.reloj import Reloj
from modelo.deltas import DeltaAtributos

RETROCESOS = 5
TAMANOS_ESTADO = (100, 1000, 10000)     # cuántos valores tiene el estado del juego


class _Celda:
    """Una posición del estado del juego, para poder registrarla con DeltaAtributos."""
    def __init__(self, valor):
        self.valor = valor


def _con_deltas(estado, reloj):
    """Registra 5 cambios pequeños y los deshace con el Historial propio."""
    historial = reloj.historial
    for i in range(RETROCESOS):
        historial.iniciar_accion(reloj)
        historial.registrar(DeltaAtributos(estado[i], "valor"))
        estado[i].valor = -1
        reloj.azar.random()
        historial.confirmar_accion()
    for _ in range(RETROCESOS):
        historial.revertir()


def _con_copias(estado, reloj):
    """Alternativa: guarda una copia completa del estado en cada paso."""
    copias = []
    for i in range(RETROCESOS):
        copias.append(([celda.valor for celda in estado], reloj.azar.getstate(),
                       reloj.tiempo_actual, reloj.agenda.siguiente_secuencia))
        estado[i].valor = -1
        reloj.azar.random()
    for _ in range(RETROCESOS):
        anterior, azar, tiempo, secuencia = copias.pop()
        for celda, valor in zip(estado, anterior):
            celda.valor = valor
        reloj.azar.setstate(azar)
        reloj.tiempo_actual = tiempo
        reloj.agenda.restaurar_secuencia(secuencia)


def correr():
    filas = []
    for tam in TAMANOS_ESTADO:
        for nombre, funcion in (('deltas', _con_deltas), ('copias', _con_copias)):
            # Preparación fuera del cronómetro; ambas restauran también el PRNG.
            estado = [_Celda(i) for i in range(tam)]
            reloj = Reloj(42, Historial())
            azar_inicial = reloj.azar.getstate()
            ms = medir(funcion, estado, reloj)
            assert all(celda.valor == i for i, celda in enumerate(estado))
            assert reloj.azar.getstate() == azar_inicial
            guardados = RETROCESOS if nombre == 'deltas' else RETROCESOS * tam
            filas.append(Fila('historial', nombre, tam, ms,
                              f'valores_guardados={guardados}; cambios=5; reversiones=5; PRNG incluido'))
    return filas
