from dataclasses import asdict
from types import SimpleNamespace
import random
import pygame
import pytest

from vista_pygame.render.muerte import AnimacionMuerte, DURACION_MUERTE_MS, DURACION_CAIDA_MS
from vista_pygame.escenas.fin_partida import EscenaFinPartida
from vista_pygame.config_vista import ESCENA_MENU
from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.contratos import ResumenPartida, FilaPuntaje


def _animacion():
    fondo=pygame.Surface((1280,720));fondo.fill((100,100,100))
    sprite=pygame.Surface((30,60),pygame.SRCALPHA);sprite.fill((120,180,60,255))
    return AnimacionMuerte(fondo,sprite,(200,350))


def test_caida_fundido_y_aparicion_siguen_el_orden():
    a=_animacion()
    assert a.cuadro == 0 and a.opacidad_fondo == 0 and a.opacidad_menu == 0
    a.actualizar(DURACION_CAIDA_MS)
    assert a.cuadro == 17 and a.opacidad_fondo > 0 and a.opacidad_menu == 0
    a.actualizar(750)
    assert a.opacidad_fondo == 210 and 0 < a.opacidad_menu < 255
    assert not a.terminada
    a.actualizar(DURACION_MUERTE_MS)
    assert a.terminada and a.opacidad_menu == 255


def test_secuencia_repetible_y_sin_modificar_sprite_fondo_ni_azar():
    estado_azar=random.getstate()
    fondo=pygame.Surface((1280,720));fondo.fill((100,100,100))
    sprite=pygame.Surface((30,60),pygame.SRCALPHA);sprite.fill((120,180,60,255))
    original=pygame.image.tobytes(sprite,'RGBA');original_fondo=pygame.image.tobytes(fondo,'RGBA')
    a=AnimacionMuerte(fondo,sprite,(200,350));b=AnimacionMuerte(fondo,sprite,(200,350))
    a.actualizar(1450)
    for delta in (400,600,450):b.actualizar(delta)
    pantallas=[pygame.Surface((1280,720)) for _ in range(2)]
    a.dibujar(pantallas[0]);b.dibujar(pantallas[1])
    assert pygame.image.tobytes(pantallas[0],'RGBA') == pygame.image.tobytes(pantallas[1],'RGBA')
    assert pygame.image.tobytes(sprite,'RGBA') == original
    assert pygame.image.tobytes(fondo,'RGBA') == original_fondo
    assert random.getstate() == estado_azar


def test_dt_negativo_no_rebobina_y_dt_grande_finaliza():
    a=_animacion();a.actualizar(-10)
    assert a.cuadro == 0
    a.actualizar(10000)
    assert a.terminada and a.opacidad_menu == 255


def _escena():
    resumen=ResumenPartida('derrota','Ada','c','v',4,1,321,3,9,10,2)
    filas=[FilaPuntaje(i+1,f'Jugador{i}','c','v',10+i,2,500+i,'derrota',i==0) for i in range(12)]
    llamadas=[]
    controlador=SimpleNamespace(resumen_fin=lambda:resumen,tabla_puntajes=lambda:filas,
        mensajes=lambda:['Golpe final','Has muerto'],salir=lambda:llamadas.append('salir'))
    fondo=pygame.Surface((1280,720));fondo.fill((100,100,100))
    sprite=pygame.Surface((30,60),pygame.SRCALPHA);sprite.fill((120,180,60,255))
    contexto=SimpleNamespace(controlador=controlador,assets=CargadorAssets(),
        audio=SimpleNamespace(reproducir_musica=lambda estado:None),
        cambiar_escena=lambda *args:llamadas.append(args),fondo_fin=fondo,jugador_fin=(sprite,(200,350)))
    e=EscenaFinPartida(contexto);e.al_entrar(resumen)
    return e,llamadas,resumen,filas


def _tecla(key):
    return pygame.event.Event(pygame.KEYDOWN,key=key,mod=0)


def test_entrada_se_bloquea_durante_la_animacion():
    e,llamadas,_,_=_escena()
    e.manejar_evento(_tecla(pygame.K_RETURN))
    e.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=e._botones[0].center))
    assert not llamadas and not e._viendo_stats and e._seleccion == 1
    e.actualizar(2500);assert e.interactiva


def test_tres_opciones_se_recorreren_por_teclado():
    e,llamadas,_,_=_escena();e.actualizar(2500)
    assert len(e._botones) == 3
    e.manejar_evento(_tecla(pygame.K_TAB));assert e._seleccion == 2
    e.manejar_evento(_tecla(pygame.K_DOWN));assert e._seleccion == 0
    e.manejar_evento(_tecla(pygame.K_UP));assert e._seleccion == 2
    assert not llamadas


def test_stats_muestra_resumen_puntajes_y_vuelve_sin_salir_ni_registrar():
    e,llamadas,resumen,filas=_escena();original=asdict(resumen);e.actualizar(2500)
    e.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=e._botones[0].center))
    assert e._viendo_stats and not llamadas
    e.manejar_evento(pygame.event.Event(pygame.MOUSEWHEEL,y=-100))
    assert e._desplazamiento == 0  # fundido: descarta entrada
    e.actualizar(500)
    e.manejar_evento(pygame.event.Event(pygame.MOUSEWHEEL,y=-100))
    assert e._desplazamiento == 6
    e.dibujar(pygame.Surface((1280,720)))
    e.manejar_evento(_tecla(pygame.K_ESCAPE))
    assert not e._viendo_stats and not llamadas
    assert asdict(resumen) == original and len(filas) == 12


def test_boton_volver_al_menu_cierra_la_sesion():
    e,llamadas,_,_=_escena();e.actualizar(2500)
    e.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=e._botones[1].center))
    assert llamadas == ['salir',(ESCENA_MENU,)]
    e.al_salir()
    assert e._muerte is None and e.contexto.fondo_fin is None and e.contexto.jugador_fin is None


def test_salir_publica_quit_sin_volver_al_menu(monkeypatch):
    e,llamadas,_,_=_escena();e.actualizar(2500);eventos=[]
    monkeypatch.setattr(pygame.event,'post',eventos.append)
    e.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=e._botones[2].center))
    assert [evento.type for evento in eventos] == [pygame.QUIT] and not llamadas


def test_boton_volver_de_stats_por_raton():
    e,llamadas,_,_=_escena();e.actualizar(2500);e._seleccion=0;e._activar()
    e.manejar_evento(_tecla(pygame.K_ESCAPE))
    assert e._viendo_stats  # no cerrar mientras se revela
    e.actualizar(500)
    e.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=e._volver.center))
    assert not e._viendo_stats and not llamadas
