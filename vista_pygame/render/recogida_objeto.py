"""Coreografía de recogida: camina, toma el objeto y regresa sin crear turnos."""
import pygame
from vista_pygame.render.transiciones_cripta import suave


class RecogidaObjeto:
    CONTACTO=900
    DURACION=1800

    def __init__(self,jugador_id,objeto,destino,origen,sprite,base):
        self.jugador_id=jugador_id;self.objeto_id=objeto.instancia_id
        self.destino=destino;self.origen=origen;self.base=base
        self.tiempo=0;self.enviado=False;self.confirmado=False;self.exito=False
        # Mano que se extiende a la derecha del apoyo de los pies.
        self.desplazamiento=(destino[0]-24-(origen[0]+34),destino[1]+8-(origen[1]+100))
        self._objeto=sprite.copy();self._objeto.set_alpha(255)

    @property
    def activa(self):return self.tiempo<self.DURACION

    @property
    def solicita_comando(self):return self.tiempo>=self.CONTACTO and not self.enviado

    def confirmar(self,exito):self.confirmado=True;self.exito=bool(exito)

    def actualizar(self,dt):
        limite=self.DURACION if self.confirmado else self.CONTACTO
        self.tiempo=min(limite,self.tiempo+max(0,dt))

    def pose(self,instancia_id):
        if instancia_id!=self.jugador_id:return self.base.pose(instancia_id)
        if self.tiempo<650:avance=suave(self.tiempo/650)
        elif self.tiempo<1150:avance=1
        else:avance=1-suave((self.tiempo-1150)/650)
        return round(self.desplazamiento[0]*avance),round(self.desplazamiento[1]*avance),False

    def estado_actor(self,instancia_id):
        if instancia_id!=self.jugador_id:return self.base.estado_actor(instancia_id)
        if self.tiempo<650:return 'caminar',int(self.tiempo/650*32)%32
        if self.tiempo<1150:return 'recoger',min(31,int((self.tiempo-650)/500*32))
        return 'caminar',int((self.tiempo-1150)/650*32)%32

    def dibujar_objeto(self,pantalla):
        if not self.exito:return
        u=suave((self.tiempo-self.CONTACTO)/350)
        self._objeto.set_alpha(round(255*(1-u)))
        x=self.destino[0]-round(10*u);y=self.destino[1]-round(38*u)
        pantalla.blit(self._objeto,self._objeto.get_rect(midbottom=(x,y)))
