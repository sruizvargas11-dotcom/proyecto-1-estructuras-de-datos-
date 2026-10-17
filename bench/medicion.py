"""Herramientas comunes de medición: cronometrar, sacar la mediana, imprimir tabla."""
from dataclasses import dataclass
from time import perf_counter

REPETICIONES = 5


@dataclass
class Fila:
    caso: str        # experimento ("cache", "historial"...)
    variante: str    # propia o alternativa ("ListaLRU", "lista_plana"...)
    n: int           # tamaño de la entrada
    ms: float        # tiempo mediano en milisegundos
    extra: str = ""  # contadores o datos extra ("aciertos=950")

    contadores: tuple = ()  # métricas de operaciones fuera del cronómetro


def mediana(valores):
    """Calcula la mediana con inserción propia, sin recurrir al ordenamiento de Python."""
    orden = []
    for v in valores:
        i = len(orden)
        orden.append(v)
        while i > 0 and orden[i - 1] > v:
            orden[i] = orden[i - 1]
            i -= 1
        orden[i] = v
    if not orden:
        raise ValueError("No hay muestras.")
    medio = len(orden) // 2
    return orden[medio] if len(orden) % 2 else (orden[medio - 1] + orden[medio]) / 2


def medir(accion, *argumentos, repeticiones=REPETICIONES):
    """Corre `accion(*argumentos)` varias veces y devuelve la mediana en ms.

    Si el experimento necesita una estructura nueva en cada vuelta, la
    función `accion` la crea por dentro (así cada repetición parte limpia).
    """
    if type(repeticiones) is not int or repeticiones < 1:
        raise ValueError("Las repeticiones deben ser positivas.")
    accion(*argumentos)  # calentamiento excluido de las muestras
    tiempos = []
    for _ in range(repeticiones):
        inicio = perf_counter()
        accion(*argumentos)
        tiempos.append((perf_counter() - inicio) * 1000)
    return mediana(tiempos)


def imprimir_tabla(filas):
    """Imprime las filas como tabla de texto alineada."""
    print(f"{'caso':<16}{'variante':<18}{'n':>8}{'ms (med)':>12}  extra")
    print("-" * 68)
    for f in filas:
        print(f"{f.caso:<16}{f.variante:<18}{f.n:>8}{f.ms:>12.3f}  {f.extra}")