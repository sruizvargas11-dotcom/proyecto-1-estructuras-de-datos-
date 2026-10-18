import pygame
from vista_pygame.render.integracion_ojo import REGION, remodelar_cuenca, preparar_integracion
from vista_pygame.render.ojo_torre import cargar_ojo
from vista_pygame.render.portada_animada import RUTA_LIMPIA, PortadaAnimada


def test_remodelar_no_cambia_el_resto_de_la_torre_ni_el_fondo_original():
    original=pygame.image.load(str(RUTA_LIMPIA)).convert()
    antes=pygame.image.tobytes(original,'RGB')
    mascara=pygame.Surface(original.get_size(),pygame.SRCALPHA)
    base,cielo=remodelar_cuenca(original,mascara)
    assert pygame.image.tobytes(original,'RGB')==antes
    w,h=original.get_size()
    for rect in ((0,0,490,h),(563,0,w-563,h),(490,0,73,62),(490,162,73,h-162)):
        assert pygame.image.tobytes(base.subsurface(rect),'RGB')==pygame.image.tobytes(original.subsurface(rect),'RGB')
    assert base.get_at((526,120))!=original.get_at((526,120))
    assert cielo.get_at((526,120)).a==255


def test_luz_reflejada_cambia_con_el_parpadeo_sin_regenerarse_por_frame():
    p=PortadaAnimada();frames=p._ojo_integrado
    assert preparar_integracion(p._base,p._mascara_original,cargar_ojo()) is frames
    # Una parte de la piedra bajo el ojo recibe menos luz al cerrar los párpados.
    punto=(526-REGION.x,154-REGION.y)
    assert frames[0].get_at(punto).a==frames[4].get_at(punto).a==255
    assert frames[0].get_at(punto).r>frames[4].get_at(punto).r
    assert all(im.get_at((0,0)).a==0 for im in frames)
