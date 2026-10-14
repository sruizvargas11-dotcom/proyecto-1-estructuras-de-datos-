"""Semilla de partida (plan v4, B3 ROL 1).

Reglas:
- Se genera automáticamente al iniciar una partida NUEVA. El jugador nunca la elige
  y nunca se hardcodea.
- Se guarda en el encabezado de la bitácora (BitacoraPartida) y en el archivo binario.
- Al cargar una partida o reproducir un replay se REUTILIZA la semilla guardada: en ese
  caso solo se valida, no se genera otra.

La generación usa random.SystemRandom (entropía del sistema operativo), que es una
instancia independiente: no toca el generador global del módulo random ni el
random.Random(semilla) del Reloj. Esa es la única fuente no determinista del juego, y
por eso vive en el controlador y no en el modelo.
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
