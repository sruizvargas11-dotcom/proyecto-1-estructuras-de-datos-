"""Punto de entrada de `python main.py --bench` (sin vista ni red)."""
from bench.casos import CASOS
from bench.medicion import imprimir_tabla


def main_bench():
    filas = []
    for caso in CASOS:
        filas.extend(caso())
    imprimir_tabla(filas)
    return filas