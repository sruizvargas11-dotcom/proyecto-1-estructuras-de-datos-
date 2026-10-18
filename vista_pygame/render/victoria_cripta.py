"""Salida hacia el exterior: solo presentación de una victoria ya resuelta."""
import math
import pygame
from vista_pygame.render.transiciones_cripta import suave
from vista_pygame.recursos.temas_cripta import tema_por_cripta


class SalidaCripta:
    DURACION=5200

    def __init__(self,assets,equipo,fondo,cripta_id="",nombre=""):
        self.tiempo=0;self.equipo=equipo
        self._fondo_sala=fondo.copy()
        self.tema=tema_por_cripta(cripta_id,nombre)
        self._exterior=pygame.image.load(str(self.tema.recurso(assets.carpeta,'exterior'))).convert()
        # La misma escala de píxel del resto del juego.
        self._exterior=pygame.transform.scale(pygame.transform.scale(self._exterior,(640,360)),(1280,720))
        self._pasos=assets.cuadros_espalda_equipo(equipo)
        self._variantes=[]
        for alto in range(85,166,4):
            tamano=round(alto*(1.3 if equipo&2 else 1))
            factor=tamano/max(im.get_height() for im in self._pasos)
            self._variantes.append(tuple(pygame.transform.scale(im,(max(1,round(im.get_width()*factor)),
                                                                    max(1,round(im.get_height()*factor)))) for im in self._pasos))

    @property
    def terminada(self):return self.tiempo>=self.DURACION

    @property
    def opacidad_menu(self):return round(255*suave((self.tiempo-4400)/800))

    def actualizar(self,dt):self.tiempo=min(self.DURACION,self.tiempo+max(0,dt))

    def _dibujar_exterior(self,pantalla,final=False):
        pantalla.blit(self._exterior,(0,0))
        avance=1 if final else max(0,min(1,(self.tiempo-1250)/2800))
        # Velocidad constante sobre los escalones y frenada corta al llegar.
        avance=avance if avance<.9 else .9+.1*suave((avance-.9)/.1)
        fase=0 if avance>=1 else int(max(0,self.tiempo-1250)//95)%8
        variante=round((1-avance)*(len(self._variantes)-1))
        heroe=self._variantes[variante][fase]
        x=640+round(18*avance)
        y=650-round(345*avance)
        if 0<avance<1:y+=round(math.sin(fase*math.pi/2)*1.5)
        sombra=pygame.Surface((100,24),pygame.SRCALPHA)
        pygame.draw.ellipse(sombra,(6,12,17,105),(0,2,100,18))
        ancho=round(70-30*avance)
        sombra=pygame.transform.scale(sombra,(ancho,12))
        pantalla.blit(sombra,sombra.get_rect(center=(x,y+2)))
        pantalla.blit(heroe,heroe.get_rect(midbottom=(x,y)))

    def fotograma_final(self):
        pantalla=pygame.Surface((1280,720));self._dibujar_exterior(pantalla,final=True)
        return pantalla

    def dibujar(self,pantalla,assets):
        if self.tiempo<900:
            pantalla.blit(self._fondo_sala,(0,0))
            titulo=assets.fuente(38).render('LA SALIDA',False,(248,227,174))
            pantalla.blit(titulo,titulo.get_rect(center=(420,85)))
        else:
            self._dibujar_exterior(pantalla)
            if self.tiempo<1250:
                anterior=self._fondo_sala.copy()
                anterior.set_alpha(round(255*(1-suave((self.tiempo-900)/350))))
                pantalla.blit(anterior,(0,0))
