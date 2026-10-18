"""Fuego pixel art compartido por portada y héroe, sin azar del modelo."""
from pathlib import Path
import pygame

def cuadros_llama(ancho, alto, atlas):
    """Fuego en la boca del brasero; no incluye un rectángulo de iluminación."""
    cuadros = []
    for n in range(12):
        s = pygame.Surface((ancho+12, alto+12), pygame.SRCALPHA)
        cx, base = s.get_width()//2, alto+5
        aw,ah=atlas.get_size();x0=round(n%4*aw/4);y0=round(n//4*ah/3)
        celda=atlas.subsurface((x0,y0,round((n%4+1)*aw/4)-x0,
                               round((n//4+1)*ah/3)-y0)).copy()
        componentes=pygame.mask.from_surface(celda,100).connected_components()
        principal=max(componentes,key=lambda c:c.count())
        mascara=principal.to_surface(setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
        celda.blit(mascara,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        rect=celda.get_bounding_rect();factor=min(ancho/rect.w,alto/rect.h)
        fuego=pygame.transform.scale(celda.subsurface(rect),
            (max(1,round(rect.w*factor)),max(1,round(rect.h*factor))))
        s.blit(fuego,(cx-fuego.get_width()//2,base-fuego.get_height()+1))
        cuadros.append(s)
    return tuple(cuadros)


_cache=[]
def cargar_llamas(ancho,alto):
    for clave,frames in _cache:
        if clave==(ancho,alto):return frames
    atlas=pygame.image.load(str(Path(__file__).resolve().parents[2]/'assets/ui/portada/fuego_menu_pixelart.png')).convert_alpha()
    frames=cuadros_llama(ancho,alto,atlas)
    _cache.append(((ancho,alto),frames))
    return frames
