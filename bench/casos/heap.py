"""Agenda de eventos: HeapMinimo vs lista lineal (buscar el mínimo recorriendo todo)."""
import random
from bench.medicion import Fila, medir

TAMANOS = (100, 500, 1000, 5000)


def _con_heap(valores):
    """Inserta todos los valores y los saca en orden con el HeapMinimo propio."""
    from estructuras.heap_minimo import HeapMinimo
    heap = HeapMinimo()
    for v in valores:
        heap.insertarEntrada(v, v)
    while not heap.esta_vacio():
        heap.extraer_minimo()


def _con_lista(valores):
    """Lo mismo, pero buscando el menor con un recorrido completo cada vez."""
    pendientes = list(valores)
    while pendientes:
        menor = 0
        for i in range(1, len(pendientes)):
            if pendientes[i] < pendientes[menor]:
                menor = i
        pendientes.pop(menor)


def correr():
    rnd = random.Random(42)
    filas = []
    for n in TAMANOS:
        valores = [rnd.randint(0, 1_000_000) for _ in range(n)]
        for nombre, funcion in (("HeapMinimo", _con_heap), ("lista_lineal", _con_lista)):
            filas.append(Fila("agenda_eventos", nombre, n, medir(funcion, valores)))
    return filas
