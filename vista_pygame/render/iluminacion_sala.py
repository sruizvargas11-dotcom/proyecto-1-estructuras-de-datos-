"""Penumbra de la sala y luz cálida, sin modificar el estado del juego."""
import math
import pygame


class IluminacionSala:
    def __init__(self):
        self.nivel=0.0
        self.tiempo=0
        self._base=None
        self._radial=None
        self._calor=None

    def actualizar(self, dt, encendida):
        dt=max(0,dt);self.tiempo+=dt
        destino=1.0 if encendida else 0.0
        paso=dt/420
        self.nivel=min(destino,self.nivel+paso) if destino>self.nivel else max(destino,self.nivel-paso)

    @staticmethod
    def _luz(radio, oscuridad):
        im=pygame.Surface((radio*2,radio*2),pygame.SRCALPHA)
        im.fill((4,7,14,oscuridad))
        for r in range(radio,0,-2):
            alpha=round(oscuridad*(r/radio)**1.6)
            pygame.draw.circle(im,(4,7,14,alpha),(radio,radio),r)
        return im

    def dibujar(self, pantalla, rect, posicion, fuentes_suelo=()):
        if self._base is None:
            self._base=pygame.Surface(rect.size,pygame.SRCALPHA)
            self._base.fill((4,7,14,145))
            sconce=self._luz(104,145)
            for u in (.166,.834):
                self._base.blit(sconce,(round(rect.w*u)-104,round(rect.h*.12)-104),special_flags=pygame.BLEND_RGBA_MIN)
            self._radial=self._luz(245,145)
            self._calor=pygame.Surface((490,490))
            for r in range(245,0,-2):
                f=(1-r/245)**2
                pygame.draw.circle(self._calor,(round(22*f),round(12*f),round(2*f)),(245,245),r)
        oscuridad=self._base.copy()
        if self.nivel>0:
            radio=max(1,round((234+4*math.sin(self.tiempo*.009))*self.nivel))
            luz=pygame.transform.scale(self._radial,(radio*2,radio*2))
            x,y=posicion
            oscuridad.blit(luz,(round(x-rect.x-radio),round(y-rect.y-radio)),special_flags=pygame.BLEND_RGBA_MIN)
        for x,y in fuentes_suelo:
            luz=pygame.transform.scale(self._radial,(340,340))
            oscuridad.blit(luz,(round(x-rect.x-170),round(y-rect.y-170)),special_flags=pygame.BLEND_RGBA_MIN)
        pantalla.blit(oscuridad,rect)
        if self.nivel>0:
            calor=pygame.transform.scale(self._calor,(radio*2,radio*2))
            clip=pantalla.get_clip();pantalla.set_clip(rect)
            pantalla.blit(calor,(round(posicion[0]-radio),round(posicion[1]-radio)),special_flags=pygame.BLEND_RGB_ADD)
            pantalla.set_clip(clip)
