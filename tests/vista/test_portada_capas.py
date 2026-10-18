import random
import pygame
import pytest
from vista_pygame.render.portada_animada import PortadaAnimada, RAYOS_MS, CICLO_TORMENTA_MS


def test_poses_completas_pies_registrados_y_sin_fondo_pintado():
    p=PortadaAnimada()
    assert p.disponible and len(p._capas)==5
    for cuadros,_ in p._capas:
        assert len(cuadros) in (4,48)
        assert len({im.get_size() for im in cuadros})==1
        assert len({im.get_bounding_rect().bottom for im in cuadros})==1
        for im in cuadros:
            assert im.get_at((0,0)).a==0
            assert im.get_at((im.get_width()-1,im.get_height()-1)).a==0


@pytest.mark.parametrize('inicio',RAYOS_MS)
def test_rayo_tiene_dos_pulsos_y_desaparece(inicio):
    p=PortadaAnimada();p.actualizar(inicio-1)
    assert p.estado_rayo() is None
    p.actualizar(1);assert p.estado_rayo()[1]==1
    p.actualizar(100);assert p.estado_rayo() is None
    p.actualizar(25);assert p.estado_rayo()[1]==.65
    p.actualizar(100);assert p.estado_rayo() is None
    p.actualizar(CICLO_TORMENTA_MS-225)
    assert p.estado_rayo()[1]==1


def test_nubes_y_rayosen_cielo_no_tapan_muro_ni_alteran_azar():
    azar=random.getstate();p=PortadaAnimada();s=pygame.Surface((1280,720))
    p.dibujar(s)
    muro=p._punto(1500,330)
    assert p._mascara_cielo.get_at(muro).a==0
    antes=s.get_at(muro)
    nube=p._nubes[0]
    p.actualizar(9000);p.dibujar(s)
    assert s.get_at(muro)==antes
    assert p._nubes[0] is nube
    assert random.getstate()==azar


def test_render_de_menu_no_reescala_ni_lee_disco_en_cada_frame(monkeypatch):
    p=PortadaAnimada();s=pygame.Surface((1280,720));p.dibujar(s)
    def prohibido(*args,**kwargs):pytest.fail('Recalculó un recurso cacheado')
    monkeypatch.setattr(pygame.transform,'scale',prohibido)
    monkeypatch.setattr(pygame.image,'load',prohibido)
    for _ in range(10):p.actualizar(300);p.dibujar(s)


def test_espadas_y_manos_tienen_margen_en_las_cuatro_poses():
    p=PortadaAnimada()
    for cuadros,_ in p._capas:
        for im in cuadros:
            rect=im.get_bounding_rect()
            assert rect.left>=8
            assert rect.right<=im.get_width()-8


def test_cielo_continua_hasta_las_almenas_sin_triangulo_vacio():
    p=PortadaAnimada();p.ajustar((1672,941))
    # Este punto de cielo quedaba fuera del antiguo polígono aproximado.
    assert p._mascara_cielo.get_at((1490,100)).a==255
    # La torre, en cambio, sigue protegida detrás de su contorno real.
    assert p._mascara_cielo.get_at((525,195)).a==0


def test_respiracion_del_heroe_completa_el_ciclo_en_3600ms():
    p=PortadaAnimada();assert p.cuadro_actor(0)==0
    p.actualizar(900);assert p.cuadro_actor(0)==12
    p.actualizar(2700);assert p.cuadro_actor(0)==0


def test_llamas_sin_parche_rectangular_y_sombras_en_contacto_con_suelo():
    p=PortadaAnimada();p.ajustar((1672,941))
    for frames in (*p._fuegos,p._fuego_heroe):
        for im in frames:
            assert im.get_at((0,0)).a==0
            assert im.get_at((im.get_width()-1,im.get_height()-1)).a==0
    _,_,pies,_=p._actores[0]
    assert p._sombras.get_at((pies[0],pies[1]-3)).a>70
    # Solo el hierro tiene opacidad; el rectángulo que lo contiene no.
    for metal,_ in p._hierros:
        assert pygame.mask.from_surface(metal).count()<metal.get_width()*metal.get_height()*.8
