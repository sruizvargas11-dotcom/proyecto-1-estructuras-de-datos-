"""Dibuja al jugador y a los enemigos de la sala actual.

Solo presentación: la vista no decide nada de los enemigos (ni movimiento,
ni ataques, ni orden, ni azar), solo muestra lo que el modelo ya resolvió
(EstadoPartida, ya publicado por ControladorPygame). El único cómputo propio
es de layout (qué rectángulo de pantalla le toca a cada uno), nunca de
reglas del juego.
"""
import pygame

from estructuras.ordenamientos import ordenar
from estructuras.vector_dinamico import Vector
from vista_pygame.config_vista import (
    COLOR_PELIGRO, COLOR_TEXTO, COLOR_TEXTO_TENUE, COLOR_VENENO, COLOR_VIDA,
    COLOR_VIDA_FONDO, MAX_ENEMIGOS_VISIBLES, SLOTS_ENEMIGOS,
)

POS_JUGADOR = (140, 480)


def _clave_natural(instancia_id):
    """Igual que modelo.partida._clave_natural: 'e-9' antes que 'e-10'."""
    texto, partes, actual, es_numero = str(instancia_id), [], "", None
    for caracter in texto:
        digito = caracter.isdigit()
        if es_numero is None or digito == es_numero:
            actual += caracter
        else:
            partes.append((0, int(actual)) if es_numero else (1, actual))
            actual = caracter
        es_numero = digito
    if actual:
        partes.append((0, int(actual)) if es_numero else (1, actual))
    return tuple(partes)


def _comparar_por_instancia(a, b):
    ka, kb = _clave_natural(a[1].instancia_id), _clave_natural(b[1].instancia_id)
    return (ka > kb) - (ka < kb)


def _orden_visual(enemigos_activos):
    """[(indice_real_1based, ActorVisual), ...] ordenado por instancia_id
    para el layout, conservando el índice real (el que espera 'A <n>')."""
    con_indice = Vector()
    for i, enemigo in enumerate(enemigos_activos, 1):
        con_indice.agregarValor((i, enemigo))
    ordenar(con_indice, _comparar_por_instancia)
    return list(con_indice)


def _barra_vida(pantalla, x, y, ancho, vida, vida_max):
    pygame.draw.rect(pantalla, COLOR_VIDA_FONDO, (x, y, ancho, 8))
    if vida_max > 0:
        lleno = max(0, min(ancho, int(ancho * vida / vida_max)))
        pygame.draw.rect(pantalla, COLOR_VIDA, (x, y, lleno, 8))


_ICONOS_COMPORTAMIENTO = (("guardián", "guardian"), ("errante", "errante"),
                          ("rastreador", "rastreador"))


def _icono_comportamiento(comportamiento):
    for nombre, icono in _ICONOS_COMPORTAMIENTO:
        if nombre == comportamiento:
            return icono
    return "desconocido"


def dibujar_jugador(pantalla, assets, estado, nombre_jugador):
    sprite = assets.sprite_jugador("parado", "S")
    x, y = POS_JUGADOR
    pantalla.blit(sprite, (x, y))
    fuente = assets.fuente(16)
    pantalla.blit(fuente.render(nombre_jugador, True, COLOR_TEXTO), (x - 10, y - 20))
    _barra_vida(pantalla, x - 6, y + sprite.get_height() + 4, sprite.get_width() + 12,
               estado.jugador.vida, estado.jugador.vida_max)
    if estado.jugador.envenenado:
        pygame.draw.circle(pantalla, COLOR_VENENO, (x + sprite.get_width() + 10, y + 10), 6)


def dibujar_enemigos(pantalla, assets, estado, objetivo_indice):
    """Hasta MAX_ENEMIGOS_VISIBLES en slots fijos, ordenados por instancia_id.
    Si hay más, dibuja los primeros y un indicador '+N'."""
    orden = _orden_visual(estado.enemigos_activos)
    fuente = assets.fuente(14)
    visibles = orden[:MAX_ENEMIGOS_VISIBLES]
    for (indice_real, enemigo), (sx, sy) in zip(visibles, SLOTS_ENEMIGOS):
        sprite = assets.sprite_enemigo(enemigo.tipo_id, enemigo.comportamiento)
        seleccionado = indice_real == objetivo_indice
        if seleccionado:
            pygame.draw.rect(pantalla, (224, 180, 90),
                             (sx - 4, sy - 4, sprite.get_width() + 8, sprite.get_height() + 8), 2)
        pantalla.blit(sprite, (sx, sy))
        nombre = f"{enemigo.nombre} #{indice_real}"
        pantalla.blit(fuente.render(nombre, True, COLOR_TEXTO), (sx - 6, sy - 18))
        _barra_vida(pantalla, sx, sy + sprite.get_height() + 2, sprite.get_width(),
                   enemigo.vida, enemigo.vida_max)
        icono_texto = fuente.render(_icono_comportamiento(enemigo.comportamiento), True,
                                    COLOR_TEXTO_TENUE)
        pantalla.blit(icono_texto, (sx, sy + sprite.get_height() + 14))
        if enemigo.envenenado:
            pygame.draw.circle(pantalla, COLOR_VENENO, (sx + sprite.get_width() + 6, sy + 6), 5)

    restantes = len(orden) - len(visibles)
    if restantes > 0:
        ultimo_x, ultimo_y = SLOTS_ENEMIGOS[len(visibles) - 1] if visibles else SLOTS_ENEMIGOS[0]
        texto = assets.fuente(20).render(f"+{restantes}", True, COLOR_PELIGRO)
        pantalla.blit(texto, (ultimo_x + 50, ultimo_y + 40))

    if estado.enemigos_dormidos:
        fuente_dormidos = assets.fuente(14)
        texto = fuente_dormidos.render(
            f"Dormidos: {len(estado.enemigos_dormidos)}", True, COLOR_TEXTO_TENUE)
        pantalla.blit(texto, (SLOTS_ENEMIGOS[0][0], SLOTS_ENEMIGOS[0][1] - 36))


def siguiente_objetivo(estado, objetivo_actual):
    """Siguiente índice real (1-based) a seleccionar con Tab, en el orden
    real de sala.enemigos_activos (el mismo que usa 'A <n>'); None si no hay
    ningún enemigo vivo en la sala."""
    cantidad = len(estado.enemigos_activos)
    if cantidad == 0:
        return None
    if objetivo_actual is None or objetivo_actual >= cantidad:
        return 1
    return objetivo_actual + 1
