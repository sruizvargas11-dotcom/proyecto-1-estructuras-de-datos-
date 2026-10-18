"""Tipografía pixelada regular, sin adornos que dificulten la lectura."""
from pathlib import Path
import pygame


class FuenteCripta:
    def __init__(self,tamano):
        carpeta=Path(__file__).resolve().parents[2]/'assets/fuentes'
        ruta=carpeta/'PixelifySans.ttf'
        self._font=pygame.font.Font(str(ruta) if ruta.is_file() else None,tamano)
        self._cache=[]

    def size(self,texto):
        w,h=self._font.size(str(texto));return w,h

    def get_height(self):return self._font.get_height()
    def get_linesize(self):return self._font.get_linesize()

    def render(self,texto,antialias,color,background=None):
        texto=str(texto);color=tuple(color)[:3];clave=(texto,color,background)
        for k,im in self._cache:
            if k==clave:return im
        im=self._font.render(texto,False,color,background)
        if len(self._cache)>=96:self._cache.clear()
        self._cache.append((clave,im));return im


def fuente_pixel_legible(tamano):
    """Trazo pixelado regular, sin negrita ni relieve sobre los glifos."""
    ruta=Path(__file__).resolve().parents[2]/'assets/fuentes/PixelifySans.ttf'
    fuente=pygame.font.Font(str(ruta) if ruta.is_file() else None,tamano)
    fuente.set_bold(False)
    return fuente
