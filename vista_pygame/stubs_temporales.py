"""Placeholders temporales de lo que implementa mi compañero.

Rectángulos de colores en vez de sprites, audio silencioso, y escenas
secundarias mínimas (menú de criptas, inventario, pausa, fin de partida) que
cumplen el contrato de EscenaBase lo justo para poder jugar y probar de
punta a punta mientras esos archivos reales no existen. Nada de esto se usa
si mi compañero ya publicó sus propios módulos: app.py decide cuál cargar.

Sin dict como caché/índice (regla del curso): los "cachés" de assets son un
Vector recorrido linealmente, igual que el resto del proyecto.
"""
import pygame

from estructuras.vector_dinamico import Vector
from vista_pygame.config_vista import (
    COLOR_FONDO, COLOR_MADERA, COLOR_MADERA_CLARA, COLOR_METAL, COLOR_METAL_OSCURO,
    COLOR_ORO, COLOR_TEXTO, COLOR_TEXTO_TENUE, ESCENA_FIN_PARTIDA, ESCENA_MENU,
    ESCENA_PARTIDA, ESCENA_PAUSA,
)
from vista_pygame.contratos import CargadorAssets, ColaAnimaciones, EscenaBase, GestorAudio


def _superficie_color(ancho, alto, color):
    superficie = pygame.Surface((ancho, alto)).convert()
    superficie.fill(color)
    return superficie


class CargadorAssetsTemporal(CargadorAssets):
    """Un color reproducible por clave (derivado del texto), no por azar:
    el mismo tipo_id siempre da el mismo rectángulo entre partidas."""

    def __init__(self):
        self._fuentes = Vector()       # pares (tamano, Font)
        self._superficies = Vector()   # pares (clave, Surface)

    @staticmethod
    def _color_desde_texto(texto):
        valor = sum(ord(c) for c in texto) if texto else 1
        return (70 + valor * 7 % 160, 70 + valor * 13 % 160, 70 + valor * 19 % 160)

    def _cacheada(self, clave, ancho, alto, color):
        for k, superficie in self._superficies:
            if k == clave:
                return superficie
        superficie = _superficie_color(ancho, alto, color)
        self._superficies.agregarValor((clave, superficie))
        return superficie

    def sprite_jugador(self, estado, direccion):
        return self._cacheada(f"jugador:{estado}:{direccion}", 40, 64, (90, 140, 190))

    def sprite_enemigo(self, id_tipo, comportamiento):
        return self._cacheada(f"enemigo:{id_tipo}", 40, 52, self._color_desde_texto(id_tipo))

    def sprite_objeto(self, id_tipo, clase):
        return self._cacheada(f"objeto:{id_tipo}", 22, 22, self._color_desde_texto(id_tipo))

    def sprite_entorno(self, nombre):
        return self._cacheada(f"entorno:{nombre}", 64, 64, self._color_desde_texto(nombre))

    def sprite_efecto(self, nombre):
        return self._cacheada(f"efecto:{nombre}", 28, 28, (200, 120, 60))

    def icono(self, nombre):
        return self._cacheada(f"icono:{nombre}", 18, 18, COLOR_ORO)

    def fuente(self, tamano):
        for t, fuente in self._fuentes:
            if t == tamano:
                return fuente
        fuente = pygame.font.SysFont("consolas", tamano)
        self._fuentes.agregarValor((tamano, fuente))
        return fuente


class GestorAudioTemporal(GestorAudio):
    """Silencioso: no reproduce nada, pero no falla si audio no está
    disponible (p. ej. SDL_AUDIODRIVER=dummy en pruebas)."""

    def __init__(self):
        self._disponible = False
        self._mute = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            self._disponible = pygame.mixer.get_init() is not None
        except pygame.error:
            self._disponible = False

    @property
    def disponible(self):
        return self._disponible

    def reproducir_musica(self, estado):
        pass

    def reproducir_sfx(self, tipo_evento):
        pass

    def set_volumen(self, musica, sfx):
        pass

    def alternar_mute(self):
        self._mute = not self._mute
        return self._mute


class ColaAnimacionesTemporal(ColaAnimaciones):
    """No anima nada: solo consume los eventos para que la escena de partida
    pueda probarse de punta a punta sin esperar al arte final."""

    def __init__(self):
        self._pendientes = Vector()

    @property
    def ocupada(self):
        return False

    def agregar_desde_eventos(self, eventos):
        for evento in eventos:
            self._pendientes.agregarValor(evento)

    def actualizar(self, dt_ms):
        self._pendientes = Vector()

    def dibujar(self, pantalla):
        pass


# ---------------------------------------------------------------------------
# Escenas secundarias mínimas
# ---------------------------------------------------------------------------

def _panel(pantalla, rect, titulo, fuente):
    pygame.draw.rect(pantalla, COLOR_MADERA, rect)
    pygame.draw.rect(pantalla, COLOR_METAL, rect, 3)
    if titulo:
        texto = fuente.render(titulo, True, COLOR_ORO)
        pantalla.blit(texto, (rect.x + 16, rect.y + 12))


class EscenaMenuCriptasTemporal(EscenaBase):
    """Placeholder: lista las criptas y Enter inicia la primera con un
    nombre de jugador fijo. Mi compañero la reemplaza por el menú real."""

    def al_entrar(self, datos=None):
        self._fuente = self.contexto.assets.fuente(22)
        try:
            self._criptas = self.contexto.controlador.listar_criptas()
            self._error = None
        except (OSError, ValueError, RuntimeError) as error:
            self._criptas = []
            self._error = str(error)

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_RETURN and self._criptas:
            self.contexto.cambiar_escena(
                ESCENA_PARTIDA, (self._criptas[0]["id"], "Jugador", None))

    def actualizar(self, dt_ms):
        pass

    def dibujar(self, pantalla):
        pantalla.fill(COLOR_FONDO)
        _panel(pantalla, pygame.Rect(360, 120, 560, 420), "CRIPTA (placeholder)", self._fuente)
        y = 180
        if self._error:
            pantalla.blit(self._fuente.render(f"Error: {self._error}", True, (220, 100, 100)),
                          (400, y))
        for cripta in self._criptas:
            texto = f"{cripta['id']}: {cripta['nombre']}"
            pantalla.blit(self._fuente.render(texto, True, COLOR_TEXTO), (400, y))
            y += 34
        ayuda = self._fuente.render("Enter: jugar la primera cripta", True, COLOR_TEXTO_TENUE)
        pantalla.blit(ayuda, (400, 480))


class EscenaInventarioTemporal(EscenaBase):
    def al_entrar(self, datos=None):
        self._fuente = self.contexto.assets.fuente(20)

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self.contexto.cambiar_escena(ESCENA_PARTIDA)

    def actualizar(self, dt_ms):
        pass

    def dibujar(self, pantalla):
        pantalla.fill(COLOR_FONDO)
        _panel(pantalla, pygame.Rect(260, 100, 760, 500), "Inventario (placeholder)", self._fuente)
        estado = self.contexto.controlador.estado()
        y = 160
        if estado:
            for objeto in estado.inventario:
                marca = " [equipado]" if objeto.equipado else ""
                texto = f"{objeto.nombre}{marca}"
                pantalla.blit(self._fuente.render(texto, True, COLOR_TEXTO), (300, y))
                y += 28
        ayuda = self._fuente.render("Esc: volver", True, COLOR_TEXTO_TENUE)
        pantalla.blit(ayuda, (300, 560))


class EscenaPausaTemporal(EscenaBase):
    def al_entrar(self, datos=None):
        self._fuente = self.contexto.assets.fuente(22)

    def manejar_evento(self, evento):
        if evento.type != pygame.KEYDOWN:
            return
        controlador = self.contexto.controlador
        if evento.key == pygame.K_ESCAPE:
            self.contexto.cambiar_escena(ESCENA_PARTIDA)
        elif evento.key == pygame.K_g:
            controlador.guardar()
        elif evento.key == pygame.K_l:
            controlador.cargar()
        elif evento.key == pygame.K_q:
            controlador.salir()
            self.contexto.cambiar_escena(ESCENA_MENU)

    def actualizar(self, dt_ms):
        pass

    def dibujar(self, pantalla):
        pantalla.fill(COLOR_FONDO)
        _panel(pantalla, pygame.Rect(440, 220, 400, 280), "Pausa (placeholder)", self._fuente)
        lineas = ["Esc: continuar", "G: guardar", "L: cargar", "Q: salir al menú"]
        y = 280
        for linea in lineas:
            pantalla.blit(self._fuente.render(linea, True, COLOR_TEXTO), (480, y))
            y += 34


class EscenaFinPartidaTemporal(EscenaBase):
    def al_entrar(self, datos=None):
        self._fuente = self.contexto.assets.fuente(22)
        self._resumen = datos

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_RETURN:
            self.contexto.cambiar_escena(ESCENA_MENU)

    def actualizar(self, dt_ms):
        pass

    def dibujar(self, pantalla):
        pantalla.fill(COLOR_FONDO)
        _panel(pantalla, pygame.Rect(360, 140, 560, 420), "Fin de la partida (placeholder)",
              self._fuente)
        y = 210
        r = self._resumen
        if r is not None:
            lineas = [
                f"Resultado: {r.resultado}", f"Jugador: {r.nombre_jugador}",
                f"Cripta: {r.id_cripta} ({r.version_cripta})",
                f"Acciones: {r.acciones_jugador}", f"Enemigos derrotados: {r.enemigos_derrotados}",
                f"Tiempo final: {r.tiempo_final}",
                f"Solicitudes: {r.solicitudes_realizadas}/{r.presupuesto_solicitudes}",
                f"Caché: {r.aciertos_cache} aciertos, {r.fallos_cache} fallos",
            ]
            for linea in lineas:
                pantalla.blit(self._fuente.render(linea, True, COLOR_TEXTO), (400, y))
                y += 30
        ayuda = self._fuente.render("Enter: volver al menú", True, COLOR_TEXTO_TENUE)
        pantalla.blit(ayuda, (400, 520))
