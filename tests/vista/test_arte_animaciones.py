import random
from types import SimpleNamespace
import pygame
import pytest

from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.render.animaciones import ColaAnimaciones, DURACION_ATAQUE_MS
from vista_pygame.controlador_pygame import EventoAtaque, EventoMensaje
from tests.vista.test_render_enemigos import _estado, _enemigo
from vista_pygame.escenas.partida import EscenaPartida
from vista_pygame.config_vista import ESCENA_FIN_PARTIDA


def _cola():
    c = ColaAnimaciones()
    c.preparar([('jugador', (100, 300)), ('rata', (500, 200))])
    return c


def _ataque(atacante='jugador', objetivo='rata', dano=7):
    return EventoAtaque(atacante_id=atacante, objetivo_id=objetivo, dano=dano)


def test_png_se_escala_sin_suavizado_y_cachea():
    a = CargadorAssets()
    original = pygame.image.load(str(a.carpeta/'sprites/jugador/idle.png'))
    sprite = a._imagen(('sprites/jugador/idle.png',))
    assert sprite.get_size() == (original.get_width()*2, original.get_height()*2)
    for x in range(original.get_width()):
        for y in range(original.get_height()):
            assert sprite.get_at((x*2, y*2)) == original.get_at((x,y))
    assert a._imagen(('sprites/jugador/idle.png',)) is sprite


@pytest.mark.parametrize('rol', ['guardián', 'errante', 'rastreador', 'desconocido'])
def test_tipo_desconocido_tiene_fallback(rol):
    a = CargadorAssets()
    assert isinstance(a.sprite_enemigo('no_existe', rol), pygame.Surface)


def test_archivo_corrupto_se_salta_sin_perder_la_familia(tmp_path):
    carpeta=tmp_path/'sprites/objetos';carpeta.mkdir(parents=True)
    (carpeta/'corrupto.png').write_bytes(b'no es png')
    imagen=pygame.Surface((10,12), pygame.SRCALPHA);imagen.fill((10,20,30,255))
    pygame.image.save(imagen,str(carpeta/'arma.png'))
    sprite=CargadorAssets(tmp_path).sprite_objeto('corrupto','arma')
    assert sprite.get_size() == (20,24) and sprite.get_at((4,4)) == (10,20,30,255)


def test_no_relee_disco_por_frame(monkeypatch):
    a=CargadorAssets();sprite=a.sprite_enemigo('no_existe', 'errante')
    def prohibido(*args):
        pytest.fail('Un recurso ya resuelto no debe volver a leer el disco')
    monkeypatch.setattr(pygame.image, 'load', prohibido)
    for _ in range(20):
        assert a.sprite_enemigo('no_existe', 'errante') is sprite


def test_assets_ausentes_y_claves_invalidas_no_rompen(tmp_path):
    a=CargadorAssets(tmp_path)
    assert a.sprite_objeto('../../fuera', '../../fuera').get_width() > 0
    assert isinstance(a.icono('no_existe'), pygame.Surface)
    assert isinstance(a.sprite_efecto('veneno'), pygame.Surface)
    assert a.fuente(18) is a.fuente(18)


def test_ataque_se_acerca_golpea_y_regresa_sin_azar():
    antes=random.getstate();c=_cola();evento=_ataque();c.agregar_desde_eventos([evento])
    assert c.pose('jugador') == (0,0,False)
    impacto=round(DURACION_ATAQUE_MS*.6)
    c.actualizar(impacto)
    assert c.pose('jugador')[0] > 0 and c.pose('rata')[2]
    c.actualizar(DURACION_ATAQUE_MS-impacto)
    assert not c.ocupada and c.pose('jugador') == (0,0,False)
    assert evento.dano == 7 and random.getstate() == antes


def test_cola_fifo_y_dt_grande_respetan_los_ataques():
    c=_cola();c.agregar_desde_eventos([_ataque(),_ataque('rata','jugador',4)])
    c.actualizar(DURACION_ATAQUE_MS+round(DURACION_ATAQUE_MS*.6))
    assert c.pose('rata')[0] < 0 and c.pose('jugador')[2]
    c.actualizar(10000)
    assert not c.ocupada


def test_animacion_es_identica_para_los_mismos_eventos():
    a,b=_cola(),_cola();a.agregar_desde_eventos([_ataque()]);b.agregar_desde_eventos([_ataque()])
    a.actualizar(190);b.actualizar(90);b.actualizar(100)
    assert a.pose('jugador') == b.pose('jugador')
    superficies=[pygame.Surface((800,600)) for _ in range(2)]
    for c,s in zip((a,b),superficies): c.dibujar(s)
    assert pygame.image.tobytes(superficies[0],'RGBA') == pygame.image.tobytes(superficies[1],'RGBA')


def test_limpiar_descarta_toda_la_cola_y_dt_negativo_no_avanza():
    c=_cola();c.agregar_desde_eventos([_ataque(),_ataque()]);c.actualizar(-5)
    assert c.pose('jugador') == (0,0,False)
    c.limpiar();c.actualizar(100)
    assert not c.ocupada and c.pose('rata') == (0,0,False)


def test_ataque_fuera_de_pantalla_y_mensaje_no_inventan_objetivo():
    c=_cola();c.agregar_desde_eventos([_ataque('invisible'),EventoMensaje(texto='algo')])
    assert not c.ocupada


class ControladorFalso:
    def __init__(self, estado):
        self.foto=estado;self.eventos=[];self.nombre_jugador='Ada';self.enviados=[]
    def estado(self): return self.foto
    def eventos_nuevos(self):
        eventos,self.eventos=self.eventos,[]
        return eventos
    def error_pendiente(self): return None
    def topologia_cripta(self): return []
    def esperando_red(self): return False
    def resumen_fin(self): return 'resumen'
    def enviar_comando(self, texto): self.enviados.append(texto)


def _escena():
    c=ControladorFalso(_estado(enemigos_activos=[_enemigo(1)]));cambios=[]
    contexto=SimpleNamespace(controlador=c, audio=SimpleNamespace(reproducir_sfx=lambda tipo:None),
                             cambiar_escena=lambda *args:cambios.append(args))
    escena=EscenaPartida(contexto);escena.al_entrar()
    return escena,c,cambios


def test_golpe_final_se_ve_antes_de_quitar_enemigo_y_abrir_fin(monkeypatch):
    e,c,cambios=_escena()
    # Esta prueba aísla la cola de ataques; la captura real se cubre en test_salida_y_rejas.
    monkeypatch.setattr(e,'_capturar_fin',lambda estado:None)
    c.foto=_estado();c.foto.estado='victoria';c.foto.tiempo=100
    c.eventos=[_ataque(objetivo='e-1')]
    e.actualizar(0)
    assert e._animaciones.ocupada and e._estado_visual.enemigos_activos
    assert not cambios
    e.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,mod=0))
    assert not c.enviados
    e.actualizar(1000)
    assert cambios == [(ESCENA_FIN_PARTIDA,'resumen')]
    assert not e._estado_visual.enemigos_activos


@pytest.mark.parametrize('texto',['Partida cargada: prueba.sav','Lees el pergamino: el tiempo retrocede'])
def test_carga_o_pergamino_cancelan_animacion_aunque_el_tiempo_no_baje(texto):
    e,c,_=_escena();c.eventos=[_ataque(objetivo='e-1')];e.actualizar(0)
    assert e._animaciones.ocupada
    c.foto=_estado();c.foto.tiempo=900
    c.eventos=[EventoMensaje(tiempo=900,texto=texto)];e.actualizar(0)
    assert not e._animaciones.ocupada and e._estado_visual is c.foto
