"""Traduce eventos de teclado de pygame a acciones simbólicas.

No decide nada del juego: solo dice qué pidió el jugador. La escena de
partida es quien arma el texto final del comando (por ejemplo, agrega el
número del enemigo seleccionado a 'A') y quien decide si lo encola hacia el
controlador. Tablas como tuplas de pares, no dict (regla del curso): el
mapeo se recorre linealmente, son pocas teclas y no es una ruta caliente.
"""
import pygame

from vista_pygame.config_vista import ESCENA_INVENTARIO, ESCENA_PAUSA

# (tecla pygame, dirección) — movimiento con flechas y WASD.
TECLAS_MOVER = (
    (pygame.K_UP, "N"), (pygame.K_w, "N"),
    (pygame.K_DOWN, "S"), (pygame.K_s, "S"),
    (pygame.K_RIGHT, "E"), (pygame.K_d, "E"),
    (pygame.K_LEFT, "O"), (pygame.K_a, "O"),
)

# (tecla pygame, categoría, valor) para todo lo que no es movimiento.
#   'comando' -> texto base a enviar al controlador (la escena completa el
#                número de objetivo/objeto si aplica)
#   'escena'  -> cambiar a esa escena (no pasa por el controlador)
#   'ui'      -> acción local de la escena de partida
TECLAS_ACCION = (
    (pygame.K_SPACE, "comando", "A"),    # atacar al enemigo seleccionado
    (pygame.K_x, "comando", "W"),        # esperar
    (pygame.K_r, "comando", "R"),        # recoger
    (pygame.K_f, "comando", "T"),        # soltar (tirar)
    (pygame.K_u, "comando", "U"),        # usar
    (pygame.K_c, "comando", "EQ"),       # equipar
    (pygame.K_p, "comando", "P"),        # pergamino de retroceso
    (pygame.K_g, "comando", "G"),        # guardar (ruta por defecto)
    (pygame.K_l, "comando", "L"),        # cargar (ruta por defecto)
    (pygame.K_TAB, "ui", "siguiente_objetivo"),
    (pygame.K_i, "escena", ESCENA_INVENTARIO),
    (pygame.K_ESCAPE, "escena", ESCENA_PAUSA),
    (pygame.K_F1, "ui", "ayuda"),
    (pygame.K_F5, "ui", "minimapa"),
)


def _direccion_para_tecla(tecla):
    for k, direccion in TECLAS_MOVER:
        if k == tecla:
            return direccion
    return None


def accion_para_evento(evento):
    """Traduce un evento KEYDOWN a ('comando'|'escena'|'ui', valor), o None.

    Shift + una tecla de movimiento es 'abrir puerta hacia esa dirección'
    (AB <dir>) en vez de moverse.
    """
    if evento.type != pygame.KEYDOWN:
        return None

    direccion = _direccion_para_tecla(evento.key)
    if direccion is not None:
        con_shift = bool(evento.mod & pygame.KMOD_SHIFT)
        return ("comando", f"AB {direccion}" if con_shift else direccion)

    for tecla, categoria, valor in TECLAS_ACCION:
        if tecla == evento.key:
            return (categoria, valor)

    return None
