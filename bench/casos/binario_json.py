"""Guardado/carga (§4.10): PartidaBinaria vs JSON, tamaño y tiempo de carga.

bench/bench_bloque3.py ya mide exactamente esto con la API real de
PartidaBinaria (guardar/cargar_todo/cargar_sala_binaria) y es importable sin
efectos secundarios (solo define funciones; su main() queda detrás de
`if __name__ == "__main__"`). Se reutiliza bench_tamano() en vez de volver a
escribir esas llamadas; ya acepta num_salas, así que basta llamarla una vez
por tamaño (internamente elige su propia sala intermedia de ese tamaño).
"""
import tempfile
from bench.bench_bloque3 import bench_tamano
from bench.medicion import Fila

TAMANOS_SALAS = (50, 500, 5000)


def _medir(n):
    carpeta = tempfile.mkdtemp()
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
