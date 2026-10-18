"""Arrastrar una llave es presentación; AB sigue validando y abriendo la puerta."""
import math
import pygame
from vista_pygame.render.panel_mazmorra import PanelMazmorra
from vista_pygame.render.boton_cerrar import dibujar_cerrar
from vista_pygame.render.transiciones_cripta import suave


def rect_candado(direccion, sala_rect):
    from vista_pygame.render.reja_animada import PORTALES
    puntos=next(p for d,p in PORTALES if d==direccion)
    x=sum(p[0] for p in puntos)/4
    techo=(puntos[0][1]+puntos[1][1])/2
    suelo=(puntos[2][1]+puntos[3][1])/2
    y=techo+(suelo-techo)*.56
    return pygame.Rect(round(sala_rect.x+x*sala_rect.w/760)-13,
                       round(sala_rect.y+y*sala_rect.h/470)-13,26,26)


def modelo_candado(apertura=0):
    im=pygame.Surface((160,200),pygame.SRCALPHA)
    cuerpo=pygame.Surface((160,170),pygame.SRCALPHA)
    levantar=round(25*suave(apertura))
    # Arco de hierro con sus dos caras, desengancha el extremo derecho.
    puntos=[(43,81),(43,35-levantar),(53,20-levantar),(78,13-levantar),
            (101,23-levantar),(109,38-levantar),(109,70-round(40*apertura))]
    puntos=[(x,y+30) for x,y in puntos]
    pygame.draw.lines(im,(10,16,22),False,puntos,16)
    pygame.draw.lines(im,(106,116,121),False,puntos,10)
    pygame.draw.lines(im,(174,183,184),False,[(x-2,y-2) for x,y in puntos],2)
    # Cuerpo biselado, óxido y remaches; todos pertenecen al mismo modelo.
    pygame.draw.polygon(cuerpo,(8,13,19),((18,75),(31,63),(124,63),(142,79),(142,151),(128,165),(30,165),(18,153)))
    pygame.draw.polygon(cuerpo,(76,83,85),((24,78),(34,70),(122,70),(135,81),(135,147),(124,157),(35,157),(24,148)))
    pygame.draw.rect(cuerpo,(40,47,51),(35,80,91,65))
    pygame.draw.line(cuerpo,(132,141,142),(35,74),(122,74),2)
    for i in range(90):
        x=29+(i*43)%101;y=79+(i*31)%73
        if i%3==0:pygame.draw.rect(cuerpo,(87,51,31),(x,y,2+i%4,2))
    for x,y in ((33,79),(126,79),(33,147),(126,147)):
        pygame.draw.circle(cuerpo,(12,18,23),(x,y),5)
        pygame.draw.circle(cuerpo,(140,145,139),(x-1,y-1),3)
    pygame.draw.circle(cuerpo,(8,13,18),(80,107),10)
    pygame.draw.polygon(cuerpo,(8,13,18),((76,110),(84,110),(87,132),(73,132)))
    pygame.draw.arc(cuerpo,(149,119,66),(67,94,26,28),.1,3.0,2)
    im.blit(cuerpo,(0,30))
    return im


class InteraccionCandado:
    INSERCION=420
    APERTURA=1100

    def __init__(self,salida):
        self.direccion=salida.direccion
        self.llave_tipo_id=getattr(salida,'llave_tipo_id',None)
        self.fase='elegir';self.tiempo=0;self.enviado=False
        self.arrastrada=None;self.pos=(640,355);self.inicio=self.pos
        self.mensaje='Arrastra una llave hasta la cerradura.'
        self.cerrar=pygame.Rect(946,95,28,28)
        self.ranura=pygame.Rect(600,292,80,95)
        self._panel=PanelMazmorra()
        self._modelos=tuple(pygame.transform.scale(modelo_candado(n/15),(256,320)) for n in range(16))

    @property
    def terminada(self):return self.fase in ('terminada','cancelada')

    @property
    def solicita_comando(self):return self.fase=='insertando' and self.tiempo>=self.INSERCION and not self.enviado

    @staticmethod
    def llaves(estado):return [o for o in estado.inventario if o.clase=='llave']

    def tarjetas(self,estado):
        return [(o,pygame.Rect(350+(i%5)*116,524+(i//5)*80,108,72))
                for i,o in enumerate(self.llaves(estado))]

    def manejar_evento(self,evento,estado):
        if self.fase!='elegir':return
        if evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1:
            if self.cerrar.collidepoint(evento.pos):self.fase='cancelada';return
            for objeto,r in self.tarjetas(estado):
                if r.collidepoint(evento.pos):self.arrastrada=objeto;self.pos=evento.pos;return
        elif evento.type==pygame.MOUSEMOTION and self.arrastrada is not None:self.pos=evento.pos
        elif evento.type==pygame.MOUSEBUTTONUP and evento.button==1 and self.arrastrada is not None:
            self.pos=evento.pos
            if self.ranura.collidepoint(evento.pos):
                if self.llave_tipo_id is not None and self.arrastrada.tipo_id==self.llave_tipo_id:
                    self.fase='insertando';self.tiempo=0;self.inicio=evento.pos
                    self.mensaje='La llave encaja…'
                    return
                self.mensaje='Esta llave no corresponde a este candado.'
            self.arrastrada=None

    def actualizar(self,dt):
        if self.fase in ('insertando','abriendo'):
            self.tiempo+=max(0,dt)
            if self.fase=='abriendo' and self.tiempo>=self.APERTURA:self.fase='terminada'

    def confirmar(self,abierta,mensaje=None):
        if abierta:self.fase='abriendo';self.tiempo=0;self.mensaje='El cerrojo cede.'
        else:
            self.fase='elegir';self.tiempo=0;self.enviado=False;self.arrastrada=None
            self.mensaje=mensaje or 'No se pudo abrir. Comprueba la llave.'

    def dibujar(self,pantalla,assets,estado):
        velo=pygame.Surface((1280,720),pygame.SRCALPHA);velo.fill((3,7,13,205))
        pantalla.blit(velo,(0,0))
        self._panel.dibujar(pantalla,pygame.Rect(322,78,664,622))
        titulo=assets.fuente(28).render(f'Puerta {self.direccion} · Cerradura',False,(219,191,142))
        pantalla.blit(titulo,titulo.get_rect(center=(640,113)))
        if self.fase=='elegir':dibujar_cerrar(pantalla,self.cerrar)
        u=min(1,self.tiempo/600) if self.fase=='abriendo' else 0
        modelo=self._modelos[min(15,round(u*15))]
        pantalla.blit(modelo,modelo.get_rect(midtop=(640,108)))
        if self.arrastrada is not None:
            imagen=assets.sprite_objeto(self.arrastrada.tipo_id,self.arrastrada.clase)
            imagen=pygame.transform.scale(imagen,(imagen.get_width()*3,imagen.get_height()*3))
            x,y=self.pos
            if self.fase in ('insertando','espera','abriendo'):
                v=suave(min(1,self.tiempo/self.INSERCION)) if self.fase=='insertando' else 1
                x=self.inicio[0]+(640-self.inicio[0])*v;y=self.inicio[1]+(344-self.inicio[1])*v
                angulo=-90*min(1,self.tiempo/420) if self.fase=='abriendo' else 0
                imagen=pygame.transform.rotate(imagen,angulo)
                if self.fase=='abriendo':imagen.set_alpha(round(255*(1-suave((self.tiempo-650)/350))))
            pantalla.blit(imagen,imagen.get_rect(center=(round(x),round(y))))
        texto=assets.fuente(18).render(self.mensaje,False,(224,215,195))
        pantalla.blit(texto,texto.get_rect(center=(640,463)))
        tarjetas=self.tarjetas(estado)
        if not tarjetas:
            texto=assets.fuente(18).render('No tienes llaves. Puedes volver a explorar con la X.',False,(178,178,173))
            pantalla.blit(texto,texto.get_rect(center=(640,561)))
        for objeto,r in tarjetas:
            self._panel.dibujar(pantalla,r,objeto is self.arrastrada)
            im=assets.sprite_objeto(objeto.tipo_id,objeto.clase)
            pantalla.blit(im,im.get_rect(center=(r.centerx,r.y+23)))
            nombre=objeto.nombre
            while assets.fuente(13).size(nombre)[0]>98 and len(nombre)>1:nombre=nombre[:-2]+'…'
            t=assets.fuente(13).render(nombre,False,(223,216,195))
            pantalla.blit(t,t.get_rect(center=(r.centerx,r.y+56)))
