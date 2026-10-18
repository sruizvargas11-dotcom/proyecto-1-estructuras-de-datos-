import random
import pygame
import pytest

from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.render.rig_actores import cuadros_jugador
from vista_pygame.render.animaciones import ColaAnimaciones, DURACION_ATAQUE_MS
from vista_pygame.render.fuego_vista import FuegoAntorcha
from controlador.controlador_pygame import EventoAtaque
from vista_pygame.render.render_actores import dibujar_jugador, dibujar_enemigos
from tests.vista.test_render_enemigos import _estado,_enemigo


def _bytes(imagen):return pygame.image.tobytes(imagen,'RGBA')


def test_fuego_y_respiracion_cambian_cuadros_y_conservan_original():
    a=CargadorAssets();original=a.sprite_jugador('parado','S');antes=_bytes(original)
    uno,_=a.fotograma_jugador('reposo',0);dos,_=a.fotograma_jugador('reposo',6)
    assert _bytes(uno)!=_bytes(dos)
    assert _bytes(original)==antes
    assert a.fotograma_jugador('reposo',48)[0] is uno


def test_ataque_mueve_brazo_y_conserva_los_pies_cerca_del_suelo():
    a=CargadorAssets()
    # Las regiones de espada y torso cambian en relación con los pies,
    # no son la misma imagen desplazada.
    uno,_=a.fotograma_jugador('ataque',0);dos,_=a.fotograma_jugador('ataque',4)
    assert _bytes(uno)!=_bytes(dos)
    assert abs(uno.get_bounding_rect().bottom-dos.get_bounding_rect().bottom)<=8


def test_muerte_tiene_reaccion_rodillas_y_desplome():
    a=CargadorAssets();sprite=a.sprite_jugador('parado','S')
    cuadros=cuadros_jugador(sprite,'muerte')
    assert len(cuadros)==18
    imagenes=[cuadros[i][0] for i in (0,6,11,17)]
    assert len(set(_bytes(im) for im in imagenes))==4
    assert imagenes[-1].get_bounding_rect().width>imagenes[-1].get_bounding_rect().height
    assert imagenes[0].get_bounding_rect().height>imagenes[0].get_bounding_rect().width


def test_rata_cabeza_patas_y_cola_varian_con_desfase_por_instancia():
    a=CargadorAssets()
    uno,_=a.fotograma_enemigo('ent_rata_gigante','rastreador','reposo',0)
    dos,_=a.fotograma_enemigo('ent_rata_gigante','rastreador','reposo',3)
    assert _bytes(uno)!=_bytes(dos)
    c=ColaAnimaciones()
    assert c.estado_actor('rata-1')!=c.estado_actor('rata-2')


def test_cuadros_precargados_no_transforman_ni_leen_disco_por_frame(monkeypatch):
    a=CargadorAssets()
    primero=a.fotograma_jugador('reposo',0)[0]
    a.fotograma_enemigo('ent_rata_gigante','rastreador','reposo',0)
    def prohibido(*args,**kwargs):pytest.fail('Recalculó una animación ya preparada')
    monkeypatch.setattr(pygame.transform,'rotate',prohibido)
    monkeypatch.setattr(pygame.transform,'scale',prohibido)
    monkeypatch.setattr(pygame.image,'load',prohibido)
    for i in range(100):
        assert isinstance(a.fotograma_jugador('reposo',i)[0],pygame.Surface)
        assert isinstance(a.fotograma_enemigo('ent_rata_gigante','rastreador','reposo',i)[0],pygame.Surface)
    assert a.fotograma_jugador('reposo',0)[0] is primero


def test_movimiento_ambiental_es_determinista_y_no_usa_azar_del_modelo():
    azar=random.getstate();a,b=ColaAnimaciones(),ColaAnimaciones()
    a.actualizar(720);b.actualizar(120);b.actualizar(600)
    assert a.estado_actor('jugador')==b.estado_actor('jugador')
    assert a.estado_actor('rata-1')==b.estado_actor('rata-1')
    assert random.getstate()==azar


def test_ataque_se_prepara_antes_del_desplazamiento_y_cambia_la_postura():
    c=ColaAnimaciones();c.preparar([('jugador',(100,300)),('rata',(500,200))])
    c.agregar_desde_eventos([EventoAtaque(atacante_id='jugador',objetivo_id='rata',dano=3)])
    c.actualizar(30)
    assert c.pose('jugador')[0]<0  # anticipación hacia atrás
    assert c.estado_actor('jugador')[0]=='ataque'
    c.actualizar(160)
    assert c.pose('jugador')[0]>0
    assert c.estado_actor('jugador')[0]=='caminar'
    assert c.estado_actor('rata')[0]=='reposo'
    c.actualizar(round(DURACION_ATAQUE_MS*.6)-190)
    assert c.estado_actor('rata')[0]=='golpeado'


@pytest.mark.parametrize('tipo,rol',[('ent_rata_gigante','rastreador'),('no_existe','errante'),('no_existe','otro')])
def test_render_animado_respeta_la_foto_de_estado(tipo,rol):
    a=CargadorAssets();c=ColaAnimaciones();c.actualizar(500)
    estado=_estado(enemigos_activos=[_enemigo(1,tipo_id=tipo,comportamiento=rol)])
    antes=repr(estado);pantalla=pygame.Surface((1280,720))
    dibujar_jugador(pantalla,a,estado,'Ada',c)
    dibujar_enemigos(pantalla,a,estado,1,c)
    assert repr(estado)==antes


def test_resplandor_es_periodico_y_visible():
    fuego=FuegoAntorcha();a=pygame.Surface((200,200));b=a.copy();c=a.copy()
    fuego.dibujar(a,(100,100),0);fuego.dibujar(b,(100,100),8)
    fuego.dibujar(c,(100,100),3)
    assert _bytes(a)==_bytes(b) and _bytes(a)!=_bytes(c)
    assert a.get_at((100,100)).r>0


def test_reposo_respira_el_pecho_sin_mover_espada_ni_palo_de_antorcha():
    a=CargadorAssets();sprite=pygame.image.load(str(a.carpeta/'sprites/jugador/idle.png'))
    cuadros=[im for im,_ in cuadros_jugador(sprite,'reposo')]
    colores_equipo={(201,212,224),(184,134,46),(123,83,48)}
    def equipo(im):
        return {(x,y,tuple(im.get_at((x,y)))[:3])
                for x in range(im.get_width()) for y in range(im.get_height())
                if tuple(im.get_at((x,y)))[:3] in colores_equipo and im.get_at((x,y)).a}
    original=equipo(cuadros[0])
    assert original
    assert all(equipo(im)==original for im in cuadros)
    pecho=pygame.Rect(70,34,32,36)
    assert _bytes(cuadros[0].subsurface(pecho))!=_bytes(cuadros[3].subsurface(pecho))


def test_muerte_se_apoya_en_el_suelo_y_termina_inmovil_sin_partes_sueltas():
    a=CargadorAssets();sprite=pygame.image.load(str(a.carpeta/'sprites/jugador/idle.png'))
    cuadros=[im for im,_ in cuadros_jugador(sprite,'muerte')]
    assert len({im.get_bounding_rect().bottom for im in cuadros})==1
    assert _bytes(cuadros[-1])==_bytes(cuadros[-2])==_bytes(cuadros[-3])
    # La inclinación del cuerpo debe acompañar a la cabeza y a las piernas:
    # un único conjunto tumbado, sin fragmentos sobre el suelo.
    ultimo=cuadros[-1]
    componentes=pygame.mask.from_surface(ultimo).connected_components()
    assert len(componentes)==1
    assert ultimo.get_bounding_rect().width>=2*ultimo.get_bounding_rect().height
