"""Compatibilidad de la API previa: delega al único motor de replay."""
from controlador.controlador_replay import reproducir as reproducir_bitacora


def reproducir(fuente, ruta, cache=None, cache_size=25):
    return reproducir_bitacora(ruta, fuente, cache, cache_size=cache_size).partida
