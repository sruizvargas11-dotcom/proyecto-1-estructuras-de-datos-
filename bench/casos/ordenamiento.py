"""Inserción vs merge, con datos aleatorios y casi ordenados."""
import random
from bench.medicion import Fila, medir

TAMANOS = (5, 10, 25, 50, 100)


def _insercion(datos):
    a = list(datos)
    for i in range(1, len(a)):
        v, j = a[i], i
        while j > 0 and a[j - 1] > v:
            a[j] = a[j - 1]
            j -= 1
        a[j] = v
    return a


def _merge(datos):
    if len(datos) <= 1:
        return list(datos)
    m = len(datos) // 2
    izq, der = _merge(datos[:m]), _merge(datos[m:])
    out, i, j = [], 0, 0
    while i < len(izq) and j < len(der):
        if izq[i] <= der[j]:
            out.append(izq[i]); i += 1
        else:
            out.append(der[j]); j += 1
    return out + izq[i:] + der[j:]


def _datos(n, casi_ordenado):
    rnd = random.Random(42)                 # semilla fija = reproducible
    d = [rnd.randint(0, 10_000) for _ in range(n)]
    if casi_ordenado:
        d = _insercion(d)
        for _ in range(max(1, n // 20)):    # desordena solo ~5 %
            i, j = rnd.randrange(n), rnd.randrange(n)
            d[i], d[j] = d[j], d[i]
    return d


def correr():
    filas = []
    for forma in ("aleatorio", "casi_ordenado"):
        for n in TAMANOS:
            datos = _datos(n, forma == "casi_ordenado")
            for nombre, algoritmo in (("insercion", _insercion), ("merge", _merge)):
                filas.append(Fila("ordenamiento", nombre, n, medir(algoritmo, datos), forma))
    return filas
