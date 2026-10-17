"""Dibuja la sala actual (piso, paredes, puertas, trampas, objetos del
suelo) y el minimapa. Solo lee el EstadoPartida/topología publicados: nunca
toca el modelo ni decide nada del juego."""
import pygame

from estructuras.cola import Cola
from estructuras.vector_dinamico import Vector
from vista_pygame.config_vista import (
    CELDA_MINIMAPA, COLOR_FUEGO, COLOR_METAL, COLOR_METAL_OSCURO, COLOR_ORO,
    COLOR_PELIGRO, COLOR_PIEDRA, COLOR_PIEDRA_CLARA, COLOR_TEXTO, COLOR_TEXTO_TENUE,
    DIRECCIONES, offset_direccion,
)

SALA_RECT = pygame.Rect(40, 40, 760, 560)
GROSOR_PARED = 10
ANCHO_PUERTA = 70


def _punto_puerta(direccion):
    cx, cy = SALA_RECT.centerx, SALA_RECT.centery
    if direccion == "N":
        return (cx - ANCHO_PUERTA // 2, SALA_RECT.top), (cx + ANCHO_PUERTA // 2, SALA_RECT.top)
    if direccion == "S":
        return (cx - ANCHO_PUERTA // 2, SALA_RECT.bottom), (cx + ANCHO_PUERTA // 2, SALA_RECT.bottom)
    if direccion == "E":
        return (SALA_RECT.right, cy - ANCHO_PUERTA // 2), (SALA_RECT.right, cy + ANCHO_PUERTA // 2)
    if direccion == "O":
        return (SALA_RECT.left, cy - ANCHO_PUERTA // 2), (SALA_RECT.left, cy + ANCHO_PUERTA // 2)
    raise ValueError(f"Dirección desconocida: {direccion}")


def _color_puerta(salida):
    if not salida.cerrada:
        return (90, 150, 90)
    return COLOR_ORO if salida.tiene_llave else COLOR_PELIGRO


def dibujar_sala(pantalla, assets, estado):
    """estado: EstadoPartida publicado por ControladorPygame."""
    pantalla.fill((12, 14, 20), SALA_RECT.inflate(80, 80))
    pygame.draw.rect(pantalla, COLOR_PIEDRA, SALA_RECT)
    pygame.draw.rect(pantalla, COLOR_PIEDRA_CLARA, SALA_RECT, GROSOR_PARED)

    for salida in estado.salidas:
        a, b = _punto_puerta(salida.direccion)
        pygame.draw.line(pantalla, _color_puerta(salida), a, b, GROSOR_PARED + 4)

    fuente = assets.fuente(22)
    titulo = fuente.render(f"{estado.sala_nombre} (sala {estado.sala_id})", True, COLOR_TEXTO)
    pantalla.blit(titulo, (SALA_RECT.x + 16, SALA_RECT.y - 34))

    fuente_chica = assets.fuente(16)
    x = SALA_RECT.x + 24
    for trampa in estado.trampas:
        color = COLOR_PELIGRO if trampa.armada else COLOR_TEXTO_TENUE
        pygame.draw.circle(pantalla, color, (x, SALA_RECT.bottom - 30), 10)
        pantalla.blit(fuente_chica.render(trampa.nombre, True, color), (x + 16, SALA_RECT.bottom - 38))
        x += 140

    x = SALA_RECT.x + 24
    for objeto in estado.objetos_suelo:
        sprite = assets.sprite_objeto(objeto.tipo_id, objeto.clase)
        pantalla.blit(sprite, (x, SALA_RECT.y + 24))
        pantalla.blit(fuente_chica.render(objeto.nombre, True, COLOR_TEXTO),
                      (x - 4, SALA_RECT.y + 24 + sprite.get_height() + 2))
        x += sprite.get_width() + 70

    if estado.cargando:
        overlay = pygame.Surface(SALA_RECT.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        pantalla.blit(overlay, SALA_RECT.topleft)
        texto = assets.fuente(28).render("Cargando la siguiente sala...", True, COLOR_ORO)
        pantalla.blit(texto, texto.get_rect(center=SALA_RECT.center))


# ---------------------------------------------------------------------------
# Minimapa: el modelo no tiene coordenadas; el layout se calcula una sola
# vez por cripta con un BFS desde la sala inicial (offsets de una unidad por
# dirección). Es presentación pura, de solo lectura sobre la topología ya
# publicada (ver ControladorPygame.topologia_cripta()).
# ---------------------------------------------------------------------------

def calcular_layout_minimapa(topologia, sala_inicial_id):
    """[(sala_id, x, y), ...] en coordenadas de celda. BFS: la primera vez
    que se alcanza una sala fija su posición; no reordena la topología."""
    posiciones = Vector()   # pares (sala_id, (x, y))

    def posicion_de(sala_id):
        for sid, pos in posiciones:
            if sid == sala_id:
                return pos
        return None

    def sala_de(sala_id):
        for sala in topologia:
            if sala.sala_id == sala_id:
                return sala
        return None

    inicial = sala_de(sala_inicial_id)
    if inicial is None:
        return []
    posiciones.agregarValor((sala_inicial_id, (0, 0)))
    cola = Cola()
    cola.encolar(sala_inicial_id)
    while not cola.esta_vacia():
        actual_id = cola.desencolar()
        actual = sala_de(actual_id)
        x, y = posicion_de(actual_id)
        for direccion, destino_id in actual.salidas:
            if posicion_de(destino_id) is not None:
                continue
            dx, dy = offset_direccion(direccion)
            posiciones.agregarValor((destino_id, (x + dx, y + dy)))
            cola.encolar(destino_id)
    return [(sid, x, y) for sid, (x, y) in posiciones]


def dibujar_minimapa(pantalla, rect, layout, salas_visitadas, sala_actual_id, fuente):
    pygame.draw.rect(pantalla, COLOR_METAL_OSCURO, rect)
    pygame.draw.rect(pantalla, COLOR_METAL, rect, 2)
    if not layout:
        return
    xs = [x for _, x, _ in layout]
    ys = [y for _, _, y in layout]
    minx, miny = min(xs), min(ys)
    cx = rect.centerx - ((max(xs) - minx) * CELDA_MINIMAPA) // 2
    cy = rect.centery - ((max(ys) - miny) * CELDA_MINIMAPA) // 2
    for sala_id, x, y in layout:
        px = cx + (x - minx) * CELDA_MINIMAPA
        py = cy + (y - miny) * CELDA_MINIMAPA
        visitada = sala_id in salas_visitadas
        color = COLOR_ORO if sala_id == sala_actual_id else (
            (150, 150, 160) if visitada else (50, 50, 58))
        pygame.draw.rect(pantalla, color, (px, py, CELDA_MINIMAPA - 2, CELDA_MINIMAPA - 2))
