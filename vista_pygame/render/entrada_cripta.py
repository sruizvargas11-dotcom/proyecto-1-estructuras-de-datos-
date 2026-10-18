"""Llegada a la cripta con un ciclo de caminata dibujado de espaldas."""
from pathlib import Path
import math
import pygame
from vista_pygame.render.fuego_pixel import cargar_llamas
from vista_pygame.render.transiciones_cripta import suave
from vista_pygame.recursos.temas_cripta import tema_por_cripta

RAIZ=Path(__file__).resolve().parents[2]
_arte=None


def _recursos():
    global _arte
    if _arte is not None:return _arte
    fondo=pygame.image.load(str(RAIZ/'assets/escenarios/osario/entrada.png')).convert()
    fondo=pygame.transform.scale(fondo,(1280,720))
    fondo.fill((173,184,201),special_flags=pygame.BLEND_RGB_MULT)
    # Sombra amplia en los bordes y bajo el arco, preparada una sola vez.
    penumbra=pygame.Surface((1280,720),pygame.SRCALPHA)
    for n in range(26):
        pygame.draw.rect(penumbra,(3,7,14,round(66*(1-n/26))),
                         penumbra.get_rect().inflate(-n*18,-n*10),9)
    fondo.blit(penumbra,(0,0))
    atlas=pygame.image.load(str(RAIZ/'assets/sprites/jugador/caminar_espaldas_vacio.png')).convert_alpha()
    w,h=atlas.get_size();poses=[]
    for i in range(8):
        x0,y0=round(i%4*w/4),round(i//4*h/2)
        im=atlas.subsurface((x0,y0,round((i%4+1)*w/4)-x0,round((i//4+1)*h/2)-y0)).copy()
        rect=im.get_bounding_rect(min_alpha=100);poses.append(im.subsurface(rect).copy())
    alto=max(im.get_height() for im in poses);variantes=[]
    for n in range(20):
        factor=(140-n*2.5)/alto
        frames=[]
        for im in poses:
            frame=pygame.transform.scale(im,(round(im.get_width()*factor),round(im.get_height()*factor)))
            frame.fill((189,193,199),special_flags=pygame.BLEND_RGBA_MULT)
            frames.append(frame)
        variantes.append(tuple(frames))
    _arte=(fondo,tuple(variantes),cargar_llamas(19,33))
    return _arte


class EntradaCripta:
    DURACION=4000
    def __init__(self,fondo_menu,cripta_id="",nombre=""):
        self.tiempo=0
        self.tema=tema_por_cripta(cripta_id,nombre)
        self._fondo,self._pasos,self._fuegos=_recursos()
        ruta=self.tema.recurso(RAIZ/'assets','entrada')
        if ruta!=RAIZ/'assets/escenarios/osario/entrada.png':
            self._fondo=pygame.transform.scale(pygame.image.load(str(ruta)).convert(),(1280,720))
            self._fondo.fill((173,184,201),special_flags=pygame.BLEND_RGB_MULT)
        self._menu=pygame.transform.scale(fondo_menu,(1280,720)) if fondo_menu is not None else self._fondo
        self._velo=pygame.Surface((1280,720),pygame.SRCALPHA)

    @property
    def terminada(self):return self.tiempo>=self.DURACION
    def actualizar(self,dt):self.tiempo=min(self.DURACION,self.tiempo+max(0,dt))

    def dibujar(self,pantalla,assets,error=None):
        t=self.tiempo
        if t<500:
            pantalla.blit(self._menu,(0,0));opacidad=round(255*suave(t/500))
        else:
            pantalla.blit(self._fondo,(0,0))
            u=suave((t-850)/2400)
            paso=int(max(0,t-850)//135)%8
            im=self._pasos[min(19,round(u*19))][paso]
            pie=(640,round(714-201*u))
            sombra=pygame.Surface((im.get_width(),22),pygame.SRCALPHA)
            for n in range(6):pygame.draw.ellipse(sombra,(3,6,12,20+n*13),(n*2,n,im.get_width()-n*4,22-n*3))
            pantalla.blit(sombra,sombra.get_rect(center=pie))
            pantalla.blit(im,im.get_rect(midbottom=pie))
            fuego=self._fuegos[int(t//100)%12]
            for x,y in ((442,295),(836,295)):
                pantalla.blit(fuego,(x-fuego.get_width()//2,y-fuego.get_bounding_rect().bottom))
            titulo=assets.fuente(44).render(self.tema.titulo.upper(),False,self.tema.acento)
            pantalla.blit(titulo,titulo.get_rect(center=(640,65)))
            texto=assets.fuente(20).render(self.tema.frase,False,(174,186,196))
            pantalla.blit(texto,texto.get_rect(center=(640,108)))
            opacidad=round(255*(1-suave((t-500)/450))) if t<950 else round(255*suave((t-3250)/750))
        self._velo.fill((5,8,14,opacidad));pantalla.blit(self._velo,(0,0))
        if self.terminada:
            texto=error or 'Descendiendo a la primera sala…'
            im=assets.fuente(24).render(texto,False,(199,171,112))
            pantalla.blit(im,im.get_rect(center=(640,360)))
            if error:
                ayuda=assets.fuente(18).render('Esc: volver al menú',False,(174,186,196))
                pantalla.blit(ayuda,ayuda.get_rect(center=(640,410)))
