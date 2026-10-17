"""Los mismos últimos 20 mensajes, con buffer circular y desplazamiento manual."""
from bench.medicion import Fila, medir
from estructuras.array_circular import ArrayCircular

TAMANOS = (20, 20000)
CAPACIDAD = 20


def circular(n):
    buffer = ArrayCircular(CAPACIDAD)
    for i in range(n):
        buffer.agregarValor(i)
    return buffer.listar_en_orden()


def desplazar(n):
    datos = []
    for i in range(n):
        if len(datos) < CAPACIDAD:
            datos.append(i)
        else:
            for j in range(CAPACIDAD - 1):
                datos[j] = datos[j + 1]
            datos[-1] = i
    return datos


def correr():
    filas = []
    for n in TAMANOS:
        assert circular(n) == desplazar(n)
        for nombre, funcion in (("circular", circular), ("desplazamiento", desplazar)):
            movimientos = 0 if nombre == "circular" else max(0, n - CAPACIDAD) * (CAPACIDAD - 1)
            filas.append(Fila("mensajes", nombre, n, medir(funcion, n),
                              f"agregados={n}; desplazamientos={movimientos}"))
    return filas
