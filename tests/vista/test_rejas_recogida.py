"""Rejas con perspectiva, suelo seguro y una única recogida al tocar el objeto."""
from types import SimpleNamespace
import pygame
import pytest
from vista_pygame.render.reja_animada import fotogramas_reja,CANTIDAD_CUADROS
from vista_pygame.render.escenografia_sala import posiciones_objetos,limitar_objeto_al_suelo,SUELO_OBJETOS
from vista_pygame.render.recogida_objeto import RecogidaObjeto
from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.config_vista import ESCENA_PARTIDA
from tests.vista.test_cinematica_cripta import app,esperar,tecla,terminar


@pytest.mark.parametrize('direccion',['N','S','E','O'])
@pytest.mark.parametrize('llave',[False,True])
def test_reja_tiene_secuencia_completa_y_reutiliza_los_cuadros(direccion,llave,monkeypatch):
    cuadros,pos=fotogramas_reja(direccion,(760,470),llave)
    assert len(cuadros)==CANTIDAD_CUADROS==16
    assert len({im.get_size() for im in cuadros})==1
    cantidad=lambda im:pygame.mask.from_surface(im).count()
    assert cantidad(cuadros[0])>cantidad(cuadros[7])>cantidad(cuadros[-1])==0
    assert 0<pos[0]<760 and 0<pos[1]<470
    def prohibido(*args,**kwargs):pytest.fail('Recalculó la reja durante la reproducción')
    monkeypatch.setattr(pygame.transform,'scale',prohibido)
    assert fotogramas_reja(direccion,(760,470),llave)[0] is cuadros


def test_las_rejas_laterales_siguen_la_inclinacion_real_de_los_umbrales():
    from vista_pygame.render.reja_animada import _plano
    oeste=_plano('O',(760,470));este=_plano('E',(760,470))
    assert oeste[3][1]<oeste[2][1]
    assert este[3][1]>este[2][1]


def test_doce_objetos_caben_con_sprite_sombra_y_nombre_sin_reordenarlos():
    objetos=[SimpleNamespace(instancia_id=f'obj-{i}') for i in range(12)]
    original=list(objetos)
    for sala in range(30):
        posiciones=posiciones_objetos(objetos,sala)
        assert [i for i,o,p in posiciones]==list(range(1,13))
        assert [o for i,o,p in posiciones]==objetos==original
        assert len({p for i,o,p in posiciones})==12
        for i,o,p in posiciones:
            x,y=limitar_objeto_al_suelo(p,(44,44),(116,20))
            assert SUELO_OBJETOS.contains(pygame.Rect(x-22,y-44,44,44))
            assert SUELO_OBJETOS.contains(pygame.Rect(x-58,y+4,116,20))
            assert SUELO_OBJETOS.contains(pygame.Rect(x-27,y-4,54,10))


def test_recogida_con_rechazo_conserva_el_objeto_y_regresa():
    base=SimpleNamespace(pose=lambda i:(0,0,False),estado_actor=lambda i:('reposo',0))
    r=RecogidaObjeto('j',SimpleNamespace(instancia_id='pocion'),(400,300),(200,350),pygame.Surface((20,30)),base)
    r.actualizar(899);assert not r.solicita_comando
    r.actualizar(5000);assert r.solicita_comando and r.tiempo==900
    r.enviado=True;r.actualizar(5000)
    assert r.tiempo==900 and not r.solicita_comando
    r.confirmar(False);r.actualizar(10000)
    assert not r.exito and not r.activa and r.pose('j')==(0,0,False)


def test_recoger_solo_envia_una_accion_al_llegar_y_no_por_cada_fotograma(app):
    c=app._contexto.controlador
    app.cambiar_escena(ESCENA_PARTIDA,('cripta-prueba','Ada',999))
    e=app._escenas[ESCENA_PARTIDA]
    esperar(lambda:c.estado() is not None);e.actualizar(0)
    foto=c.estado();objeto=foto.objetos_suelo[0].instancia_id
    tecla(e,pygame.K_r);e.actualizar(899)
    assert e._recogida is not None and c.estado().acciones_jugador==0
    assert len(c.estado().objetos_suelo)==len(foto.objetos_suelo)
    for key in (pygame.K_r,pygame.K_UP,pygame.K_i)*15:tecla(e,key)
    e.actualizar(1);esperar(lambda:not c.esperando_red());e.actualizar(0)
    assert e._recogida.exito
    assert c.estado().acciones_jugador==1
    assert any(o.instancia_id==objeto for o in c.estado().inventario)
    assert not any(o.instancia_id==objeto for o in c.estado().objetos_suelo)
    terminar(e,c);tiempo=c.estado().tiempo
    for _ in range(10):e.actualizar(1000)
    assert c.estado().acciones_jugador==1 and c.estado().tiempo==tiempo


@pytest.mark.parametrize('familia',['guardian','errante','esqueleto','necrofago','trasgo','generico'])
def test_modelos_completos_tienen_apoyo_y_cuadros_distintos(familia):
    a=CargadorAssets();criatura=a._criatura(familia,'desconocido')
    assert criatura is not None and len(criatura.poses)==8
    for pose in criatura.poses:
        rect=pose.get_bounding_rect(min_alpha=100)
        assert rect.left>0 and rect.right<pose.get_width() and rect.bottom==128
    assert pygame.image.tobytes(criatura.poses[0],'RGBA')!=pygame.image.tobytes(criatura.poses[5],'RGBA')
