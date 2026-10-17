"""mapeo_teclas: traduce eventos de teclado a acciones simbólicas, sin
decidir nada del juego."""
import pygame
import pytest

from vista_pygame.config_vista import ESCENA_INVENTARIO, ESCENA_PAUSA
from vista_pygame.entrada.mapeo_teclas import accion_para_evento


def _evento(tecla, mod=0, tipo=pygame.KEYDOWN):
    return pygame.event.Event(tipo, key=tecla, mod=mod)


@pytest.mark.parametrize("tecla,direccion", [
    (pygame.K_UP, "N"), (pygame.K_w, "N"),
    (pygame.K_DOWN, "S"), (pygame.K_s, "S"),
    (pygame.K_RIGHT, "E"), (pygame.K_d, "E"),
    (pygame.K_LEFT, "O"), (pygame.K_a, "O"),
])
def test_movimiento_flechas_y_wasd(tecla, direccion):
    assert accion_para_evento(_evento(tecla)) == ("comando", direccion)


@pytest.mark.parametrize("tecla,direccion", [
    (pygame.K_UP, "N"), (pygame.K_a, "O"),
])
def test_shift_mas_movimiento_es_abrir_puerta(tecla, direccion):
    evento = _evento(tecla, mod=pygame.KMOD_SHIFT)
    assert accion_para_evento(evento) == ("comando", f"AB {direccion}")


def test_espacio_es_atacar():
    assert accion_para_evento(_evento(pygame.K_SPACE)) == ("comando", "A")


def test_tab_es_siguiente_objetivo():
    assert accion_para_evento(_evento(pygame.K_TAB)) == ("ui", "siguiente_objetivo")


def test_f1_es_ayuda():
    assert accion_para_evento(_evento(pygame.K_F1)) == ("ui", "ayuda")


def test_i_cambia_a_inventario():
    assert accion_para_evento(_evento(pygame.K_i)) == ("escena", ESCENA_INVENTARIO)


def test_escape_cambia_a_pausa():
    assert accion_para_evento(_evento(pygame.K_ESCAPE)) == ("escena", ESCENA_PAUSA)


def test_tecla_no_mapeada_devuelve_none():
    assert accion_para_evento(_evento(pygame.K_F12)) is None


def test_evento_que_no_es_keydown_devuelve_none():
    assert accion_para_evento(_evento(pygame.K_UP, tipo=pygame.KEYUP)) is None
    assert accion_para_evento(pygame.event.Event(pygame.QUIT)) is None
