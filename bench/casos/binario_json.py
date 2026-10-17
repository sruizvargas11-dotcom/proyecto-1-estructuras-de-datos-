"""Compara tamaño y tiempos del guardado binario frente a JSON.

Reutiliza bench_tamano de bench_bloque3 para medir escritura, lectura
completa y consulta de una sala en distintos tamaños de partida.
"""
import tempfile
from bench.bench_bloque3 import bench_tamano
from bench.medicion import Fila

TAMANOS_SALAS = (50, 500, 5000)


def _medir(n):
    with tempfile.TemporaryDirectory(prefix="cripta-bench-") as carpeta:
        return bench_tamano(n, carpeta)


def correr():
    filas = []
    for n in TAMANOS_SALAS:
        r = _medir(n)
        filas.append(Fila("guardado", "binario", n, r["t_guardar_bin"] * 1000, f"bytes={r['tam_bin']}"))
        filas.append(Fila("guardado", "json", n, r["t_guardar_json"] * 1000, f"bytes={r['tam_json']}"))
        filas.append(Fila("carga_total", "binario", n, r["t_cargar_todo_bin"] * 1000))
        filas.append(Fila("carga_total", "json", n, r["t_cargar_todo_json"] * 1000))
        filas.append(Fila("carga_1_sala", "binario", n, r["t_cargar_sala_bin"] * 1000, "usa índice"))
        filas.append(Fila("carga_1_sala", "json", n, r["t_cargar_sala_json"] * 1000, "lee todo"))
    return filas
