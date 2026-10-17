"""Agenda de eventos: HeapMinimo vs lista lineal (buscar el mínimo recorriendo todo)."""
import random
from bench.medicion import Fila, medir
from estructuras.vector_dinamico import Vector

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


N_VISTA = 5             # tamaño del panel "próximos turnos" (vista_pygame, §8.5)
REPETICIONES_VISTA = 200  # vista_ordenada es barata: se repite dentro de medir()


def _preparar_heap(n, rnd):
    from estructuras.heap_minimo import HeapMinimo
    heap = HeapMinimo()
    for v in (rnd.randint(0, 1_000_000) for _ in range(n)):
        heap.insertarEntrada(v, v)
    return heap


def _vista_ordenada(heap):
    """vista_ordenada no muta el heap: puede repetirse sin reconstruirlo."""
    for _ in range(REPETICIONES_VISTA):
        heap.vista_ordenada(N_VISTA)


def _comparar_clave(a, b):
    return (a[0] > b[0]) - (a[0] < b[0])


def _copiar_y_ordenar(heap):
    """Alternativa ingenua para contrastar: copiar las entradas válidas del
    heap a un Vector y ordenarlo completo (con el propio ordenar()), en vez
    del heap auxiliar de índices que usa vista_ordenada (que no copia ni
    ordena el heap entero)."""
    from estructuras.ordenamientos import ordenar
    datos = heap._datos
    for _ in range(REPETICIONES_VISTA):
        copia = Vector()
        for i in range(len(datos)):
            entrada = datos.obtenerValor(i)
            if entrada.valido:
                copia.agregarValor((entrada.clave(), i))
        ordenar(copia, _comparar_clave)


def correr():
    rnd = random.Random(42)
    filas = []
    for n in TAMANOS:
        valores = [rnd.randint(0, 1_000_000) for _ in range(n)]
        for nombre, funcion in (("HeapMinimo", _con_heap), ("lista_lineal", _con_lista)):
            filas.append(Fila("agenda_eventos", nombre, n, medir(funcion, valores)))

    rnd_vista = random.Random(43)
    for n in TAMANOS:
        heap = _preparar_heap(n, rnd_vista)
        filas.append(Fila("proximos_turnos", f"vista_ordenada({N_VISTA})", n,
                          medir(_vista_ordenada, heap),
                          extra=f"{REPETICIONES_VISTA} llamadas/repetición"))
        filas.append(Fila("proximos_turnos", "copiar_y_ordenar", n,
                          medir(_copiar_y_ordenar, heap),
                          extra=f"{REPETICIONES_VISTA} llamadas/repetición"))
    return filas
