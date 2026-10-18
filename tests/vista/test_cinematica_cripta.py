"""Integración offline: las transiciones descartan teclas y no crean turnos."""
import time
import pygame
import pytest
from adaptadores.datos_offline import DatosOffline
from herramientas.generar_cripta_prueba import generar
from vista_pygame.app import AppPygame
from vista_pygame.config_vista import ESCENA_MENU, ESCENA_PARTIDA
from vista_pygame.render.transiciones_cripta import TransicionSala, EfectoTrampa


def esperar(condicion):
    limite=time.monotonic()+10
    while not condicion() and time.monotonic()<limite:time.sleep(.002)
    assert condicion(), 'El controlador no publicó el resultado'


@pytest.fixture
def app(tmp_path):
    generar(tmp_path/'datos')
    a=AppPygame(DatosOffline(str(tmp_path/'datos')),carpeta_cache=str(tmp_path/'cache'),
                partidas_dir=str(tmp_path/'partidas'))
    esperar(lambda:not a._escenas[ESCENA_MENU]._cargando)
    yield a
    if a._contexto._hilo_inicio is not None:a._contexto._hilo_inicio.join(timeout=10)
    a._contexto.controlador.salir()


def tecla(escena,key,mod=0):
    escena.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=key,mod=mod))


def terminar(escena,controlador):
    limite=time.monotonic()+10
    while time.monotonic()<limite:
        escena.actualizar(50)
        if not escena.bloqueada and not escena._animaciones.ocupada and not controlador.esperando_red():return
        time.sleep(.002)
    pytest.fail('La secuencia no desbloqueó la partida')


def test_entrada_salas_trampa_ataque_y_reja_no_encolan_acciones(app):
    c=app._contexto.controlador
    app._contexto.iniciar_cripta(('cripta-prueba','Ada',999))
    e=app._escenas[ESCENA_PARTIDA]
    e.actualizar(3999)
    for key in (pygame.K_r,pygame.K_i,pygame.K_SPACE,pygame.K_ESCAPE)*5:tecla(e,key)
    assert c.sesion is None and app._actual==ESCENA_PARTIDA
    e.actualizar(1);esperar(lambda:not app._contexto.iniciando())
    terminar(e,c)
    assert c.estado().acciones_jugador==0
    tiempo=c.estado().tiempo
    tecla(e,pygame.K_UP);e.actualizar(419)
    assert c.estado().sala_id==1 and c.estado().tiempo==tiempo
    for key in (pygame.K_r,pygame.K_i,pygame.K_UP)*10:tecla(e,key)
    terminar(e,c)
    assert c.estado().sala_id==2 and c.estado().acciones_jugador==1
    # El mensaje real de la trampa de la sala 2 alimenta el efecto visual.
    assert e._efecto_trampa.texto.startswith('¡Una trampa se activa!')
    antes=c.estado().acciones_jugador
    tecla(e,pygame.K_SPACE);esperar(lambda:not c.esperando_red());e.actualizar(0)
    assert e._animaciones.ocupada
    for _ in range(10):tecla(e,pygame.K_r)
    terminar(e,c)
    assert c.estado().acciones_jugador==antes+1
    for key in (pygame.K_UP,pygame.K_UP,pygame.K_r):tecla(e,key);terminar(e,c)
    antes=c.estado().acciones_jugador
    tecla(e,pygame.K_RIGHT,pygame.KMOD_SHIFT)
    esperar(lambda:not c.esperando_red());e.actualizar(0)
    assert e._puerta_direccion=='E' and e._puerta_ms==0
    assert not next(x for x in c.estado().salidas if x.direccion=='E').cerrada
    for key in (pygame.K_r,pygame.K_i,pygame.K_SPACE)*10:tecla(e,key)
    terminar(e,c)
    assert c.estado().acciones_jugador==antes+1 and e._puerta_ms==700


@pytest.mark.parametrize('fallo_modelo',[False,True])
def test_error_al_iniciar_permite_regresar_al_menu(app,monkeypatch,fallo_modelo):
    c=app._contexto.controlador
    def fallar(*args):raise OSError('Datos de prueba no disponibles')
    if fallo_modelo:
        monkeypatch.setattr(c,'iniciar_partida',lambda *args:None)
        monkeypatch.setattr(c,'error_pendiente',lambda:'Datos de prueba no disponibles')
    else:monkeypatch.setattr(c,'iniciar_partida',fallar)
    app._contexto.iniciar_cripta(('ausente','Ada',9))
    e=app._escenas[ESCENA_PARTIDA];e.actualizar(4000)
    esperar(lambda:not app._contexto.iniciando());e.actualizar(0)
    assert e._error_mostrado=='Datos de prueba no disponibles'
    tecla(e,pygame.K_ESCAPE)
    assert app._actual==ESCENA_MENU and c.sesion is None
    esperar(lambda:not app._escenas[ESCENA_MENU]._cargando)


def test_fundido_espera_hasta_recibir_sala_y_no_avanza_con_dt_negativo():
    from types import SimpleNamespace
    t=TransicionSala();t.salir(pygame.Surface((1280,720)))
    t.actualizar(-50);assert t.tiempo==0
    t.actualizar(420);assert t.fase=='espera'
    t.actualizar(10000);assert t.fase=='espera'
    t.entrar(SimpleNamespace(sala_nombre='Osario',sala_id=4))
    assert t.nombre=='Osario' and t.identificador=='4'
    t.actualizar(1049);assert t.activa
    t.actualizar(1);assert not t.activa and t.fondo is None
    trampa=EfectoTrampa();trampa.iniciar('Dardos')
    trampa.actualizar(-50);assert trampa.tiempo==0
    trampa.actualizar(trampa.DURACION);assert not trampa.activa
