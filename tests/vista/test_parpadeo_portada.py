import random
import pygame
from vista_pygame.render.parpadeo_portada import OJOS, fase_parpadeo, preparar_parpadeos
from vista_pygame.render.portada_animada import _cuadros_atlas, RUTA_PERSONAJES


def test_parpadeos_breves_desfasados_y_sin_azar_del_modelo():
    antes=random.getstate()
    assert all(fase_parpadeo(0,i)==0 for i in range(5))
    for i in range(5):
        inicio=3400+i*527
        assert fase_parpadeo(inicio-1,i)==0
        assert fase_parpadeo(inicio+20,i)==1
        assert fase_parpadeo(inicio+100,i)==2
        assert fase_parpadeo(inicio+170,i)==1
        assert fase_parpadeo(inicio+215,i)==0
        assert all(fase_parpadeo(inicio+100,j)==0 for j in range(5) if j!=i)
    assert random.getstate()==antes


def test_solo_cambian_los_ojos_y_el_dibujo_original_queda_intacto():
    capas=_cuadros_atlas(pygame.image.load(str(RUTA_PERSONAJES)).convert_alpha())
    for i,(frames,_) in enumerate(capas):
        original=frames[0];antes=pygame.image.tobytes(original,'RGBA')
        fases=preparar_parpadeos((original,),i,1)[0]
        cerrado=original.copy();parche,offset=fases[2];cerrado.blit(parche,offset)
        assert pygame.image.tobytes(cerrado,'RGBA')!=antes or i==1
        ojos=tuple(pygame.Rect(r) for r in OJOS[i])
        for y in range(original.get_height()):
            for x in range(original.get_width()):
                if not any(r.collidepoint(x,y) for r in ojos):
                    assert cerrado.get_at((x,y))==original.get_at((x,y))
        assert pygame.image.tobytes(original,'RGBA')==antes
