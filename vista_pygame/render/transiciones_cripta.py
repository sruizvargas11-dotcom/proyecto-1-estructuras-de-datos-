"""Fundidos y trampas de presentación; nunca consumen turnos del modelo."""
import math
import pygame
from vista_pygame.recursos.temas_cripta import tema_estado


def suave(t):
    t=max(0,min(1,t));return t*t*(3-2*t)


class TransicionSala:
    def __init__(self):
        self.fase=None;self.tiempo=0;self.fondo=None;self.nombre='';self.identificador='';self.acento=(218,188,125)

    @property
    def activa(self):return self.fase is not None

    def salir(self,fondo):
        self.fondo=fondo.copy();self.fase='salida';self.tiempo=0

    def entrar(self,estado):
        self.fase='entrada';self.tiempo=0
        self.nombre=estado.sala_nombre;self.identificador=str(estado.sala_id)
        self.acento=tema_estado(estado).acento

    def actualizar(self,dt):
        self.tiempo+=max(0,dt)
        if self.fase=='salida' and self.tiempo>=420:
            self.fase='espera';self.tiempo=0
        elif self.fase=='entrada' and self.tiempo>=1050:
            self.fase=None;self.fondo=None

    def dibujar(self,pantalla,assets):
        if not self.activa:return
        if self.fase in ('salida','espera'):
            if self.fondo is not None:pantalla.blit(self.fondo,(0,0))
            opacidad=255 if self.fase=='espera' else round(255*suave(self.tiempo/420))
        else:opacidad=round(255*(1-suave(self.tiempo/850)))
        velo=pygame.Surface(pantalla.get_size(),pygame.SRCALPHA)
        velo.fill((5,8,14,opacidad));pantalla.blit(velo,(0,0))
        if self.fase=='entrada':
            alpha=round(255*min(suave(self.tiempo/220),1-suave((self.tiempo-650)/400)))
            capa=pygame.Surface(pantalla.get_size(),pygame.SRCALPHA)
            titulo=assets.fuente(48).render(self.nombre,False,self.acento)
            sub=assets.fuente(20).render(f'SALA {self.identificador}',False,(148,162,179))
            capa.blit(titulo,titulo.get_rect(center=(640,280)))
            capa.blit(sub,sub.get_rect(center=(640,335)))
            pygame.draw.line(capa,(126,98,55),(480,360),(800,360),1)
            capa.set_alpha(alpha);pantalla.blit(capa,(0,0))


# Se conserva el punto de importación público de las escenas y pruebas.
from vista_pygame.render.cinematica_trampa import EfectoTrampa
