"""Fotogramas completos del héroe: sin recortar ni articular miembros."""
from pathlib import Path
import pygame

RUTA = Path(__file__).resolve().parents[2] / 'assets/sprites/jugador/animaciones_heroe.png'
PIES = (96, 160)
OFFSET = (-62, -60)
_cache = None


def _figura(imagen, componente):
    """Aísla una figura completa cuando dos celdas tienen márgenes comunes."""
    rect = componente.get_bounding_rects()[0]
    figura = imagen.subsurface(rect).copy()
    mascara = componente.to_surface(setcolor=(255, 255, 255, 255),
                                    unsetcolor=(255, 255, 255, 0))
    figura.blit(mascara.subsurface(rect), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return figura


class HeroeCompartido:
    def __init__(self, ruta=RUTA):
        ruta = Path(ruta)
        atlas = pygame.image.load(str(ruta)).convert_alpha()
        self._poses = []
        # El archivo artístico no tiene márgenes de fila exactamente iguales.
        for inicio, fin in ((0, .344), (.344, .663), (.663, 1)):
            y0, y1 = round(atlas.get_height()*inicio), round(atlas.get_height()*fin)
            fila = atlas.subsurface((0, y0, atlas.get_width(), y1-y0))
            componentes = pygame.mask.from_surface(fila, 100).connected_components(500)
            componentes = sorted(componentes, key=lambda c: c.get_bounding_rects()[0].x)
            if len(componentes) != 8:
                raise ValueError('La secuencia requiere ocho figuras completas por fila')
            self._poses.append([_figura(fila, c) for c in componentes])
        # Estas dos poses corrigen la espada ausente y la espada duplicada.
        for fila, columna, nombre in ((1, 1, 'ataque_anticipacion.png'),
                                       (2, 3, 'muerte_transicion.png')):
            im = pygame.image.load(str(ruta.parent / nombre)).convert_alpha()
            componente = max(pygame.mask.from_surface(im, 100).connected_components(),
                             key=lambda c: c.count())
            corregida = _figura(im, componente)
            alto = self._poses[fila][columna].get_height()
            ancho = round(corregida.get_width()*alto/corregida.get_height())
            self._poses[fila][columna] = pygame.transform.scale(corregida, (ancho, alto))
        factor = 96 / max(im.get_height() for im in self._poses[0])
        self._dibujados = []
        for fila in self._poses:
            registrados = []
            for figura in fila:
                mini = pygame.transform.scale(figura, (round(figura.get_width()*factor),
                                                       round(figura.get_height()*factor)))
                # Registro por el apoyo del personaje, sin modificar su anatomía.
                puntos = [(x, y) for y in range(max(0, mini.get_height()-3), mini.get_height())
                          for x in range(mini.get_width()) if mini.get_at((x, y)).a > 100]
                centro = round(sum(x for x, _ in puntos)/len(puntos))
                frame = pygame.Surface((256, 192), pygame.SRCALPHA)
                frame.blit(mini, (PIES[0]-centro, PIES[1]-mini.get_height()))
                registrados.append(frame)
            self._dibujados.append(tuple(registrados))
        self._caminata=[]
        camino=ruta.parent/'caminar_frente.png'
        if camino.is_file():
            hoja=pygame.image.load(str(camino)).convert_alpha();aw,ah=hoja.get_size()
            dibujos=[]
            for n in range(8):
                x0,y0=round(n%4*aw/4),round(n//4*ah/2)
                im=hoja.subsurface((x0,y0,round((n%4+1)*aw/4)-x0,round((n//4+1)*ah/2)-y0))
                dibujos.append(im.subsurface(im.get_bounding_rect(min_alpha=100)).copy())
            factor=96/max(im.get_height() for im in dibujos)
            for im in dibujos:
                im=pygame.transform.scale(im,(round(im.get_width()*factor),round(im.get_height()*factor)))
                pies=[x for y in range(im.get_height()-3,im.get_height()) for x in range(im.get_width()) if im.get_at((x,y)).a>100]
                frame=pygame.Surface((256,192),pygame.SRCALPHA)
                frame.blit(im,(96-round(sum(pies)/len(pies)),160-im.get_height()))
                self._caminata.append(frame)
        self._recoger=[]
        recogida=ruta.parent/'recoger_objeto.png'
        if recogida.is_file():
            hoja=pygame.image.load(str(recogida)).convert_alpha();aw,ah=hoja.get_size()
            dibujos=[]
            for n in range(8):
                x0,y0=round(n%4*aw/4),round(n//4*ah/2)
                im=hoja.subsurface((x0,y0,round((n%4+1)*aw/4)-x0,round((n//4+1)*ah/2)-y0)).copy()
                mascara=pygame.mask.from_surface(im,100).connected_component()
                limpia=pygame.Surface(im.get_size(),pygame.SRCALPHA)
                mascara.to_surface(surface=limpia,setsurface=im,unsetcolor=(0,0,0,0))
                dibujos.append(limpia.subsurface(limpia.get_bounding_rect(min_alpha=100)).copy())
            factor=96/max(im.get_height() for im in dibujos[:2])
            for im in dibujos:
                im=pygame.transform.scale(im,(round(im.get_width()*factor),round(im.get_height()*factor)))
                pies=[x for y in range(im.get_height()-3,im.get_height()) for x in range(im.get_width()) if im.get_at((x,y)).a>100]
                frame=pygame.Surface((256,192),pygame.SRCALPHA)
                frame.blit(im,(96-round(sum(pies)/len(pies)),160-im.get_height()))
                self._recoger.append(frame)
            # La penúltima pose tiene una empuñadura ambigua junto a la vaina:
            # usar el dibujo final, que muestra una sola espada inequívoca.
            self._recoger[6]=self._recoger[7]
        self._cuadros = []

    def cuadros(self, estado):
        for nombre, frames in self._cuadros:
            if nombre == estado:
                return frames
        fila = 1 if estado == 'ataque' else 2 if estado == 'muerte' else 0
        poses = self._caminata if estado=='caminar' and self._caminata else self._dibujados[fila]
        if estado=='recoger' and self._recoger:poses=self._recoger
        cantidad = 32 if estado in ('ataque','caminar','recoger') else 48
        # Ocho dibujos reales por estado; las repeticiones controlan su duración.
        # No son interpolaciones ni fotogramas nuevos inventados por el render.
        frames = tuple(poses[min(7, i*8//cantidad)] for i in range(cantidad))
        self._cuadros.append((estado, frames))
        return frames


def heroe_compartido():
    global _cache
    if _cache is None:
        _cache = HeroeCompartido()
    return _cache
