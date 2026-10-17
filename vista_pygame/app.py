"""Bucle principal de la vista Pygame: ventana, reloj de FPS, cambio de
escenas y cierre controlado. No contiene reglas del juego: eso vive en el
modelo, detrás de ControladorPygame (hilo de fondo, ver ese módulo).

Las escenas se registran en una lista indexada por las constantes de
config_vista.py (ESCENA_MENU, ESCENA_PARTIDA, ...), nunca un dict.
"""
import pygame

from vista_pygame.config_vista import (
    ALTO_LOGICO, ANCHO_LOGICO, CANTIDAD_ESCENAS, ESCENA_FIN_PARTIDA, ESCENA_INVENTARIO,
    ESCENA_MENU, ESCENA_PARTIDA, ESCENA_PAUSA, FPS_OBJETIVO, TITULO_VENTANA,
)
from vista_pygame.controlador_pygame import ControladorPygame
from vista_pygame.escenas.menu_criptas import EscenaMenuCriptas
from vista_pygame.escenas.partida import EscenaPartida
from vista_pygame.stubs_temporales import (
    CargadorAssetsTemporal, EscenaFinPartidaTemporal, EscenaInventarioTemporal,
    EscenaPausaTemporal, GestorAudioTemporal,
)


class Contexto:
    """Lo que recibe cada escena (ver CONTRATOS.md §1): controlador, assets,
    audio y cambiar_escena. La app real detrás de cambiar_escena no es parte
    del contrato, por eso queda privada."""

    def __init__(self, controlador, assets, audio, app):
        self.controlador = controlador
        self.assets = assets
        self.audio = audio
        self._app = app

    def cambiar_escena(self, id_escena, datos=None):
        self._app.cambiar_escena(id_escena, datos)


class AppPygame:
    def __init__(self, fuente, carpeta_cache=None, cache_size=25, partidas_dir="partidas"):
        pygame.init()
        self._pantalla = pygame.display.set_mode((ANCHO_LOGICO, ALTO_LOGICO))
        pygame.display.set_caption(TITULO_VENTANA)
        self._reloj = pygame.time.Clock()

        controlador = ControladorPygame(fuente, carpeta_cache, cache_size, partidas_dir)
        assets = CargadorAssetsTemporal()
        audio = GestorAudioTemporal()
        self._contexto = Contexto(controlador, assets, audio, self)

        self._escenas = [None] * CANTIDAD_ESCENAS
        self._escenas[ESCENA_MENU] = EscenaMenuCriptas(self._contexto)
        self._escenas[ESCENA_PARTIDA] = EscenaPartida(self._contexto)
        self._escenas[ESCENA_INVENTARIO] = EscenaInventarioTemporal(self._contexto)
        self._escenas[ESCENA_PAUSA] = EscenaPausaTemporal(self._contexto)
        self._escenas[ESCENA_FIN_PARTIDA] = EscenaFinPartidaTemporal(self._contexto)

        self._actual = ESCENA_MENU
        self._escenas[self._actual].al_entrar()
        self._corriendo = True

    def cambiar_escena(self, id_escena, datos=None):
        self._escenas[self._actual].al_salir()
        self._actual = id_escena
        self._escenas[self._actual].al_entrar(datos)

    def ejecutar(self):
        """Todas las llamadas a pygame ocurren aquí, en el hilo principal."""
        try:
            while self._corriendo:
                dt_ms = self._reloj.tick(FPS_OBJETIVO)
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        self._corriendo = False
                    else:
                        self._escenas[self._actual].manejar_evento(evento)
                self._escenas[self._actual].actualizar(dt_ms)
                self._escenas[self._actual].dibujar(self._pantalla)
                pygame.display.flip()
        finally:
            # Cierre ordenado: pide salir y espera (join) a que el hilo de
            # modelo termine de verdad, nunca lo abandona a medias.
            try:
                self._contexto.controlador.salir()
            finally:
                pygame.quit()


def ejecutar(fuente, carpeta_cache=None, cache_size=25, partidas_dir="partidas"):
    AppPygame(fuente, carpeta_cache, cache_size, partidas_dir).ejecutar()
