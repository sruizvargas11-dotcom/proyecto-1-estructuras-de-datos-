"""
Ordenamiento con seleccion automatica entre InsertionSort y MergeSort,
segun tamano y grado de desorden medidos.

Ambos reciben un 'comparar(a, b)' que devuelve negativo si a < b, cero
si son iguales, positivo si a > b - asi sirven tanto para ordenar la
tabla de puntajes como las vistas del inventario (por peso, valor o
nombre), sin duplicar codigo por cada criterio.
"""

from estructuras.vector_dinamico import Vector

UMBRAL_TAMANO_PEQUENO = 30       # se ajusta con --bench
# El umbral de tamaño es provisional hasta calibrarlo con --bench.
# Pocos descensos adyacentes NO garantizan pocas inversiones: dos bloques
# ordenados en orden inverso pueden requerir O(n^2) movimientos en Insertion.


def insertion_sort(vector, comparar):
    """In-place, O(n^2) en el peor caso, O(n + I), donde I es la cantidad de inversiones - por eso es la mejor opcion para listas pequenas
    o con pocos elementos fuera de lugar."""
    for i in range(1, len(vector)):
        actual = vector.obtenerValor(i)
        j = i - 1
        while j >= 0 and comparar(vector.obtenerValor(j), actual) > 0:
            vector.asignarValor(j + 1, vector.obtenerValor(j))
            j -= 1
        vector.asignarValor(j + 1, actual)


def merge_sort(vector, comparar):
    """O(n log n) garantizado, sin importar el orden de entrada.
    Necesita un Vector auxiliar del mismo tamano para la mezcla."""
    if len(vector) <= 1:
        return
    _merge_sort_rango(vector, 0, len(vector) - 1, comparar)


def _merge_sort_rango(vector, inicio, fin, comparar):
    if inicio >= fin:
        return
    medio = (inicio + fin) // 2
    _merge_sort_rango(vector, inicio, medio, comparar)
    _merge_sort_rango(vector, medio + 1, fin, comparar)
    _mezclar(vector, inicio, medio, fin, comparar)


def _mezclar(vector, inicio, medio, fin, comparar):
    izquierda = Vector()
    for i in range(inicio, medio + 1):
        izquierda.agregarValor(vector.obtenerValor(i))

    derecha = Vector()
    for i in range(medio + 1, fin + 1):
        derecha.agregarValor(vector.obtenerValor(i))

    i = j = 0
    k = inicio
    while i < len(izquierda) and j < len(derecha):
        if comparar(izquierda.obtenerValor(i), derecha.obtenerValor(j)) <= 0:
            vector.asignarValor(k, izquierda.obtenerValor(i))
            i += 1
        else:
            vector.asignarValor(k, derecha.obtenerValor(j))
            j += 1
        k += 1

    while i < len(izquierda):
        vector.asignarValor(k, izquierda.obtenerValor(i))
        i += 1
        k += 1

    while j < len(derecha):
        vector.asignarValor(k, derecha.obtenerValor(j))
        j += 1
        k += 1


def contar_desorden_local(vector, comparar):
    """Barrido O(n): cuenta pares ADYACENTES fuera de orden, sin medir
    inversiones completas (eso seria O(n^2) y arruinaria la ganancia)."""
    desorden = 0
    for i in range(len(vector) - 1):
        if comparar(vector.obtenerValor(i), vector.obtenerValor(i + 1)) > 0:
            desorden += 1
    return desorden


def elegir_algoritmo(vector, comparar, comparacion_costosa=False):
    """Decide cual algoritmo usar segun tamano y desorden medidos. Los umbrales se calibran corriendo --bench."""
    n = len(vector)

    if n <= UMBRAL_TAMANO_PEQUENO and not comparacion_costosa:
        return insertion_sort

    desorden = contar_desorden_local(vector, comparar)
    if desorden == 0 and not comparacion_costosa:
        return insertion_sort

    return merge_sort


def ordenar(vector, comparar, comparacion_costosa=False):
    """Punto de entrada unico: elige el algoritmo y ordena in-place."""
    algoritmo = elegir_algoritmo(vector, comparar, comparacion_costosa)
    algoritmo(vector, comparar)
    return algoritmo.__name__
