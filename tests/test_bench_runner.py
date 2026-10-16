"""Comprobaciones básicas de los casos y resultados de --bench."""
import ast
import glob

from bench.casos import CASOS, heap, inventario, lru
from bench.medicion import Fila, mediana, medir


def test_mediana_y_medir():
    assert mediana([5, 1, 3, 9, 2]) == 3
    assert medir(sum, [1, 2, 3], repeticiones=3) >= 0


def test_cada_caso_devuelve_filas_bien_formadas(monkeypatch):
    # tamaños pequeños para que el test sea rápido
    monkeypatch.setattr(heap, "TAMANOS", (10, 20))
    monkeypatch.setattr(inventario, "TAMANOS", (5, 10))
    monkeypatch.setattr(lru, "BUSQUEDAS", 50)
    for caso in CASOS:
        filas = caso()
        assert len(filas) > 0
        for f in filas:
            assert isinstance(f, Fila)
            assert f.ms >= 0
            assert f.n > 0
            assert f.caso and f.variante


def test_bench_no_usa_construcciones_prohibidas():
    archivos = glob.glob("bench/casos/*.py") + ["bench/medicion.py", "bench/runner.py"]
    for ruta in archivos:
        with open(ruta, encoding="utf-8-sig") as f:
            arbol = ast.parse(f.read())
        for nodo in ast.walk(arbol):
            assert not isinstance(nodo, ast.Lambda), f"lambda en {ruta}"
            if isinstance(nodo, ast.Call):
                if isinstance(nodo.func, ast.Name):
                    assert nodo.func.id != "sorted", f"sorted() en {ruta}"
                if isinstance(nodo.func, ast.Attribute):
                    assert nodo.func.attr != "sort", f".sort() en {ruta}"
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    assert alias.name != "heapq", f"heapq en {ruta}"
            if isinstance(nodo, ast.ImportFrom):
                assert nodo.module != "heapq", f"heapq en {ruta}"
