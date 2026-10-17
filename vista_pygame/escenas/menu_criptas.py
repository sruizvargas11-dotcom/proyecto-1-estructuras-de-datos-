"""Escena de portada: selección de cripta.

Fondo con el boceto `assets/ui/portada.png` (si no existe, color sólido de
la paleta: nunca rompe), visible completo, sin ningún panel ni viñeta
encima. El boceto puede traer título y filas de ejemplo ya dibujados; esta
escena no los lee como datos. Sin una versión limpia del fondo
(`assets/ui/portada_limpia.png`), el título, el subtítulo y hasta 4 criptas
se dibujan EXACTAMENTE sobre los rectángulos medidos una vez con
`herramientas/medir_portada.py` (proporciones en `config_vista.py`), con un
ancho uniforme entre las filas para que ninguna placa pintada asome — y si
hay menos de 4 criptas, las filas sobrantes se tapan con una placa vacía
idéntica. Con portada_limpia.png (sin texto pintado), cada placa se ajusta
al ancho de su propio texto.

`listar_criptas()` puede bloquear (red); se consulta en un hilo propio de la
escena (no el hilo de modelo de ControladorPygame, que todavía no existe acá:
la partida no ha empezado) para no congelar la ventana. Esta escena es dueña
de iniciar la partida: llama a `controlador.iniciar_partida(...)` ella misma
al confirmar una cripta y le pasa `datos=None` a la escena de partida (que ya
no vuelve a iniciarla — ver el ajuste en `escenas/partida.py`).

Sin dict como índice/caché (regla del curso): las criptas llegan como lista
de registros planos (la propia respuesta de la fuente de datos, no una
estructura nuestra), el caché de fuentes es una lista de pares recorrida
linealmente (mismo patrón que `stubs_temporales.CargadorAssetsTemporal`), y
el foco es un entero simple (-1 = nombre, 0..N-1 = cripta).
"""
import math
import os
import threading
from dataclasses import dataclass

import pygame

from vista_pygame.config_vista import (
    ALTO_LOGICO, ANCHO_LOGICO, COLOR_AVISO, COLOR_FONDO, COLOR_PELIGRO,
    COLOR_TEXTO_TENUE, ESCENA_PARTIDA, PORTADA_CENTRO_X_PROP, PORTADA_ESPACIO_FILA_PROP,
    PORTADA_FILAS_PROP, PORTADA_REF_ALTO, PORTADA_REF_ANCHO, PORTADA_SUBTITULO_PROP,
    PORTADA_TITULO_PROP,
)
from vista_pygame.contratos import EscenaBase

RUTA_FONDO = "assets/ui/portada.png"
RUTA_FONDO_LIMPIO = "assets/ui/portada_limpia.png"
CANDIDATOS_FUENTE_PIXEL = (
    "assets/fuentes/PressStart2P-Regular.ttf",
    "assets/fuentes/PressStart2P.ttf",
    "assets/fuentes/PixelifySans-Regular.ttf",
    "assets/fuentes/PixelifySans-VariableFont_wght.ttf",
    "assets/fuentes/PixelifySans.ttf",
)
MAX_NOMBRE = 20
NOMBRE_POR_DEFECTO = "Jugador"

TITULO_TEXTO = "CRIPTA - Seleccionar Mazmorra"
TITULO_TAMANO_INICIAL = 26
TITULO_TAMANO_MINIMO = 12
MARGEN_TITULO_INTERNO = 24
MARGEN_FILA_UNIFORME = 4   # +4 px sobre la placa pintada más ancha (sin portada_limpia)
PADDING_TEXTO_LIMPIO = 16   # relleno a cada lado del texto (con portada_limpia)
FILA_TAMANO_INICIAL = 18
FILA_TAMANO_MINIMO = 12
FILA_MARGEN_INTERNO = 16

FLECHA_PERIODO_MS = 800
FLECHA_AMPLITUD = 2.5

# -- Paleta de las placas, igual al boceto: madera oscura casi lisa, marco
# metálico fino, selección dorada (nunca cambia el fondo de la placa). --
COLOR_MADERA_BASE = (0x2e, 0x22, 0x19)
COLOR_VETA = (0x36, 0x28, 0x1d)
COLOR_MARCO = (0x4a, 0x4f, 0x55)
COLOR_MARCO_INTERIOR = (0x6e, 0x73, 0x78)
COLOR_TEXTO_PLACA = (0xd9, 0xcd, 0xb0)
COLOR_TEXTO_TITULO = (0xe8, 0xdc, 0xc0)
COLOR_SUBTITULO_TEXTO = (0x9a, 0x94, 0x88)
COLOR_SELECCION_BORDE = (0xe0, 0xb2, 0x4a)
COLOR_SELECCION_TEXTO = (0xf5, 0xd7, 0x7a)
COLOR_FLECHA = (0xe0, 0xb2, 0x4a)
COLOR_FLECHA_BORDE = (0x14, 0x18, 0x1f)
COLOR_PLACEHOLDER_NOMBRE = (120, 114, 100)
COLOR_SOMBRA_PLACA = (10, 8, 6)


@dataclass
class LayoutPortada:
    """Todo lo que depende del tamaño de la ventana (nunca del contenido:
    criptas, foco, scroll...). Se calcula una sola vez por tamaño — ver
    EscenaMenuCriptas._refrescar_layout_si_hace_falta."""
    escala: float
    offset_x: int
    offset_y: int
    titulo_rect: pygame.Rect
    subtitulo_rect: pygame.Rect
    filas_medidas: tuple      # los 4 rectángulos tal como se midieron (sin ancho uniforme)
    fila_rects: tuple         # los mismos 4, ya con el ancho uniforme y centrados
    ancho_fila_uniforme: int
    espacio_fila: int
    centro_x: int
    viewport_top: int
    viewport_bottom: int
    nombre_rect: pygame.Rect


class EscenaMenuCriptas(EscenaBase):
    def __init__(self, contexto):
        super().__init__(contexto)
        self._tamano_layout = (ANCHO_LOGICO, ALTO_LOGICO)
        self._layout = self._calcular_layout(*self._tamano_layout)

        self._fondo, self._fondo_limpio = self._cargar_fondo_preferido()

        self._ruta_fuente_pixel = self._buscar_fuente_pixel()
        self._fuentes_cache = []   # [(tamano, Font), ...] — sin dict (regla del curso)
        self._fuente_normal = self._fuente(20)
        self._fuente_fila = self._fuente(18)
        self._fuente_chica = self._fuente(15)

        # El título no cambia en la vida de la escena: se renderiza una sola
        # vez. Sin portada_limpia, su placa es de ancho fijo (medido) y el
        # texto se achica hasta que entre; con portada_limpia, la placa se
        # ajusta a un tamaño de letra fijo (ver _rect_titulo_actual).
        if self._fondo_limpio:
            self._titulo_superficie = self._fuente(TITULO_TAMANO_INICIAL).render(
                TITULO_TEXTO, True, COLOR_TEXTO_TITULO)
        else:
            ancho_max = self._layout.titulo_rect.w - 2 * MARGEN_TITULO_INTERNO
            self._titulo_superficie = self._renderizar_ajustado(
                TITULO_TEXTO, ancho_max, TITULO_TAMANO_INICIAL,
                COLOR_TEXTO_TITULO, TITULO_TAMANO_MINIMO)

        self._lock = threading.Lock()
        self._carga_id = 0
        self._hilo_carga = None
        self._criptas = []
        self._cargando = True
        self._error_carga = None
        self._nombre = NOMBRE_POR_DEFECTO
        self._nombre_seleccionado = True
        self._foco = -1
        self._scroll = 0
        self._iniciando = False
        self._tiempo_acumulado = 0

    # -- layout: de las proporciones medidas a rectángulos de pantalla ----

    @staticmethod
    def _calcular_layout(ancho_ventana, alto_ventana):
        escala = min(ancho_ventana / PORTADA_REF_ANCHO, alto_ventana / PORTADA_REF_ALTO)
        disp_ancho = round(PORTADA_REF_ANCHO * escala)
        disp_alto = round(PORTADA_REF_ALTO * escala)
        offset_x = (ancho_ventana - disp_ancho) // 2
        offset_y = (alto_ventana - disp_alto) // 2

        def a_pantalla(prop):
            px, py, pw, ph = prop
            return pygame.Rect(
                offset_x + round(px * PORTADA_REF_ANCHO * escala),
                offset_y + round(py * PORTADA_REF_ALTO * escala),
                round(pw * PORTADA_REF_ANCHO * escala),
                round(ph * PORTADA_REF_ALTO * escala),
            )

        titulo_rect = a_pantalla(PORTADA_TITULO_PROP)
        subtitulo_rect = a_pantalla(PORTADA_SUBTITULO_PROP)
        filas_medidas = tuple(a_pantalla(p) for p in PORTADA_FILAS_PROP)

        centro_x = offset_x + round(PORTADA_CENTRO_X_PROP * PORTADA_REF_ANCHO * escala)
        ancho_uniforme = max(r.w for r in filas_medidas) + round(MARGEN_FILA_UNIFORME * escala)
        fila_rects = tuple(
            pygame.Rect(centro_x - ancho_uniforme // 2, r.y, ancho_uniforme, r.h)
            for r in filas_medidas
        )
        espacio_fila = round(PORTADA_ESPACIO_FILA_PROP * PORTADA_REF_ALTO * escala)

        viewport_top = fila_rects[0].y
        viewport_bottom = fila_rects[3].bottom

        gap = max(8, round(0.018 * PORTADA_REF_ALTO * escala))
        nombre_ancho = round(ancho_uniforme * 0.62)
        nombre_rect = pygame.Rect(centro_x - nombre_ancho // 2, viewport_bottom + gap,
                                  nombre_ancho, fila_rects[0].h)

        return LayoutPortada(
            escala=escala, offset_x=offset_x, offset_y=offset_y,
            titulo_rect=titulo_rect, subtitulo_rect=subtitulo_rect,
            filas_medidas=filas_medidas, fila_rects=fila_rects,
            ancho_fila_uniforme=ancho_uniforme, espacio_fila=espacio_fila,
            centro_x=centro_x, viewport_top=viewport_top, viewport_bottom=viewport_bottom,
            nombre_rect=nombre_rect,
        )

    def _refrescar_layout_si_hace_falta(self):
        """Recalcula el layout solo si cambió el tamaño de la ventana desde
        la última vez — nunca por frame. Hoy la ventana no se redimensiona
        (ANCHO_LOGICO/ALTO_LOGICO son constantes), así que en la práctica
        esto se queda en una comparación barata de dos enteros."""
        tamano_actual = (ANCHO_LOGICO, ALTO_LOGICO)
        if tamano_actual == self._tamano_layout:
            return
        self._tamano_layout = tamano_actual
        self._layout = self._calcular_layout(*tamano_actual)

    def _rect_fila_sin_scroll(self, indice):
        layout = self._layout
        if indice < 4:
            return layout.fila_rects[indice]
        return layout.fila_rects[3].move(0, (indice - 3) * layout.espacio_fila)

    def _rect_fila_pantalla(self, indice):
        """El rectángulo donde se dibuja (y se hace clic) la fila 'indice'.
        Sin portada_limpia es el de ancho uniforme medido; con ella, se
        ajusta al ancho del texto de esa cripta en particular."""
        base = self._rect_fila_sin_scroll(indice)
        if self._fondo_limpio:
            with self._lock:
                cripta = self._criptas[indice] if indice < len(self._criptas) else None
            if cripta is not None:
                ancho = self._fuente_fila.size(self._texto_fila(cripta))[0] + 2 * PADDING_TEXTO_LIMPIO
                base = pygame.Rect(0, base.y, ancho, base.h)
                base.centerx = self._layout.centro_x
        rect = base.copy()
        rect.y -= self._scroll
        return rect

    def _rect_titulo_actual(self):
        if not self._fondo_limpio:
            return self._layout.titulo_rect
        rect = pygame.Rect(0, 0, self._titulo_superficie.get_width() + 2 * PADDING_TEXTO_LIMPIO,
                           self._layout.titulo_rect.h)
        rect.center = self._layout.titulo_rect.center
        return rect

    def _rect_subtitulo_actual(self, texto_subtitulo):
        if not self._fondo_limpio:
            return self._layout.subtitulo_rect
        ancho = self._fuente_chica.size(texto_subtitulo)[0] + 2 * PADDING_TEXTO_LIMPIO
        rect = pygame.Rect(0, 0, ancho, self._layout.subtitulo_rect.h)
        rect.center = self._layout.subtitulo_rect.center
        return rect

    def _rect_mensaje(self):
        """Caja para 'Consultando criptas...'/error/'No hay criptas': las
        dos primeras filas medidas, unidas (deja sitio para 2-3 líneas)."""
        f0, f1 = self._layout.fila_rects[0], self._layout.fila_rects[1]
        return pygame.Rect(f0.x, f0.y, f0.w, f1.bottom - f0.y)

    def _rect_elemento_actual(self, cantidad):
        """El rectángulo del elemento con foco (para las flechas), o None
        si el foco apunta a algo que ya no existe (p. ej. tras un reintento
        que redujo la cantidad de criptas)."""
        if self._foco == -1:
            return self._layout.nombre_rect
        if 0 <= self._foco < cantidad:
            return self._rect_fila_pantalla(self._foco)
        return None

    # -- fondo y fuentes ---------------------------------------------------

    def _cargar_fondo_preferido(self):
        """assets/ui/portada_limpia.png (sin texto) si existe; si no,
        assets/ui/portada.png; si ninguno carga, None (color sólido,
        nunca rompe). El booleano dice si el fondo ya viene "limpio" (sin
        texto del boceto), para no dibujar ninguna placa de cobertura."""
        disp_tamano = (round(PORTADA_REF_ANCHO * self._layout.escala),
                       round(PORTADA_REF_ALTO * self._layout.escala))
        limpio = self._intentar_cargar_imagen(RUTA_FONDO_LIMPIO, disp_tamano)
        if limpio is not None:
            return limpio, True
        return self._intentar_cargar_imagen(RUTA_FONDO, disp_tamano), False

    @staticmethod
    def _intentar_cargar_imagen(ruta, disp_tamano):
        try:
            imagen = pygame.image.load(ruta).convert()
        except (pygame.error, OSError):
            return None
        try:
            return pygame.transform.scale(imagen, disp_tamano)
        except pygame.error:
            return None

    @staticmethod
    def _buscar_fuente_pixel():
        for ruta in CANDIDATOS_FUENTE_PIXEL:
            if os.path.isfile(ruta):
                return ruta
        return None

    def _fuente(self, tamano):
        for t, fuente in self._fuentes_cache:
            if t == tamano:
                return fuente
        if self._ruta_fuente_pixel is not None:
            try:
                fuente = pygame.font.Font(self._ruta_fuente_pixel, tamano)
            except pygame.error:
                fuente = self.contexto.assets.fuente(tamano)
        else:
            fuente = self.contexto.assets.fuente(tamano)
        self._fuentes_cache.append((tamano, fuente))
        return fuente

    def _renderizar_ajustado(self, texto, ancho_max, tamano_inicial, color, tamano_min):
        tamano = tamano_inicial
        while tamano > tamano_min:
            superficie = self._fuente(tamano).render(texto, True, color)
            if superficie.get_width() <= ancho_max:
                return superficie
            tamano -= 2
        return self._fuente(tamano_min).render(texto, True, color)

    @staticmethod
    def _texto_fila(cripta):
        return f"{cripta['nombre']}  |  {cripta['salas']} salas  |  Dificultad {cripta['dificultad']}"

    def _renderizar_fila_ajustada(self, texto, ancho_max, color):
        """Como _renderizar_ajustado, para el texto de una fila: el ancho
        de la placa es fijo (uniforme, medido) y un nombre de cripta largo
        no debe asomar fuera del marco."""
        tamano = FILA_TAMANO_INICIAL
        while tamano > FILA_TAMANO_MINIMO:
            superficie = self._fuente(tamano).render(texto, True, color)
            if superficie.get_width() <= ancho_max:
                return superficie
            tamano -= 2
        return self._fuente(FILA_TAMANO_MINIMO).render(texto, True, color)

    # -- ciclo de vida ---------------------------------------------------

    def al_entrar(self, datos=None):
        self._nombre = NOMBRE_POR_DEFECTO
        self._nombre_seleccionado = True
        self._foco = -1
        self._scroll = 0
        self._iniciando = False
        self._tiempo_acumulado = 0
        with self._lock:
            self._criptas = []
        self.contexto.audio.reproducir_musica("menu")
        self._iniciar_carga()

    def _iniciar_carga(self):
        with self._lock:
            self._cargando = True
            self._error_carga = None
            self._carga_id += 1
            carga_id = self._carga_id
        hilo = threading.Thread(target=self._cargar_criptas, args=(carga_id,), daemon=True)
        self._hilo_carga = hilo
        hilo.start()

    def _cargar_criptas(self, carga_id):
        """Corre en un hilo propio de la escena: listar_criptas() puede
        bloquear (red). Nunca toca pygame."""
        try:
            criptas = list(self.contexto.controlador.listar_criptas())
            error = None
        except (OSError, ValueError, RuntimeError) as excepcion:
            criptas = []
            error = str(excepcion)
        with self._lock:
            if carga_id != self._carga_id:
                return   # una carga más nueva (reintento) ya está en curso
            self._criptas = criptas
            self._error_carga = error
            self._cargando = False

    # -- entrada -----------------------------------------------------

    def manejar_evento(self, evento):
        if self._iniciando:
            return   # ignora cualquier tecla repetida mientras arranca
        if evento.type == pygame.KEYDOWN:
            self._manejar_tecla(evento)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self._manejar_clic(evento.pos)
        elif evento.type == pygame.MOUSEMOTION:
            self._manejar_movimiento_mouse(evento.pos)

    def _manejar_tecla(self, evento):
        if evento.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        with self._lock:
            cargando = self._cargando
            error = self._error_carga
            cantidad = len(self._criptas)

        if error is not None and evento.key == pygame.K_r:
            self._iniciar_carga()
            return

        lista_lista = not cargando and error is None

        if evento.key == pygame.K_TAB and lista_lista:
            direccion = -1 if evento.mod & pygame.KMOD_SHIFT else 1
            self._mover_foco(direccion, cantidad)
        elif evento.key in (pygame.K_UP, pygame.K_DOWN) and lista_lista \
                and self._foco >= 0 and cantidad:
            paso = -1 if evento.key == pygame.K_UP else 1
            self._foco = (self._foco + paso) % cantidad
            self._asegurar_visible(cantidad)
            self.contexto.audio.reproducir_sfx("menu_mover")
        elif evento.key == pygame.K_RETURN:
            if self._foco == -1:
                if lista_lista and cantidad:
                    self._foco = 0
                    self._asegurar_visible(cantidad)
                    self.contexto.audio.reproducir_sfx("menu_mover")
            else:
                self._confirmar(cantidad)
        elif evento.key == pygame.K_BACKSPACE and self._foco == -1:
            if self._nombre_seleccionado:
                self._nombre = ""
            else:
                self._nombre = self._nombre[:-1]
            self._nombre_seleccionado = False
        elif self._foco == -1:
            self._editar_nombre(evento)

    def _editar_nombre(self, evento):
        caracter = evento.unicode
        if not (caracter and caracter.isprintable()):
            return
        if self._nombre_seleccionado:
            # El valor por defecto estaba "seleccionado": la primera tecla
            # lo reemplaza entero, no se agrega al final.
            self._nombre = caracter[:MAX_NOMBRE]
            self._nombre_seleccionado = False
            return
        if len(self._nombre) < MAX_NOMBRE:
            self._nombre += caracter

    def _mover_foco(self, direccion, cantidad):
        total = cantidad + 1   # 1 campo de nombre + N criptas
        posicion = (self._foco + 1 + direccion) % total
        self._foco = posicion - 1
        if self._foco >= 0:
            self._asegurar_visible(cantidad)
        else:
            self._nombre_seleccionado = (self._nombre == NOMBRE_POR_DEFECTO)
        self.contexto.audio.reproducir_sfx("menu_mover")

    def _asegurar_visible(self, cantidad):
        if self._foco < 0:
            return
        rect = self._rect_fila_pantalla(self._foco)
        if rect.top < self._layout.viewport_top:
            self._scroll -= (self._layout.viewport_top - rect.top)
        elif rect.bottom > self._layout.viewport_bottom:
            self._scroll += (rect.bottom - self._layout.viewport_bottom)
        self._scroll = max(0, min(self._scroll, self._scroll_maximo(cantidad)))

    def _scroll_maximo(self, cantidad):
        if cantidad == 0:
            return 0
        ultima = self._rect_fila_sin_scroll(cantidad - 1)
        return max(0, ultima.bottom - self._layout.viewport_bottom)

    def _confirmar(self, cantidad):
        if self._iniciando or self._foco < 0 or self._foco >= cantidad:
            return
        with self._lock:
            if self._foco >= len(self._criptas):
                return
            cripta = self._criptas[self._foco]
        self._iniciando = True
        # Garantía explícita (§5.1/ANALISIS_ARQUITECTURA.md): el hilo que
        # consultó listar_criptas() debe haber terminado del todo antes de
        # que iniciar_partida() empiece a usar la misma fuente de datos
        # (nueva_partida la llama de forma síncrona, en este mismo hilo) —
        # nunca dos hilos tocándola a la vez. En el flujo normal ya está
        # terminado (self._cargando solo pasa a False después de que ese
        # hilo retorna de listar_criptas()); el join() es una red de
        # seguridad barata, no una espera real.
        if self._hilo_carga is not None:
            self._hilo_carga.join()
        nombre = self._nombre.strip() or NOMBRE_POR_DEFECTO
        self.contexto.audio.reproducir_sfx("menu_confirmar")
        self.contexto.controlador.iniciar_partida(cripta["id"], nombre, semilla=None)
        self.contexto.cambiar_escena(ESCENA_PARTIDA, None)

    def _elemento_en_posicion(self, pos):
        """-1 si 'pos' cae en el campo de nombre, el índice de la cripta si
        cae en una fila visible y seleccionable, o None si no hay nada ahí
        (incluida la lista mientras carga o con error: no es seleccionable)."""
        if self._layout.nombre_rect.collidepoint(pos):
            return -1
        with self._lock:
            cargando = self._cargando
            error = self._error_carga
            cantidad = len(self._criptas)
        if cargando or error is not None:
            return None
        for indice in range(cantidad):
            rect = self._rect_fila_pantalla(indice)
            if rect.bottom <= self._layout.viewport_top or rect.top >= self._layout.viewport_bottom:
                continue
            if rect.collidepoint(pos):
                return indice
        return None

    def _manejar_clic(self, pos):
        elemento = self._elemento_en_posicion(pos)
        if elemento is None:
            return
        if elemento == -1:
            self._foco = -1
            self._nombre_seleccionado = (self._nombre == NOMBRE_POR_DEFECTO)
            return
        with self._lock:
            cantidad = len(self._criptas)
        self._foco = elemento
        self._confirmar(cantidad)

    def _manejar_movimiento_mouse(self, pos):
        """Mover el mouse sobre una placa la selecciona (sin confirmar);
        el clic (_manejar_clic) sigue siendo quien confirma."""
        elemento = self._elemento_en_posicion(pos)
        if elemento is None or elemento == self._foco:
            return
        self._foco = elemento
        if elemento == -1:
            self._nombre_seleccionado = (self._nombre == NOMBRE_POR_DEFECTO)
        self.contexto.audio.reproducir_sfx("menu_mover")

    # -- actualización -----------------------------------------------

    def actualizar(self, dt_ms):
        self._tiempo_acumulado += dt_ms
        self._refrescar_layout_si_hace_falta()

    # -- dibujo --------------------------------------------------------

    def dibujar(self, pantalla):
        self._refrescar_layout_si_hace_falta()   # red de seguridad si no hubo actualizar() antes
        pantalla.fill(COLOR_FONDO)
        if self._fondo is not None:
            pantalla.blit(self._fondo, (self._layout.offset_x, self._layout.offset_y))

        with self._lock:
            cargando = self._cargando
            error = self._error_carga
            criptas = list(self._criptas)

        self._dibujar_titulo(pantalla, len(criptas))
        self._dibujar_nombre(pantalla)

        if cargando:
            puntos = "." * ((self._tiempo_acumulado // 400) % 4)
            self._dibujar_mensaje_estado(pantalla, "Consultando criptas" + puntos)
        elif error is not None:
            self._dibujar_mensaje_error(pantalla, error)
        elif not criptas:
            self._dibujar_mensaje_estado(pantalla, "No hay criptas disponibles")
        else:
            self._dibujar_lista(pantalla, criptas)

        self._dibujar_pie(pantalla)

        rect_actual = self._rect_elemento_actual(len(criptas))
        if rect_actual is not None:
            self._dibujar_flechas(pantalla, rect_actual)

    # -- placas al estilo del boceto: madera casi lisa + marco fino -------

    @staticmethod
    def _puntos_biselados(rect, corte):
        if corte <= 0:
            return [rect.topleft, rect.topright, rect.bottomright, rect.bottomleft]
        x0, y0, x1, y1 = rect.left, rect.top, rect.right, rect.bottom
        return [
            (x0 + corte, y0), (x1 - corte, y0), (x1, y0 + corte),
            (x1, y1 - corte), (x1 - corte, y1), (x0 + corte, y1),
            (x0, y1 - corte), (x0, y0 + corte),
        ]

    def _dibujar_placa(self, pantalla, rect, seleccionada=False):
        if seleccionada:
            self._dibujar_brillo_dorado(pantalla, rect)

        pantalla.fill(COLOR_SOMBRA_PLACA, rect.move(3, 3))   # sombra abajo a la derecha

        corte = min(3, rect.w // 4, rect.h // 4)
        puntos = self._puntos_biselados(rect, corte)
        pygame.draw.polygon(pantalla, COLOR_MADERA_BASE, puntos)

        y = rect.y + 4   # vetas muy sutiles, no un rayado denso
        while y < rect.bottom - 3:
            pygame.draw.line(pantalla, COLOR_VETA, (rect.x + 3, y), (rect.right - 4, y))
            y += 7

        interior = rect.inflate(-4, -4)
        if interior.w > 0 and interior.h > 0:
            puntos_interior = self._puntos_biselados(interior, max(0, corte - 1))
            pygame.draw.polygon(pantalla, COLOR_MARCO_INTERIOR, puntos_interior, 1)

        color_marco = COLOR_SELECCION_BORDE if seleccionada else COLOR_MARCO
        pygame.draw.polygon(pantalla, color_marco, puntos, 2)

    @staticmethod
    def _dibujar_brillo_dorado(pantalla, rect):
        """Resplandor dorado suave, 3-4 px por fuera del marco, con alpha
        bajo — el fondo de madera de la placa no cambia de color."""
        grosor = 4
        glow = pygame.Surface((rect.w + 2 * grosor, rect.h + 2 * grosor), pygame.SRCALPHA)
        centro = glow.get_rect()
        for i in range(grosor, 0, -1):
            alpha = int(45 * (grosor - i + 1) / grosor)
            inflado = centro.inflate(2 * i, 2 * i)
            pygame.draw.rect(glow, (*COLOR_SELECCION_BORDE, alpha), inflado, border_radius=3)
        pantalla.blit(glow, (rect.x - grosor, rect.y - grosor))

    @staticmethod
    def _dibujar_ornamento_titulo(pantalla, rect):
        """Esquinas con remate (escuadras doradas) y un pequeño diamante
        metálico centrado arriba, como en el boceto."""
        tam = 10
        for cx, cy, sx, sy in (
            (rect.left, rect.top, 1, 1), (rect.right, rect.top, -1, 1),
            (rect.left, rect.bottom, 1, -1), (rect.right, rect.bottom, -1, -1),
        ):
            puntos = [(cx, cy + sy * tam), (cx, cy), (cx + sx * tam, cy)]
            pygame.draw.lines(pantalla, COLOR_SELECCION_BORDE, False, puntos, 2)

        cx, cima = rect.centerx, rect.top - 10
        diamante = [(cx, cima - 8), (cx + 7, cima), (cx, cima + 8), (cx - 7, cima)]
        pygame.draw.polygon(pantalla, COLOR_MARCO_INTERIOR, diamante)
        pygame.draw.polygon(pantalla, COLOR_SELECCION_BORDE, diamante, 1)

    def _dibujar_titulo(self, pantalla, cantidad):
        rect = self._rect_titulo_actual()
        self._dibujar_placa(pantalla, rect)
        self._dibujar_ornamento_titulo(pantalla, rect)
        pantalla.blit(self._titulo_superficie, self._titulo_superficie.get_rect(center=rect.center))

        plural = "s" if cantidad != 1 else ""
        sub_texto = f"{cantidad} cripta{plural} disponible{plural}"
        rect_sub = self._rect_subtitulo_actual(sub_texto)
        self._dibujar_placa(pantalla, rect_sub)
        texto_sub = self._fuente_chica.render(sub_texto, True, COLOR_SUBTITULO_TEXTO)
        pantalla.blit(texto_sub, texto_sub.get_rect(center=rect_sub.center))

    def _dibujar_nombre(self, pantalla):
        rect = self._layout.nombre_rect
        seleccionada = self._foco == -1
        self._dibujar_placa(pantalla, rect, seleccionada=seleccionada)

        if self._nombre:
            texto = f"Nombre: {self._nombre}"
            color = COLOR_SELECCION_TEXTO if seleccionada else COLOR_TEXTO_PLACA
        else:
            texto = f"Nombre: {NOMBRE_POR_DEFECTO}"
            color = COLOR_PLACEHOLDER_NOMBRE
        render = self._fuente_normal.render(texto, True, color)
        centro = render.get_rect(center=rect.center)
        pantalla.blit(render, centro)

        if seleccionada and (self._tiempo_acumulado // 400) % 2 == 0:
            x_cursor = centro.right + 3 if self._nombre else centro.left
            pygame.draw.line(pantalla, COLOR_SELECCION_TEXTO,
                             (x_cursor, rect.centery - 10), (x_cursor, rect.centery + 10), 2)

    def _dibujar_lista(self, pantalla, criptas):
        layout = self._layout
        viewport = pygame.Rect(0, layout.viewport_top, ANCHO_LOGICO,
                               layout.viewport_bottom - layout.viewport_top)
        clip_anterior = pantalla.get_clip()
        pantalla.set_clip(viewport)

        cantidad = len(criptas)
        tope = cantidad if self._fondo_limpio else max(cantidad, 4)
        for indice in range(tope):
            rect = self._rect_fila_pantalla(indice)
            if rect.bottom < viewport.top or rect.top > viewport.bottom:
                continue
            if indice < cantidad:
                seleccionada = indice == self._foco
                self._dibujar_placa(pantalla, rect, seleccionada=seleccionada)
                color_texto = COLOR_SELECCION_TEXTO if seleccionada else COLOR_TEXTO_PLACA
                texto = self._texto_fila(criptas[indice])
                if self._fondo_limpio:
                    render = self._fuente_fila.render(texto, True, color_texto)
                else:
                    render = self._renderizar_fila_ajustada(
                        texto, rect.w - 2 * FILA_MARGEN_INTERNO, color_texto)
                pantalla.blit(render, render.get_rect(center=rect.center))
            else:
                self._dibujar_placa(pantalla, rect)   # placa vacía: tapa la fila pintada sobrante
        pantalla.set_clip(clip_anterior)

    def _dibujar_relleno_filas_vacias(self, pantalla, desde):
        if self._fondo_limpio:
            return
        for indice in range(desde, 4):
            self._dibujar_placa(pantalla, self._rect_fila_pantalla(indice))

    def _dibujar_mensaje_estado(self, pantalla, texto):
        rect = self._rect_mensaje()
        self._dibujar_placa(pantalla, rect)
        render = self._fuente_normal.render(texto, True, COLOR_TEXTO_TENUE)
        pantalla.blit(render, render.get_rect(center=rect.center))
        self._dibujar_relleno_filas_vacias(pantalla, desde=2)

    def _dibujar_mensaje_error(self, pantalla, error):
        rect = self._rect_mensaje()
        self._dibujar_placa(pantalla, rect)
        titulo = self._fuente_normal.render("Error al consultar criptas", True, COLOR_PELIGRO)
        pantalla.blit(titulo, (rect.x + 14, rect.y + 10))
        detalle = self._fuente_chica.render(str(error)[:70], True, COLOR_TEXTO_PLACA)
        pantalla.blit(detalle, (rect.x + 14, rect.y + 36))
        ayuda = self._fuente_chica.render("R: reintentar   Esc: salir", True, COLOR_AVISO)
        pantalla.blit(ayuda, (rect.x + 14, rect.bottom - 24))
        self._dibujar_relleno_filas_vacias(pantalla, desde=2)

    def _dibujar_pie(self, pantalla):
        texto = "Tab/↑↓ elegir · Enter jugar · Esc salir"
        pos_y = ALTO_LOGICO - 22
        sombra = self._fuente_chica.render(texto, True, COLOR_SOMBRA_PLACA)
        principal = self._fuente_chica.render(texto, True, COLOR_TEXTO_TENUE)
        rect = principal.get_rect(center=(ANCHO_LOGICO // 2, pos_y))
        pantalla.blit(sombra, (rect.x + 2, rect.y + 2))
        pantalla.blit(principal, rect)

    # -- flechas de selección: triángulos dorados, oscilan suavemente -----

    def _dibujar_flechas(self, pantalla, rect):
        fase = (self._tiempo_acumulado % FLECHA_PERIODO_MS) / FLECHA_PERIODO_MS
        desplazamiento = round(FLECHA_AMPLITUD * math.sin(2 * math.pi * fase))
        y = rect.centery
        self._dibujar_triangulo(pantalla, rect.left - 18 + desplazamiento, y, hacia_derecha=True)
        self._dibujar_triangulo(pantalla, rect.right + 8 - desplazamiento, y, hacia_derecha=False)

    @staticmethod
    def _dibujar_triangulo(pantalla, x, y, hacia_derecha):
        if hacia_derecha:
            puntos = [(x, y - 6), (x + 10, y), (x, y + 6)]
        else:
            puntos = [(x + 10, y - 6), (x, y), (x + 10, y + 6)]
        pygame.draw.polygon(pantalla, COLOR_FLECHA, puntos)
        pygame.draw.polygon(pantalla, COLOR_FLECHA_BORDE, puntos, 1)
