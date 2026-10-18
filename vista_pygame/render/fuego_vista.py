"""Resplandor pixelado de la antorcha, precalculado y periódico."""
import pygame


class FuegoAntorcha:
    def __init__(self):
        self._luces=[]
        for radio in (39,41,38,42,40,37,41,40):
            luz=pygame.Surface((96,96),pygame.SRCALPHA)
            pygame.draw.circle(luz,(255,100,24,12),(48,48),radio)
            pygame.draw.circle(luz,(255,137,38,18),(48,48),radio-12)
            pygame.draw.circle(luz,(255,190,92,22),(48,48),radio-24)
            self._luces.append(luz)

    def dibujar(self,pantalla,posicion,cuadro):
        luz=self._luces[cuadro%len(self._luces)]
        pantalla.blit(luz,luz.get_rect(center=posicion))
