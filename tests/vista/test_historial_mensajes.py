"""F5-01: consultar los veinte mensajes con una ventana de ocho filas."""
from types import SimpleNamespace

import pygame
import pytest

from controlador.controlador_pygame import ControladorPygame
from vista_pygame.escenas.partida import EscenaPartida, MENSAJES_RECT
from tests.vista.test_menu_criptas import ContextoFalso


@pytest.fixture
def panel(tmp_path):
    c = ControladorPygame(None, partidas_dir=str(tmp_path))
    escena = EscenaPartida(ContextoFalso(c))
    escena.al_entrar()
    for n in range(20):
        c.agregar_mensaje(n, f'mensaje-{n}')
    return escena, c


def _dibujados(escena, controlador):
    textos = []
    fuente = pygame.font.Font(None, 14)

    class Fuente:
        def size(self, texto):
            return fuente.size(texto)

        def render(self, texto, *args):
            if 'mensaje-' in texto:
                textos.append(texto.split('mensaje-')[1])
            return fuente.render(texto, *args)

    assets = SimpleNamespace(fuente=lambda tamano: Fuente())
    escena._dibujar_mensajes(pygame.Surface((1280, 720)), assets, controlador)
    return [int(n) for n in textos]


def _rueda(escena, cantidad, pos=MENSAJES_RECT.center):
    escena.manejar_evento(pygame.event.Event(
        pygame.MOUSEWHEEL, y=cantidad, x=0, pos=pos))


def _tecla(escena, tecla):
    escena.manejar_evento(pygame.event.Event(
        pygame.KEYDOWN, key=tecla, mod=0, unicode=''))


def test_rueda_permite_ver_todos_los_mensajes_sin_alterar_buffer(panel):
    escena, c = panel
    originales = c.mensajes()
    almacenamiento = c._historial_mensajes._datos
    assert _dibujados(escena, c) == list(range(12, 20))
    _rueda(escena, 100)
    assert _dibujados(escena, c) == list(range(8))
    _rueda(escena, -5)
    assert _dibujados(escena, c) == list(range(5, 13))
    _rueda(escena, -100)
    assert _dibujados(escena, c) == list(range(12, 20))
    assert c.mensajes() == originales
    assert c._historial_mensajes._datos is almacenamiento and len(almacenamiento) == 20
    assert c._comandos.empty()


def test_repaginacion_y_avpaginacion_recorrer_historial(panel):
    escena, c = panel
    _tecla(escena, pygame.K_PAGEUP)
    assert _dibujados(escena, c) == list(range(4, 12))
    _tecla(escena, pygame.K_PAGEUP)
    assert _dibujados(escena, c) == list(range(8))
    _tecla(escena, pygame.K_PAGEDOWN)
    assert _dibujados(escena, c) == list(range(8, 16))
    _tecla(escena, pygame.K_PAGEDOWN)
    assert _dibujados(escena, c) == list(range(12, 20))
    assert c._comandos.empty()


def test_restaura_lista_corta_y_rueda_fuera_del_panel_no_desplaza(panel):
    escena, c = panel
    _rueda(escena, 12)
    _rueda(escena, -12, pos=(20, 20))
    assert _dibujados(escena, c) == list(range(8))
    c.restaurar_mensajes(['mensaje-99'])
    assert _dibujados(escena, c) == [99]
    assert escena._scroll_mensajes == 0
