"""Agenda de eventos: HeapMinimo vs lista lineal (buscar el mínimo recorriendo todo)."""
import random
from bench.medicion import Fila, medir

EXTRACCIONES = 20001

TAMANOS = (100, 500, 1000, 5000)


def _con_heap(valores):
    """Inserta todos los valores y los saca en orden con el HeapMinimo propio."""
    from estructuras.heap_minimo import HeapMinimo
    heap = HeapMinimo()
    for v in valores:
        heap.insertarEntrada(v, v)
    total = 0
    for i in range(EXTRACCIONES):
        total += heap.extraer_minimo()
        heap.insertarEntrada(valores[i % len(valores)] + i, valores[i % len(valores)] + i)
    return total


def _con_lista(valores):
    """Lo mismo, pero buscando el menor con un recorrido completo cada vez."""
    pendientes = list(valores)
    total = 0
    for paso in range(EXTRACCIONES):
        menor = 0
        for i in range(1, len(pendientes)):
            if pendientes[i] < pendientes[menor]:
                menor = i
        total += pendientes.pop(menor)
        pendientes.append(valores[paso % len(valores)] + paso)
    return total


def correr():
    rnd = random.Random(42)
    filas = []
    for n in TAMANOS:
        valores = [rnd.randint(0, 1_000_000) for _ in range(n)]
        for nombre, funcion in (("HeapMinimo", _con_heap), ("lista_lineal", _con_lista)):
            filas.append(Fila("agenda_eventos", nombre, n, medir(funcion, valores),
                              f"extracciones={EXTRACCIONES}; inserciones={n + EXTRACCIONES}"))
    return filas
