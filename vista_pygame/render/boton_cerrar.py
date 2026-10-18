"""Botón de cierre de hierro oxidado con una X roja pixelada."""
import pygame
from vista_pygame.render.panel_mazmorra import PanelMazmorra
_panel=PanelMazmorra()


def dibujar_cerrar(pantalla,rect):
    _panel.dibujar(pantalla,rect)
    centro=rect.center;radio=max(6,min(rect.w,rect.h)//5)
    for signo in (-1,1):
        a=(centro[0]-radio,centro[1]-signo*radio)
        b=(centro[0]+radio,centro[1]+signo*radio)
        pygame.draw.line(pantalla,(35,8,11),(a[0]+1,a[1]+2),(b[0]+1,b[1]+2),5)
        pygame.draw.line(pantalla,(225,74,67),a,b,3)
