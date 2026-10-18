import time
import pygame
import pytest
from adaptadores.datos_offline import DatosOffline
from herramientas.generar_cripta_prueba import generar
from vista_pygame.app import AppPygame
from vista_pygame.config_vista import ESCENA_PARTIDA, ESCENA_FIN_PARTIDA, ESCENA_MENU
from vista_pygame.controlador_pygame import ControladorPygame
from tests.vista.test_fin_partida import _esperar, COMANDOS_VICTORIA


def test_muerte_publica_vida_cero_y_sin_turnos_pendientes(tmp_path):
    c=ControladorPygame(DatosOffline(), carpeta_cache=str(tmp_path/'cache'),
                        partidas_dir=str(tmp_path/'partidas'))
    try:
        c.iniciar_partida('cripta-01','Ada',2026)
        assert _esperar(lambda:c.estado() is not None)
        for comando in ['N']+['W']*15:c.enviar_comando(comando)
        assert _esperar(lambda:c.resumen_fin() is not None)
        assert c.estado().estado == 'derrota'
        assert c.estado().jugador.vida == 0
        assert c.estado().tiempo == c.resumen_fin().tiempo_final
        assert not c.estado().proximos_turnos
        assert not c.esperando_red()
    finally:c.salir()


@pytest.mark.parametrize('victoria',[False,True])
def test_app_cambia_a_fin_y_permite_otra_partida(tmp_path,victoria):
    if victoria:
        generar(tmp_path/'datos')
        fuente=DatosOffline(str(tmp_path/'datos'));cripta='cripta-prueba'
        comandos=COMANDOS_VICTORIA
    else:
        fuente=DatosOffline();cripta='cripta-01';comandos=['N']+['W']*15
    app=AppPygame(fuente,carpeta_cache=str(tmp_path/'cache'),partidas_dir=str(tmp_path/'partidas'))
    c=app._contexto.controlador
    try:
        assert _esperar(lambda:not app._escenas[ESCENA_MENU]._cargando)
        app.cambiar_escena(ESCENA_PARTIDA,(cripta,'Ada',2026))
        assert _esperar(lambda:c.estado() is not None)
        escena=app._escenas[ESCENA_PARTIDA];escena.actualizar(0)
        for comando in comandos:c.enviar_comando(comando)
        assert _esperar(lambda:c.resumen_fin() is not None)
        escena.actualizar(10000)
        assert app._actual == ESCENA_FIN_PARTIDA
        fin=app._escenas[ESCENA_FIN_PARTIDA]
        assert fin._resumen.resultado == ('victoria' if victoria else 'derrota')
        assert any(f.es_actual for f in fin._filas)
        assert any('Puntaje registrado' in m for m in fin._mensajes)
        fin.actualizar(5200 if victoria else 2500)
        fin.dibujar(app._pantalla)
        pygame.image.save(app._pantalla,str(tmp_path/'pantalla-final.png'))
        fin.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        assert app._actual == ESCENA_MENU
        assert _esperar(lambda:not app._escenas[ESCENA_MENU]._cargando)
        app.cambiar_escena(ESCENA_PARTIDA,(cripta,'Segunda',43))
        assert _esperar(lambda:c.estado() is not None)
        assert c.resumen_fin() is None and c.error_pendiente() is None
        assert c.estado().estado == 'en_curso' and c.estado().jugador.vida > 0
        assert not any('Has muerto' in m for m in c.mensajes())
        assert c._hilo.is_alive()
        acciones=c.estado().acciones_jugador;c.enviar_comando('W')
        assert _esperar(lambda:c.estado().acciones_jugador>acciones)
    finally:c.salir()
