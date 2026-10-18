"""Dibuja al jugador y a los enemigos de la sala actual.

Solo presentación: la vista no decide nada de los enemigos (ni movimiento,
ni ataques, ni orden, ni azar), solo muestra lo que el modelo ya resolvió
(EstadoPartida, ya publicado por ControladorPygame). El único cómputo propio
es de layout (qué rectángulo de pantalla le toca a cada uno), nunca de
reglas del juego.
"""
import pygame
from vista_pygame.render.escenografia_sala import sombra_contacto
from vista_pygame.render.fuego_vista import FuegoAntorcha
from vista_pygame.render.heroe_equipo import clave_equipo

from estructuras.ordenamientos import ordenar
from estructuras.vector_dinamico import Vector
from vista_pygame.config_vista import (
    COLOR_PELIGRO, COLOR_TEXTO, COLOR_TEXTO_TENUE, COLOR_VENENO, COLOR_VIDA, COLOR_ORO,
    COLOR_VIDA_FONDO, MAX_ENEMIGOS_VISIBLES, SLOTS_ENEMIGOS,
)

POS_JUGADOR = (265, 240)
_FUEGO = None


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


def dibujar_jugador(pantalla, assets, estado, nombre_jugador, animaciones=None, pantalla_ui=None):
    global _FUEGO
    ui=pantalla_ui if pantalla_ui is not None else pantalla
    sprite = assets.sprite_jugador("parado", "S")
    ancho,alto = sprite.get_size()
    if hasattr(assets,'tiene_heroe_compartido') and assets.tiene_heroe_compartido():
        ancho,alto=68,100
    offset = (0,0)
    cuadro = 0
    if hasattr(assets,'fotograma_jugador') and (animaciones is not None or
            (hasattr(assets,'tiene_heroe_compartido') and assets.tiene_heroe_compartido())):
        estado_actor,cuadro=(animaciones.estado_actor(estado.jugador.instancia_id)
                            if animaciones is not None else ('reposo',0))
        if hasattr(assets,'fotograma_jugador_equipado'):
            sprite,offset=assets.fotograma_jugador_equipado(estado_actor,cuadro,clave_equipo(estado))
        else:sprite,offset=assets.fotograma_jugador(estado_actor,cuadro)
    x, y = POS_JUGADOR
    if animaciones is not None:
        dx, dy, golpeado = animaciones.pose(estado.jugador.instancia_id)
        x, y = x+dx, y+dy
        if golpeado:
            sprite = _destello(sprite)
    if (hasattr(assets,'fotograma_jugador') and estado.jugador.vida>0 and clave_equipo(estado)&2
            and not (hasattr(assets,'tiene_heroe_compartido') and assets.tiene_heroe_compartido())):
        if _FUEGO is None:
            _FUEGO=FuegoAntorcha()
        _FUEGO.dibujar(pantalla,(x+14,y+12),cuadro)
    sombra_contacto(pantalla,(x+ancho//2,y+alto-2),ancho+18,18)
    pantalla.blit(sprite, (x+offset[0], y+offset[1]))
    fuente = assets.fuente(16)
    etiqueta=fuente.render(nombre_jugador,False,COLOR_TEXTO)
    limite_sprite=sprite.get_bounding_rect(min_alpha=100)
    ui.blit(etiqueta,etiqueta.get_rect(midbottom=(x+ancho//2,y+offset[1]+limite_sprite.top-8)))
    _barra_vida(ui, x - 6, y + alto + 4, ancho + 12,
               estado.jugador.vida, estado.jugador.vida_max)
    if estado.jugador.envenenado:
        pygame.draw.circle(ui, COLOR_VENENO, (x + ancho + 10, y + 10), 6)


def dibujar_enemigos(pantalla, assets, estado, objetivo_indice, animaciones=None, pantalla_ui=None):
    """Hasta MAX_ENEMIGOS_VISIBLES en slots fijos, ordenados por instancia_id.
    Si hay más, dibuja los primeros y un indicador '+N'."""
    ui=pantalla_ui if pantalla_ui is not None else pantalla
    orden = _orden_visual(estado.enemigos_activos)
    fuente = assets.fuente(14)
    visibles = orden[:MAX_ENEMIGOS_VISIBLES]
    for (indice_real, enemigo), (sx, sy) in zip(visibles, SLOTS_ENEMIGOS):
        sprite = assets.sprite_enemigo(enemigo.tipo_id, enemigo.comportamiento)
        ancho,alto = sprite.get_size()
        offset = (0,0)
        if hasattr(assets,'fotograma_enemigo') and animaciones is not None:
            estado_actor,cuadro=animaciones.estado_actor(enemigo.instancia_id)
            sprite,offset=assets.fotograma_enemigo(enemigo.tipo_id,enemigo.comportamiento,estado_actor,cuadro)
        if animaciones is not None:
            dx, dy, golpeado = animaciones.pose(enemigo.instancia_id)
            sx, sy = sx+dx, sy+dy
            if golpeado:
                sprite = _destello(sprite)
        seleccionado = indice_real == objetivo_indice
        if seleccionado:
            pygame.draw.rect(pantalla, (224, 180, 90),
                             (sx - 4, sy - 4, ancho + 8, alto + 8), 2)
        sombra_contacto(pantalla,(sx+ancho//2,sy+alto),ancho+16,14)
        pantalla.blit(sprite, (sx+offset[0], sy+offset[1]))
        nombre = enemigo.nombre
        while fuente.size(nombre)[0] > 112:
            nombre = nombre[:-2].rstrip('…') + '…'
        ui.blit(fuente.render(nombre, False, COLOR_TEXTO), (sx - 6, sy - 32))
        identificador = assets.fuente(12).render(enemigo.instancia_id, False, COLOR_ORO)
        ui.blit(identificador, (sx - 6, sy - 16))
        _barra_vida(ui, sx, sy + alto + 2, ancho,
                   enemigo.vida, enemigo.vida_max)
        icono_texto = fuente.render(_icono_comportamiento(enemigo.comportamiento), True,
                                    COLOR_TEXTO_TENUE)
        ui.blit(icono_texto, (sx, sy + alto + 14))
        if enemigo.envenenado:
            pygame.draw.circle(ui, COLOR_VENENO, (sx + ancho + 6, sy + 6), 5)

    restantes = len(orden) - len(visibles)
    if restantes > 0:
        ultimo_x, ultimo_y = SLOTS_ENEMIGOS[len(visibles) - 1] if visibles else SLOTS_ENEMIGOS[0]
        texto = assets.fuente(20).render(f"+{restantes}", True, COLOR_PELIGRO)
        ui.blit(texto, (ultimo_x + 50, ultimo_y + 40))

    if estado.enemigos_dormidos:
        fuente_dormidos = assets.fuente(14)
        texto = fuente_dormidos.render(
            f"Dormidos: {len(estado.enemigos_dormidos)}", True, COLOR_TEXTO_TENUE)
        ui.blit(texto, (SLOTS_ENEMIGOS[0][0], SLOTS_ENEMIGOS[0][1] - 36))


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


def posiciones_actores(estado):
    """Coordenadas de presentación copiadas por instancia, no índices de ataque."""
    return [(estado.jugador.instancia_id, POS_JUGADOR)] + [
        (enemigo.instancia_id, posicion)
        for (_, enemigo), posicion in zip(_orden_visual(estado.enemigos_activos), SLOTS_ENEMIGOS)]


_DESTELLOS = []  # pares Surface original/Surface blanca, sin dict


def _destello(sprite):
    for original, blanco in _DESTELLOS:
        if original is sprite:
            return blanco
    blanco = sprite.copy()
    blanco.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
    if len(_DESTELLOS) >= 64:
        _DESTELLOS.clear()
    _DESTELLOS.append((sprite, blanco))
    return blanco
