"""Regresión: mapas grandes no invaden vida/equipo y siguen la sala actual."""
import pygame
import pytest
from vista_pygame.render.render_sala import dibujar_minimapa
from vista_pygame.config_vista import COLOR_ORO


@pytest.mark.parametrize('actual',[1,25,50])
def test_mapa_de_50_salas_se_recorta_y_sigue_al_jugador(actual):
    im=pygame.Surface((500,500));im.fill((220,0,220));antes=im.copy()
    rect=pygame.Rect(80,30,292,100)
    layout=[(i,0,1-i) for i in range(1,51)]+[(51,30,0),(52,-30,0)]
    dibujar_minimapa(im,rect,layout,list(range(1,actual+1)),actual,None)
    # La barra de vida, equipo y las zonas exteriores conservan cada píxel.
    for region in (pygame.Rect(0,0,500,rect.top),pygame.Rect(0,rect.bottom,500,500-rect.bottom),
                   pygame.Rect(0,0,rect.left,500),pygame.Rect(rect.right,0,500-rect.right,500)):
        assert pygame.image.tobytes(im.subsurface(region),'RGB')==pygame.image.tobytes(antes.subsurface(region),'RGB')
    assert im.get_at(rect.center)[:3]==COLOR_ORO
    assert im.get_clip()==im.get_rect()


def test_minimapa_respeta_y_restaura_un_recorte_preexistente():
    im=pygame.Surface((400,240));im.fill((220,0,220))
    clip=pygame.Rect(100,80,80,70);im.set_clip(clip)
    dibujar_minimapa(im,pygame.Rect(20,20,300,150),[(1,0,0),(2,0,-1)],[1],1,None)
    assert im.get_clip()==clip
    assert im.get_at((20,20))[:3]==(220,0,220)
    dibujar_minimapa(im,pygame.Rect(20,20,300,150),[],[],1,None)
    assert im.get_clip()==clip
