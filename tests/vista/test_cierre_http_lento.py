"""Cerrar una ventana cancela 429 incluso durante el menú o el arranque."""
import threading
import time
from unittest.mock import Mock

import pygame
import pytest

from adaptadores.datos_http import DatosHTTP
from vista_pygame.app import AppPygame
from vista_pygame.config_vista import ESCENA_MENU


@pytest.mark.parametrize('fase', ['menu', 'arranque'])
def test_cierre_cancela_espera_larga_y_espera_los_hilos(fase, monkeypatch, tmp_path):
    fuente = DatosHTTP()
    esperando = threading.Event()
    espera_original = fuente._esperar_reintento
    def esperar(segundos):
        esperando.set()
        espera_original(segundos)
    monkeypatch.setattr(fuente, '_esperar_reintento', esperar)
    def get(url, **kwargs):
        if fase == 'arranque' and url.endswith('/criptas'):
            return Mock(status_code=200, json=lambda: {'criptas': [
                {'id': 'prueba', 'nombre': 'Prueba', 'salas': 1, 'dificultad': 1}]})
        return Mock(status_code=429, json=lambda: {'reintentar_en': 120})
    monkeypatch.setattr('adaptadores.datos_http.requests.get', get)
    app = AppPygame(fuente, carpeta_cache=str(tmp_path/'cache'), partidas_dir=str(tmp_path/'partidas'))
    menu = app._escenas[ESCENA_MENU]
    try:
        if fase == 'arranque':
            menu._hilo_carga.join(2)
            assert not menu._hilo_carga.is_alive()
            app._contexto.arrancar_partida(('prueba', 'QA', 17))
        assert esperando.wait(2), 'La consulta no llegó al 429 simulado.'
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        inicio = time.monotonic()
        app.ejecutar()
        assert time.monotonic()-inicio < 2
        assert not menu._hilo_carga.is_alive()
        arranque = app._contexto._hilo_inicio
        assert arranque is None or not arranque.is_alive()
        assert app._contexto.controlador._hilo is None
    finally:
        fuente.cancelar_pendientes()
        if app._contexto._hilo_inicio is not None:
            app._contexto._hilo_inicio.join(2)
        menu._hilo_carga.join(2)
        app._contexto.controlador.salir()
        pygame.quit()
        # La aplicación debe cerrar SDL; las demás pruebas comparten una
        # sesión de vídeo dummy y necesitan recuperarla después del cierre.
        pygame.init()
        pygame.display.set_mode((64, 64))
