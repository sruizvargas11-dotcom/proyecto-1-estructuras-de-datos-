"""Orientación visual con conexiones que no tienen direcciones opuestas."""
from dataclasses import replace
import pygame
from tests.vista.test_cinematica_cripta import app, esperar, tecla, terminar
from vista_pygame.config_vista import ESCENA_PARTIDA


def iniciar(app):
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    # Solo el escenario sintético del test: subir a sala 2, volver por oeste.
    c.sesion.partida.cripta.sala_por_id(2).salida_hacia('S').direccion='O'
    app.cambiar_escena(ESCENA_PARTIDA,None)
    e=app._escenas[ESCENA_PARTIDA]
    tecla(e,pygame.K_UP);terminar(e,c)
    return e,c


def test_subir_y_volver_por_oeste_muestra_la_salida_real_sin_cambiarla(app):
    e,c=iniciar(app)
    estado=c.estado()
    assert estado.sala_id==2
    assert e._texto_regreso(estado)=='Volver a sala 1: O (Oeste) · abierta'
    # La consulta y el dibujo no alteran el turno ni las conexiones del motor.
    antes=(estado.tiempo,estado.acciones_jugador,[(s.direccion,s.sala_destino_id) for s in estado.salidas])
    pantalla=pygame.Surface((1280,720));pantalla.fill((0,0,0))
    e._dibujar_regreso(pantalla,app._contexto.assets,estado)
    assert pygame.mask.from_threshold(pantalla,(0,0,0),(1,1,1,255)).count()<1280*720
    assert antes==(c.estado().tiempo,c.estado().acciones_jugador,
                  [(s.direccion,s.sala_destino_id) for s in c.estado().salidas])
    tecla(e,pygame.K_LEFT);terminar(e,c)
    assert c.estado().sala_id==1
    assert e._texto_regreso(c.estado())=='Volver a sala 2: N (Norte) · abierta'


def test_regreso_no_promete_una_puerta_abierta_ni_una_salida_inexistente(app):
    e,c=iniciar(app)
    estado=c.estado()
    cerrada=replace(estado,salidas=[replace(s,cerrada=True) if s.sala_destino_id==1 else s for s in estado.salidas])
    assert e._texto_regreso(cerrada)=='Volver a sala 1: O (Oeste) · cerrada: abrir primero'
    sin_regreso=replace(estado,salidas=[s for s in estado.salidas if s.sala_destino_id!=1])
    assert e._texto_regreso(sin_regreso)=='Volver a sala 1: no hay salida directa.'


def test_cargar_en_la_misma_sala_descarta_la_referencia_visual_anterior(app):
    e,c=iniciar(app)
    assert e._texto_regreso(c.estado()) is not None
    tecla(e,pygame.K_g);terminar(e,c)
    assert e._texto_regreso(c.estado()) is not None
    tecla(e,pygame.K_l);terminar(e,c)
    assert e._texto_regreso(c.estado()) is None
