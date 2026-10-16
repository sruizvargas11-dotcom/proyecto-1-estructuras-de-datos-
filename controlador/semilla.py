"""Genera y valida las semillas de las partidas.

Una partida nueva obtiene su semilla de SystemRandom y la guarda en la
bitácora y el archivo binario. Al cargar o reproducir, se reutiliza la
semilla guardada.

SystemRandom es independiente del generador de Reloj; crear una semilla
no consume los valores aleatorios que usa el modelo.
"""
import random

SEMILLA_MIN = 0
SEMILLA_MAX = 2 ** 32 - 1


def validar_semilla(semilla):
    """Devuelve la semilla si es un entero en [0, 2**32 - 1]; si no, ValueError."""
    if type(semilla) is not int or not SEMILLA_MIN <= semilla <= SEMILLA_MAX:
        raise ValueError(
            f"La semilla debe ser un entero entre {SEMILLA_MIN} y {SEMILLA_MAX}."
        )
    return semilla


def generar_semilla(generador=None):
    """Semilla nueva para una partida nueva.

    generador: solo para pruebas (un objeto con randint). Por defecto SystemRandom.
    """
    if generador is None:
        generador = random.SystemRandom()
    return validar_semilla(generador.randint(SEMILLA_MIN, SEMILLA_MAX))
