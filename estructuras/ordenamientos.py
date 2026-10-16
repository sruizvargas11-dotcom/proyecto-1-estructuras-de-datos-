"""Selecciona entre InsertionSort y MergeSort para ordenar un Vector.

El comparador devuelve un valor negativo si a < b, cero si son equivalentes
y uno positivo si a > b. Esto permite reutilizar los algoritmos con distintos
criterios, como el peso, el valor o el nombre de los objetos.
"""

from estructuras.vector_dinamico import Vector

UMBRAL_TAMANO_PEQUENO = 50
# Medido con las funciones reales y Vector: docs/decisiones/4.09.txt.
# Cruce aleatorio claro desde n=60; n=50 queda dentro del margen del 10%.
# Dos bloques ordenados pero colocados en orden inverso pueden tener pocos
# descensos entre vecinos y aun así exigir O(n²) movimientos a InsertionSort.


def insertion_sort(vector, comparar):
    """Ordena sobre el mismo Vector en O(n + I), donde I es el número de inversiones.

    Con datos ordenados cuesta O(n); en el peor caso llega a O(n²).
    """
    for i in range(1, len(vector)):
        actual = vector.obtenerValor(i)
        j = i - 1
        while j >= 0 and comparar(vector.obtenerValor(j), actual) > 0:
            vector.asignarValor(j + 1, vector.obtenerValor(j))
            j -= 1
        vector.asignarValor(j + 1, actual)


def merge_sort(vector, comparar):
    """Ordena en O(n log n), con vectores auxiliares para mezclar cada rango."""
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
    """Cuenta en O(n) los pares vecinos que están fuera de orden.

    Este conteo permite detectar una entrada ya ordenada, pero no mide
    el total de inversiones.
    """
    desorden = 0
    for i in range(len(vector) - 1):
        if comparar(vector.obtenerValor(i), vector.obtenerValor(i + 1)) > 0:
            desorden += 1
    return desorden


def elegir_algoritmo(vector, comparar, comparacion_costosa=False):
    """Elige según el tamaño, el orden de entrada y el costo del comparador."""
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
