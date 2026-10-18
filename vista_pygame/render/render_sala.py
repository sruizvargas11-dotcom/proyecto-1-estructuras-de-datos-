"""Dibuja la sala actual (piso, paredes, puertas, trampas, objetos del
suelo) y el minimapa. Solo lee el EstadoPartida/topología publicados: nunca
toca el modelo ni decide nada del juego."""
import pygame
from vista_pygame.render.escenografia_sala import dibujar_escenario,posiciones_objetos,sombra_contacto,limitar_objeto_al_suelo

from estructuras.cola import Cola
from estructuras.vector_dinamico import Vector
from vista_pygame.config_vista import (
    CELDA_MINIMAPA, COLOR_FUEGO, COLOR_METAL, COLOR_METAL_OSCURO, COLOR_ORO,
    COLOR_PELIGRO, COLOR_PIEDRA, COLOR_PIEDRA_CLARA, COLOR_TEXTO, COLOR_TEXTO_TENUE,
    DIRECCIONES, offset_direccion,
)

SALA_RECT = pygame.Rect(40, 40, 760, 470)
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


def dibujar_sala(pantalla, assets, estado, tiempo_ms=0, puerta=None, objeto_oculto=None):
    """estado: EstadoPartida publicado por ControladorPygame."""
    pantalla.fill((12, 14, 20), SALA_RECT.inflate(80, 80))
    detallado=dibujar_escenario(pantalla,assets,estado,SALA_RECT,tiempo_ms,puerta)
    if detallado:pass
    elif hasattr(assets, 'texto'):
        _dibujar_piedra(pantalla, assets)
    else:
        pygame.draw.rect(pantalla, COLOR_PIEDRA, SALA_RECT)
    if not detallado:pygame.draw.rect(pantalla, COLOR_PIEDRA_CLARA, SALA_RECT, GROSOR_PARED)

    for salida in (() if detallado else estado.salidas):
        a, b = _punto_puerta(salida.direccion)
        pygame.draw.line(pantalla, _color_puerta(salida), a, b, GROSOR_PARED + 4)
        if hasattr(assets, 'texto'):
            nombre = ('puerta_abierta' if not salida.cerrada else
                      'puerta_llave' if salida.tiene_llave else 'puerta_cerrada')
            imagen = assets.sprite_entorno(nombre)
            centro = ((a[0]+b[0])//2, (a[1]+b[1])//2)
            pantalla.blit(imagen, imagen.get_rect(center=centro))

    fuente = assets.fuente(22)
    nombre_cripta=getattr(estado,'cripta_nombre','')
    texto=(nombre_cripta+' · ' if nombre_cripta else '')+f'{estado.sala_nombre} (sala {estado.sala_id})'
    while fuente.size(texto)[0]>SALA_RECT.width-32 and len(texto)>1:texto=texto[:-2]+'…'
    titulo = fuente.render(texto, True, COLOR_TEXTO)
    pantalla.blit(titulo, (SALA_RECT.x + 16, SALA_RECT.y - 34))

    fuente_chica = assets.fuente(16)
    x = SALA_RECT.x + 24
    for trampa in estado.trampas:
        color = COLOR_PELIGRO if trampa.armada else COLOR_TEXTO_TENUE
        pygame.draw.circle(pantalla, color, (x, SALA_RECT.bottom - 30), 10)
        pantalla.blit(fuente_chica.render(trampa.nombre, True, color), (x + 16, SALA_RECT.bottom - 38))
        x += 140

    for indice,objeto,(x,y) in posiciones_objetos(estado.objetos_suelo,estado.sala_id):
        if objeto.instancia_id==objeto_oculto:continue
        sprite,texto,(x,y)=presentacion_objeto(assets,indice,objeto,(x,y))
        sombra_contacto(pantalla,(x,y+1),sprite.get_width()+10,10)
        pantalla.blit(sprite,sprite.get_rect(midbottom=(x,y)))
        pantalla.blit(texto,texto.get_rect(midtop=(x,y+4)))
    if len(estado.objetos_suelo)>12:
        texto=f'+{len(estado.objetos_suelo)-12} objetos (R para recoger)'
        pantalla.blit(fuente_chica.render(texto,False,COLOR_ORO),(60,165))

    if estado.cargando:
        overlay = pygame.Surface(SALA_RECT.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        pantalla.blit(overlay, SALA_RECT.topleft)
        texto = assets.fuente(28).render("Cargando la siguiente sala...", True, COLOR_ORO)
        pantalla.blit(texto, texto.get_rect(center=SALA_RECT.center))



def presentacion_objeto(assets,indice,objeto,punto):
    sprite=assets.sprite_objeto(objeto.tipo_id,objeto.clase)
    fuente=assets.fuente(16)
    nombre=f'{indice}: {objeto.nombre}'
    while fuente.size(nombre)[0]>116 and len(nombre)>3:
        nombre=nombre[:-2].rstrip('.')+'…'
    texto=fuente.render(nombre,False,COLOR_TEXTO)
    punto=limitar_objeto_al_suelo(punto,sprite.get_size(),texto.get_size())
    return sprite,texto,punto


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
    """Ventana sobre el mapa: sigue al jugador y nunca pinta fuera del panel."""
    pygame.draw.rect(pantalla, COLOR_METAL_OSCURO, rect)
    if layout:
        actual=next(((x,y) for sid,x,y in layout if sid==sala_actual_id),None)
        if actual is None:actual=layout[0][1:]
        interior=rect.inflate(-8,-8)
        clip_anterior=pantalla.get_clip()
        pantalla.set_clip(clip_anterior.clip(interior))
        try:
            lado=CELDA_MINIMAPA-2
            for sala_id,x,y in layout:
                px=rect.centerx+(x-actual[0])*CELDA_MINIMAPA-lado//2
                py=rect.centery+(y-actual[1])*CELDA_MINIMAPA-lado//2
                celda=pygame.Rect(px,py,lado,lado)
                if not interior.colliderect(celda):continue
                visitada=sala_id in salas_visitadas
                color=COLOR_ORO if sala_id==sala_actual_id else (
                    (150,150,160) if visitada else (50,50,58))
                pygame.draw.rect(pantalla,color,celda)
        finally:
            pantalla.set_clip(clip_anterior)
    pygame.draw.rect(pantalla, COLOR_METAL, rect, 2)


_FONDO_PIEDRA = None
_ASSETS_FONDO = None


def _dibujar_piedra(pantalla, assets):
    global _FONDO_PIEDRA, _ASSETS_FONDO
    if _ASSETS_FONDO is not assets:
        _ASSETS_FONDO = assets
        _FONDO_PIEDRA = pygame.Surface(SALA_RECT.size)
        _FONDO_PIEDRA.fill(COLOR_PIEDRA)
        for y in range(0, SALA_RECT.height, 64):
            for x in range(0, SALA_RECT.width, 64):
                nombre = 'suelo_veta' if (x//64 + y//64)%5 == 0 else 'suelo_piedra'
                _FONDO_PIEDRA.blit(assets.sprite_entorno(nombre), (x,y))
        for x in range(0, SALA_RECT.width, 64):
            _FONDO_PIEDRA.blit(assets.sprite_entorno('pared'), (x,0))
    pantalla.blit(_FONDO_PIEDRA, SALA_RECT.topleft)
