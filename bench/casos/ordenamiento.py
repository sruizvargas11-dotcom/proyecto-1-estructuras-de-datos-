"""Mide los algoritmos reales sobre Vector, sin incluir preparación ni E/S."""
import random
from time import perf_counter
from bench.medicion import Fila, mediana
from estructuras.ordenamientos import insertion_sort, merge_sort
from estructuras.vector_dinamico import Vector

TAMANOS = (5, 10, 15, 20, 25, 30, 50, 60, 75, 100, 200, 500)
REPETICIONES = 7
MUESTRAS = 20


def comparar(a, b):
    return (a > b) - (a < b)


def vector(datos):
    salida = Vector()
    for dato in datos:
        salida.agregarValor(dato)
    return salida


def _datos(n, casi_ordenado, semilla=42):
    rnd = random.Random(semilla)
    datos = [rnd.randint(0, 10_000) for _ in range(n)]
    if casi_ordenado:
        ordenados = vector(datos)
        merge_sort(ordenados, comparar)
        datos = list(ordenados)
        for _ in range(max(1, n // 20)):
            i, j = rnd.randrange(n), rnd.randrange(n)
            datos[i], datos[j] = datos[j], datos[i]
    return datos


def medir_par(n, casi_ordenado):
    datos = [_datos(n, casi_ordenado, 42 + i) for i in range(MUESTRAS)]
    algoritmos = (insertion_sort, merge_sort)
    tiempos = ([], [])
    for algoritmo in algoritmos:
        for muestra in datos:
            algoritmo(vector(muestra), comparar)
    for repeticion in range(REPETICIONES):
        for indice in ((0, 1) if repeticion % 2 == 0 else (1, 0)):
            entradas = [vector(muestra) for muestra in datos]
            inicio = perf_counter()
            for entrada in entradas:
                algoritmos[indice](entrada, comparar)
            tiempos[indice].append((perf_counter() - inicio) * 1000 / MUESTRAS)
    return tiempos


def correr():
    filas = []
    for forma in ("aleatorio", "casi_ordenado"):
        for n in TAMANOS:
            tiempos = medir_par(n, forma == "casi_ordenado")
            for nombre, muestras in zip(("insertion_sort", "merge_sort"), tiempos):
                filas.append(Fila("ordenamiento", nombre, n, mediana(muestras),
                                  f"{forma}; rep={REPETICIONES}; muestras={MUESTRAS}"))
    return filas
