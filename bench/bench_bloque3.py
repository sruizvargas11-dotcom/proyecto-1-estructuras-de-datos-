"""Benchmark Bloque 3 — PartidaBinaria vs. equivalente en JSON (§4.10 / §5.3).

Ejecutar directo, sin pytest:
    python bench/bench_bloque3.py

Mide con time.perf_counter(), 5 repeticiones por medición, reporta la
mediana. Los estados se generan proceduralmente; los archivos temporales
se escriben en la carpeta temporal del sistema y se borran al terminar.
"""

import json
import os
import random
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistencia.PartidaBinaria import PartidaBinaria
from bench.medicion import mediana
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar


def _comparar_ids(a, b):
    return (a > b) - (a < b)


def _comparar_pares(a, b):
    return (a[0] > b[0]) - (a[0] < b[0])

REPETICIONES = 5
TAMANOS = [10, 100, 500]


def generar_estado(num_salas):
    """Genera un estado global + estado de salas de ejemplo, sin leer archivos."""
    rng = random.Random(42 + num_salas)

    estado_global = {
        "reloj": rng.randint(0, 100_000),
        "jugador": {
            "vida": rng.randint(1, 100),
            "inventario": [f"itm_{i}" for i in range(rng.randint(0, 10))],
        },
        "semilla": rng.randint(0, 2**31 - 1),
    }

    estado_salas = {}
    for sid in range(1, num_salas + 1):
        estado_salas[sid] = {
            "sala": sid,
            "enemigos": [f"ent_{rng.randint(0, 50)}" for _ in range(rng.randint(0, 5))],
            "objetos": [f"itm_{rng.randint(0, 50)}" for _ in range(rng.randint(0, 5))],
            "trampas": [f"trp_{rng.randint(0, 20)}" for _ in range(rng.randint(0, 3))],
            "descripcion": "Una sala húmeda y oscura, llena de ecos. " * rng.randint(1, 3),
        }
    return estado_global, estado_salas


def medir(func, repeticiones=REPETICIONES):
    """Corre func() repeticiones veces y devuelve la mediana del tiempo en segundos."""
    func()  # calentamiento excluido de las muestras
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        func()
        tiempos.append(time.perf_counter() - inicio)
    return mediana(tiempos)


def bench_tamano(num_salas, carpeta_tmp):
    estado_global, estado_salas = generar_estado(num_salas)

    # ids ordenados con el ordenamiento propio (no sorted()), solo para
    # elegir la sala "del medio" que se mide en cargar_sala_bin.
    ids = Vector()
    for sid in estado_salas:
        ids.agregarValor(sid)
    ordenar(ids, _comparar_ids)
    sala_media = ids.obtenerValor(num_salas // 2)

    pares_salas = [(sid, datos) for sid, datos in estado_salas.items()]

    ruta_bin = os.path.join(carpeta_tmp, f"partida_{num_salas}.bin")
    ruta_json = os.path.join(carpeta_tmp, f"partida_{num_salas}.json")

    partida = PartidaBinaria(ruta_bin)
    estado_equivalente = {"global": estado_global, "salas": estado_salas}

    def guardar_bin():
        partida.guardar(estado_global, pares_salas)

    def guardar_json():
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(estado_equivalente, f)

    def cargar_todo_bin():
        partida.cargar_todo()

    def cargar_todo_json():
        with open(ruta_json, "r", encoding="utf-8") as f:
            json.load(f)

    def cargar_sala_bin():
        partida.cargar_sala_binaria(sala_media)

    t_guardar_bin = medir(guardar_bin)
    t_guardar_json = medir(guardar_json)

    tam_bin = os.path.getsize(ruta_bin)
    tam_json = os.path.getsize(ruta_json)

    t_cargar_todo_bin = medir(cargar_todo_bin)
    t_cargar_todo_json = medir(cargar_todo_json)

    t_cargar_sala_bin = medir(cargar_sala_bin)
    # JSON no tiene índice: la única forma de "llegar" a una sala es
    # cargar el archivo completo, así que reutilizamos esa medición.
    t_cargar_sala_json = t_cargar_todo_json

    os.remove(ruta_bin)
    os.remove(ruta_json)

    return {
        "num_salas": num_salas,
        "tam_bin": tam_bin,
        "tam_json": tam_json,
        "t_guardar_bin": t_guardar_bin,
        "t_guardar_json": t_guardar_json,
        "t_cargar_todo_bin": t_cargar_todo_bin,
        "t_cargar_todo_json": t_cargar_todo_json,
        "t_cargar_sala_bin": t_cargar_sala_bin,
        "t_cargar_sala_json": t_cargar_sala_json,
    }


def fmt_tiempo(segundos):
    return f"{segundos * 1000:.3f} ms"


def fmt_bytes(n):
    return f"{n} B"


def fmt_factor(valor_json, valor_bin):
    if valor_bin <= 0:
        return "N/A"
    return f"{valor_json / valor_bin:.1f}x"


def imprimir_tabla(resultados):
    columnas = (12, 22, 14, 14, 10)
    encabezado = (
        f"{'tamaño':<{columnas[0]}} {'operación':<{columnas[1]}} "
        f"{'binario':>{columnas[2]}} {'JSON':>{columnas[3]}} {'factor':>{columnas[4]}}"
    )
    separador = "-" * len(encabezado)

    print(encabezado)
    print(separador)

    for r in resultados:
        etiqueta = f"{r['num_salas']} salas"
        filas = [
            ("guardar", r["t_guardar_bin"], r["t_guardar_json"], fmt_tiempo, fmt_tiempo),
            ("cargar_todo", r["t_cargar_todo_bin"], r["t_cargar_todo_json"], fmt_tiempo, fmt_tiempo),
            ("cargar_sala (media)", r["t_cargar_sala_bin"], r["t_cargar_sala_json"], fmt_tiempo, fmt_tiempo),
            ("tamaño archivo", r["tam_bin"], r["tam_json"], fmt_bytes, fmt_bytes),
        ]
        for i, (op, val_bin, val_json, fmt_bin_fn, fmt_json_fn) in enumerate(filas):
            etq = etiqueta if i == 0 else ""
            print(
                f"{etq:<{columnas[0]}} {op:<{columnas[1]}} "
                f"{fmt_bin_fn(val_bin):>{columnas[2]}} {fmt_json_fn(val_json):>{columnas[3]}} "
                f"{fmt_factor(val_json, val_bin):>{columnas[4]}}"
            )
        print(separador)


def imprimir_resumen(resultados):
    print()
    print("Resumen:")
    for r in resultados:
        bin_kb = r["tam_bin"] / 1024
        json_kb = r["tam_json"] / 1024
        # Se usa cargar_sala_binaria (acceso indexado a una sala) como
        # referencia de "carga": es el caso de uso real del juego (cargar
        # la sala actual, no todo el archivo) y donde el formato binario
        # muestra su ventaja frente a JSON, que siempre debe leerse completo.
        factor_carga = (
            r["t_cargar_sala_json"] / r["t_cargar_sala_bin"]
            if r["t_cargar_sala_bin"] > 0
            else float("inf")
        )
        print(
            f"{r['num_salas']} salas: binario {bin_kb:.1f} KB / JSON {json_kb:.1f} KB "
            f"— carga binaria {factor_carga:.1f}x más rápida que JSON"
        )


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    carpeta_tmp = tempfile.mkdtemp(prefix="cripta_bench_")
    try:
        resultados = [bench_tamano(n, carpeta_tmp) for n in TAMANOS]
        imprimir_tabla(resultados)
        imprimir_resumen(resultados)
    finally:
        try:
            os.rmdir(carpeta_tmp)
        except OSError:
            pass


if __name__ == "__main__":
    main()
