"""Ojo de la torre con párpados dibujados: no comprime el iris al parpadear."""
from pathlib import Path
import pygame

RUTA = Path(__file__).resolve().parents[2] / 'assets/ui/ojo_torre_parpadeo.png'
_cuadros = None


def cargar_ojo():
    global _cuadros
    if _cuadros is not None:
        return _cuadros
    atlas = pygame.image.load(str(RUTA)).convert_alpha()
    w, h = atlas.get_size()
    figuras = []
    for n in range(8):
        x0, y0 = round(n%4*w/4), round(n//4*h/2)
        celda = atlas.subsurface((x0, y0, round((n%4+1)*w/4)-x0,
                                  round((n//4+1)*h/2)-y0)).copy()
        rect = celda.get_bounding_rect(min_alpha=100)
        figuras.append(celda.subsurface(rect).copy())
    # La escala y el lienzo son comunes a las ocho poses del mismo ojo.
    factor = 62 / max(im.get_width() for im in figuras)
    resultado = []
    for figura in figuras:
        mini = pygame.transform.scale(figura, (round(figura.get_width()*factor),
                                               round(figura.get_height()*factor)))
        frame = pygame.Surface((68, 48), pygame.SRCALPHA)
        frame.blit(mini, mini.get_rect(center=(34, 24)))
        resultado.append(frame)
    _cuadros = tuple(resultado)
    return _cuadros


def cuadro_ojo(tiempo_ms):
    instante = max(0, tiempo_ms) % 18000
    for inicio in (5400, 12300):
        t = instante-inicio
        if 0 <= t < 320:
            return min(7, int(t//40))
    return 0
