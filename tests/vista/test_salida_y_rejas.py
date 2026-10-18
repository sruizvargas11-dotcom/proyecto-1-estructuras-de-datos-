"""Salida solar y coherencia de puertas sin alterar las reglas del modelo."""
from types import SimpleNamespace
import pygame
import pytest
from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.render.reja_animada import dibujar_rejas, fotogramas_reja, pared_tapiada
from vista_pygame.controlador_pygame import SalidaVisual, construir_estado
from vista_pygame.config_vista import ESCENA_PARTIDA, ESCENA_FIN_PARTIDA
from tests.vista.test_cinematica_cripta import app, esperar


@pytest.mark.parametrize('direccion',['N','S','E','O'])
def test_reja_cerrada_se_ve_sin_tener_llave_y_abierta_desaparece(direccion):
    pygame.init();pygame.display.set_mode((1,1))
    rect=pygame.Rect(0,0,760,470)
    cerrada=SalidaVisual(direccion,2,'Sala',True,False,'itm_llave')
    superficie=pygame.Surface(rect.size,pygame.SRCALPHA)
    dibujar_rejas(superficie,rect,[cerrada],solo_existentes=True)
    cuadros,pos=fotogramas_reja(direccion,rect.size,True)
    assert pygame.mask.from_surface(cuadros[0]).count()>200
    assert superficie.get_at((pos[0]+cuadros[0].get_width()//2,pos[1]+cuadros[0].get_height()//2)).a>0
    abierta=SalidaVisual(direccion,2,'Sala',False,False,'itm_llave')
    superficie.fill((0,0,0,0));dibujar_rejas(superficie,rect,[abierta],solo_existentes=True)
    assert pygame.mask.from_surface(superficie).count()==0
    pared,_=pared_tapiada(direccion,rect.size)
    assert pygame.mask.from_surface(pared).count()>pygame.mask.from_surface(cuadros[0]).count()


@pytest.mark.parametrize('equipo',range(8))
def test_ocho_pasos_completos_para_cada_equipo(equipo):
    pygame.init();pygame.display.set_mode((1,1))
    pasos=CargadorAssets().cuadros_espalda_equipo(equipo)
    assert len(pasos)==8
    for im in pasos:
        assert im.get_width()>20 and im.get_height()>40
        assert pygame.mask.from_surface(im).count()>350


def test_victoria_bloquea_entrada_y_no_avanza_el_modelo(app):
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    for comando in ('N','N','N','R','AB E','E'):
        c.enviar_comando(comando);esperar(lambda:not c.esperando_red())
    assert c.estado().es_sala_salida and c.estado().estado=='victoria'
    partida=c.sesion.partida
    salida_id=partida.cripta.sala_salida_id
    partida.cripta.sala_salida_id=-900
    assert not construir_estado(partida).es_sala_salida
    partida.cripta.sala_salida_id=salida_id
    app.cambiar_escena(ESCENA_PARTIDA)
    escena=app._escenas[ESCENA_PARTIDA]
    escena._capturar_fin(c.estado())
    app.cambiar_escena(ESCENA_FIN_PARTIDA,c.resumen_fin())
    fin=app._escenas[ESCENA_FIN_PARTIDA]
    assert fin._victoria is not None and not fin.interactiva
    estado=(c.estado().tiempo,c.estado().acciones_jugador,c.estado().jugador.vida)
    pantalla=pygame.Surface((1280,720))
    for _ in range(103):
        fin.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        fin.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=fin._botones[1].center,button=1))
        fin.actualizar(50);fin.dibujar(pantalla)
    assert not fin.interactiva and app._actual==ESCENA_FIN_PARTIDA
    fin.actualizar(50);assert fin.interactiva and fin._victoria.opacidad_menu==255
    assert estado==(c.estado().tiempo,c.estado().acciones_jugador,c.estado().jugador.vida)
    fin.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=fin._botones[0].center,button=1))
    assert fin._viendo_stats


def test_puerta_sin_cierre_automatico_sigue_abierta_al_volver(app):
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    for comando in ('R 1','R 1','R 1','R 1','N'):
        c.enviar_comando(comando);esperar(lambda:not c.esperando_red())
    # Variante de prueba: esta puerta no tiene temporizador de cierre.
    puerta=next(s for s in c.sesion.partida.jugador.sala_actual.salidas if s.direccion=='E')
    puerta.cierre_automatico=None
    llaves=[o.instancia_id for o in c.estado().inventario if o.clase=='llave']
    for comando in ('AB E','E','O')+('W',)*10:
        c.enviar_comando(comando);esperar(lambda:not c.esperando_red())
    assert c.estado().sala_id==2
    assert not next(s for s in c.estado().salidas if s.direccion=='E').cerrada
    assert llaves==[o.instancia_id for o in c.estado().inventario if o.clase=='llave']
