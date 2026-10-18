"""Escenografía, rejas y luz: solo representación de salidas ya resueltas."""
import math
from pathlib import Path
import pygame
from vista_pygame.render.fuego_pixel import cargar_llamas
from vista_pygame.render.reja_animada import dibujar_rejas
from vista_pygame.recursos.temas_cripta import tema_estado

_fondos=[]
_halo=None
_fuego=None


def dibujar_escenario(pantalla,assets,estado,rect,tiempo,puerta):
    global _halo,_fuego
    final=getattr(estado,'es_sala_salida',False)
    tema=tema_estado(estado)
    ruta=tema.recurso(getattr(assets,'carpeta',Path('.')),'final' if final else 'sala')
    if not ruta.is_file():ruta=getattr(assets,'carpeta',Path('.'))/'escenarios/osario/sala.png'
    if not hasattr(assets,'carpeta') or not ruta.is_file():return False
    clave=(str(ruta),rect.size,estado.sala_id%3)
    fondo=next((im for k,im in _fondos if k==clave),None)
    if fondo is None:
        arte=pygame.image.load(str(ruta)).convert()
        # Misma cuadrícula visual que los actores; sin reducción suavizada.
        arte=pygame.transform.scale(arte,(rect.w//2,rect.h//2))
        fondo=pygame.transform.scale(arte,rect.size)
        tinte=((255,255,255),(235,243,255),(252,239,223))[estado.sala_id%3]
        fondo.fill(tinte,special_flags=pygame.BLEND_RGB_MULT)
        if len(_fondos)>=48:_fondos.clear()
        _fondos.append((clave,fondo))
    pantalla.blit(fondo,rect)
    if final:return True
    if _fuego is None:_fuego=cargar_llamas(12,25)
    if _halo is None:
        _halo=pygame.Surface((160,160),pygame.SRCALPHA)
        for r in range(79,0,-1):pygame.draw.circle(_halo,(242,124,41,round(38*(1-r/80)**2)),(80,80),r)
    for i,(u,v) in enumerate(((.166,.12),(.834,.12))):
        x,y=round(rect.x+u*rect.w),round(rect.y+v*rect.h)
        _halo.set_alpha(round(190+35*math.sin(tiempo*.006+i*1.7)))
        pantalla.blit(_halo,(x-80,y-68))
        im=_fuego[int(tiempo//105+i*3)%12]
        pantalla.blit(im,(x-im.get_width()//2,y-im.get_bounding_rect().bottom))
    # Motas ambientales deterministas: no consumen azar ni tiempo del modelo.
    for n in range(14):
        x=rect.x+80+((n*113+estado.sala_id*23)%max(1,rect.w-160))
        y=rect.y+80+round((n*71+tiempo*.008*(1+n%3))%max(1,rect.h-140))
        tono=tuple(round(c*(.45+.12*math.sin(tiempo*.001+n))) for c in tema.particula)
        pygame.draw.rect(pantalla,tono,(x,y,2,2))
    dibujar_rejas(pantalla,rect,estado.salidas,puerta,piedra=tema.piedra)
    return True


SUELO_OBJETOS=pygame.Rect(155,165,540,255)


def limitar_objeto_al_suelo(punto,tamano_sprite,tamano_texto):
    """El dibujo, la sombra y la etiqueta deben caber sobre las baldosas."""
    margen_x=max(math.ceil(tamano_sprite[0]/2)+5,math.ceil(tamano_texto[0]/2))
    x=max(SUELO_OBJETOS.left+margen_x,min(SUELO_OBJETOS.right-margen_x,punto[0]))
    y=max(SUELO_OBJETOS.top+tamano_sprite[1],min(SUELO_OBJETOS.bottom-4-tamano_texto[1],punto[1]))
    return x,y


def posiciones_objetos(objetos,sala_id):
    puntos=((220,220),(350,220),(480,210),(620,210),
            (220,290),(350,290),(480,330),(620,330),
            (300,395),(410,395),(530,395),(640,395))
    usados=[];resultado=[]
    for i,objeto in enumerate(objetos[:12]):
        n=(sum(ord(c) for c in str(objeto.instancia_id))+sala_id*7)%len(puntos)
        while n in usados:n=(n+1)%len(puntos)
        usados.append(n);resultado.append((i+1,objeto,puntos[n]))
    return resultado


_sombras=[]
def sombra_contacto(pantalla,centro,ancho,alto=14):
    clave=(max(8,round(ancho)),max(4,round(alto)))
    im=next((s for k,s in _sombras if k==clave),None)
    if im is None:
        im=pygame.Surface(clave,pygame.SRCALPHA)
        for n in range(6):
            pygame.draw.ellipse(im,(3,6,12,14+n*18),
                (n,round(n*clave[1]/15),max(1,clave[0]-n*2),max(1,clave[1]-round(n*clave[1]/7))))
        _sombras.append((clave,im))
    pantalla.blit(im,im.get_rect(center=centro))
