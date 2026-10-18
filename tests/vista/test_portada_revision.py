import random
import pygame
import pytest
from tests.vista.test_menu_criptas import _crear,_criptas,_tecla
from vista_pygame.escenas.menu_criptas import COLOR_PLACEHOLDER_NOMBRE
from vista_pygame.render.portada_animada import PortadaAnimada
from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.render.rig_actores import cuadros_jugador,cuadros_rata
from controlador.controlador_pygame import ControladorPygame
from adaptadores.datos_offline import DatosOffline


@pytest.mark.parametrize('nombre',['',' ','    ','\t\n'])
def test_nombre_vacio_o_espacios_no_inicia_por_enter_ni_clic(nombre):
    e,contexto,c=_crear(_criptas(1));e._nombre=nombre;e._foco=0
    e.manejar_evento(_tecla(pygame.K_RETURN))
    e.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=e._rect_fila_pantalla(0).center))
    assert not c.llamadas_iniciar and not contexto.cambios_escena
    assert e._foco==-1 and e._error_nombre and not e._iniciando


def test_borrar_nombre_muestra_placeholder_gris_y_etiqueta_permanece():
    e,_,c=_crear(_criptas(1));e._nombre='José Fabio';e._nombre_seleccionado=False
    e.manejar_evento(_tecla(pygame.K_a,mod=pygame.KMOD_CTRL))
    e.manejar_evento(_tecla(pygame.K_BACKSPACE))
    assert e._nombre==''
    pantalla=pygame.Surface((1280,720));e.dibujar(pantalla)
    area=e._layout.nombre_rect
    assert any(tuple(pantalla.get_at((x,y)))[:3]==COLOR_PLACEHOLDER_NOMBRE
               for x in range(area.x,area.right) for y in range(area.y,area.bottom))
    e._foco=0;e.manejar_evento(_tecla(pygame.K_RETURN))
    assert not c.llamadas_iniciar
    for ch in 'José':e.manejar_evento(_tecla(pygame.K_a,unicode=ch))
    e._foco=0;e.manejar_evento(_tecla(pygame.K_RETURN))
    assert c.llamadas_iniciar==[('cripta-0','José',None)]


def test_controlador_grafico_tambien_rechaza_nombre_vacio(tmp_path):
    c=ControladorPygame(DatosOffline(),partidas_dir=str(tmp_path))
    with pytest.raises(ValueError,match='obligatorio'):
        c.iniciar_partida('cripta-01','   ',42)
    assert c.sesion is None


@pytest.mark.parametrize('tamano',[(1280,720),(1920,1080),(1000,800),(1600,900)])
def test_portada_cubre_toda_la_superficie_sin_franjas(tamano):
    portada=PortadaAnimada();pantalla=pygame.Surface(tamano);pantalla.fill((255,0,255))
    portada.dibujar(pantalla)
    w,h=tamano
    assert portada._fondo.get_size()==tamano
    for punto in ((0,0),(w-1,0),(0,h-1),(w-1,h-1)):
        assert pantalla.get_at(punto)[:3]!=(255,0,255)
    fondo=portada._fondo;portada.dibujar(pantalla)
    assert portada._fondo is fondo


def test_ambiente_animado_repetible_no_usa_azar_del_modelo():
    azar=random.getstate();a,b=PortadaAnimada(),PortadaAnimada()
    a.actualizar(800);b.actualizar(300);b.actualizar(500)
    uno=pygame.Surface((1280,720));dos=uno.copy();a.dibujar(uno);b.dibujar(dos)
    assert pygame.image.tobytes(uno,'RGB')==pygame.image.tobytes(dos,'RGB')
    a.actualizar(200);a.dibujar(uno)
    assert pygame.image.tobytes(uno,'RGB')!=pygame.image.tobytes(dos,'RGB')
    assert random.getstate()==azar


@pytest.mark.parametrize('estado',['reposo','caminar','ataque','golpeado','muerte'])
def test_uniones_del_cuerpo_son_continuas_en_todos_los_cuadros(estado):
    a=CargadorAssets();sprite=a.sprite_jugador('parado','S')
    for imagen,_ in cuadros_jugador(sprite,estado):
        componentes=pygame.mask.from_surface(imagen).connected_components()
        areas=[c.count() for c in componentes]
        # Las brasas pueden ser componentes de 1 píxel. Los miembros,
        # la cabeza y el arma tienen que pertenecer al cuerpo principal.
        assert max(areas)/sum(areas)>.94,(estado,areas)


def test_rata_no_tiene_patas_cortadas_al_moverse():
    a=CargadorAssets();sprite=a.sprite_enemigo('ent_rata_gigante','rastreador')
    for estado in ('reposo','ataque','golpeado'):
        for imagen,_ in cuadros_rata(sprite,estado):
            areas=[c.count() for c in pygame.mask.from_surface(imagen).connected_components()]
            assert max(areas)/sum(areas)>.97
