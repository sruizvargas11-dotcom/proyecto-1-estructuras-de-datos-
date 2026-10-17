"""Escena de partida: sala actual, HUD, enemigos y el bucle de una acción
del jugador = una llamada al controlador (ver ANALISIS_ARQUITECTURA.md §7).

No decide nada del juego: traduce teclas a comandos de texto (igual que la
consola), lee EstadoPartida/eventos ya publicados por ControladorPygame, y
dibuja. Nunca llama a un método del modelo directamente.
"""
import pygame

from vista.vista_consola import AYUDA
from vista_pygame.config_vista import (
    ALTO_LOGICO, ALTO_PANEL_MENSAJES, ANCHO_LOGICO, ANCHO_PANEL_HUD,
    CANTIDAD_PROXIMOS_TURNOS, COLOR_AVISO, COLOR_FONDO, COLOR_MADERA, COLOR_METAL,
    COLOR_ORO, COLOR_PELIGRO, COLOR_TEXTO, COLOR_TEXTO_TENUE, COLOR_VENENO, COLOR_VIDA,
    COLOR_VIDA_FONDO, ESCENA_FIN_PARTIDA,
)
from vista_pygame.contratos import EscenaBase
from vista_pygame.entrada.mapeo_teclas import accion_para_evento
from vista_pygame.render.render_actores import (dibujar_enemigos, dibujar_jugador,
                                                siguiente_objetivo)
from vista_pygame.render.render_sala import calcular_layout_minimapa, dibujar_minimapa, dibujar_sala
from vista_pygame.stubs_temporales import ColaAnimacionesTemporal

HUD_RECT = pygame.Rect(ANCHO_LOGICO - ANCHO_PANEL_HUD, 0, ANCHO_PANEL_HUD, ALTO_LOGICO)
MINIMAPA_RECT = pygame.Rect(ANCHO_LOGICO - ANCHO_PANEL_HUD + 16, 16,
                            ANCHO_PANEL_HUD - 32, 140)
MENSAJES_RECT = pygame.Rect(40, ALTO_LOGICO - ALTO_PANEL_MENSAJES - 20,
                            760, ALTO_PANEL_MENSAJES)

COMANDOS_SIN_INDICE = ("N", "S", "E", "O", "W")


class EscenaPartida(EscenaBase):
    def al_entrar(self, datos=None):
        # datos is None cuando quien cambió a esta escena (menu_criptas) ya
        # llamó iniciar_partida() ella misma, para poder encolar esa llamada
        # desde su propio Enter/clic (ver escenas/menu_criptas.py). Con la
        # tupla (id_cripta, nombre_jugador, semilla), se inicia acá como
        # antes, para cualquier otro llamador que siga ese contrato.
        if datos is not None:
            id_cripta, nombre_jugador, semilla = datos
            self.contexto.controlador.iniciar_partida(id_cripta, nombre_jugador, semilla)
        self._objetivo_indice = None
        self._mostrar_ayuda = False
        self._mostrar_minimapa = True
        self._layout_minimapa = None
        self._animaciones = ColaAnimacionesTemporal()
        self._fin_enviado = False
        self._error_mostrado = None

    def al_salir(self):
        self._layout_minimapa = None

    # -- entrada -----------------------------------------------------

    def manejar_evento(self, evento):
        if self._error_mostrado is not None:
            return   # con un error de fondo no se aceptan más acciones
        accion = accion_para_evento(evento)
        if accion is None:
            return
        categoria, valor = accion
        controlador = self.contexto.controlador

        if categoria == "comando":
            texto = valor
            if valor == "A":
                texto = f"A {self._objetivo_indice}" if self._objetivo_indice else "A"
            controlador.enviar_comando(texto)
        elif categoria == "ui":
            if valor == "siguiente_objetivo":
                estado = controlador.estado()
                if estado is not None:
                    self._objetivo_indice = siguiente_objetivo(estado, self._objetivo_indice)
            elif valor == "ayuda":
                self._mostrar_ayuda = not self._mostrar_ayuda
            elif valor == "minimapa":
                self._mostrar_minimapa = not self._mostrar_minimapa
        elif categoria == "escena":
            self.contexto.cambiar_escena(valor)

    # -- actualización -------------------------------------------------

    def actualizar(self, dt_ms):
        controlador = self.contexto.controlador
        self._error_mostrado = controlador.error_pendiente()

        if self._layout_minimapa is None and controlador.topologia_cripta():
            self._layout_minimapa = calcular_layout_minimapa(
                controlador.topologia_cripta(), controlador.sala_inicial_id())

        eventos = controlador.eventos_nuevos()
        if eventos:
            self._animaciones.agregar_desde_eventos(eventos)
            for evento in eventos:
                tipo = getattr(evento, "tipo", None)
                if tipo in ("ataque", "movimiento", "mensaje"):
                    self.contexto.audio.reproducir_sfx(tipo)
        self._animaciones.actualizar(dt_ms)

        estado = controlador.estado()
        if (not self._fin_enviado and estado is not None
                and estado.estado in ("victoria", "derrota")):
            resumen = controlador.resumen_fin()
            if resumen is not None:
                self._fin_enviado = True
                self.contexto.cambiar_escena(ESCENA_FIN_PARTIDA, resumen)

    # -- dibujo ----------------------------------------------------------

    def dibujar(self, pantalla):
        pantalla.fill(COLOR_FONDO)
        assets = self.contexto.assets
        controlador = self.contexto.controlador
        estado = controlador.estado()

        if estado is None:
            texto = assets.fuente(26).render("Entrando a la cripta...", True, COLOR_TEXTO)
            pantalla.blit(texto, texto.get_rect(center=(ANCHO_LOGICO // 2, ALTO_LOGICO // 2)))
            return

        dibujar_sala(pantalla, assets, estado)
        dibujar_jugador(pantalla, assets, estado, controlador.nombre_jugador or "Jugador")
        dibujar_enemigos(pantalla, assets, estado, self._objetivo_indice)
        self._animaciones.dibujar(pantalla)

        self._dibujar_hud(pantalla, assets, estado)
        self._dibujar_mensajes(pantalla, assets, controlador)
        if self._mostrar_minimapa and self._layout_minimapa:
            dibujar_minimapa(pantalla, MINIMAPA_RECT, self._layout_minimapa,
                             estado.salas_visitadas, estado.sala_id, assets.fuente(14))
        if self._mostrar_ayuda:
            self._dibujar_ayuda(pantalla, assets)
        if self._error_mostrado is not None:
            self._dibujar_error(pantalla, assets)

    def _dibujar_hud(self, pantalla, assets, estado):
        pygame.draw.rect(pantalla, COLOR_MADERA, HUD_RECT)
        pygame.draw.rect(pantalla, COLOR_METAL, HUD_RECT, 3)
        fuente = assets.fuente(18)
        fuente_chica = assets.fuente(15)
        x, y = HUD_RECT.x + 16, MINIMAPA_RECT.bottom + 20

        pantalla.blit(fuente.render(f"t = {estado.tiempo}", True, COLOR_TEXTO_TENUE), (x, y))
        y += 26
        pantalla.blit(fuente.render(
            f"Vida {estado.jugador.vida}/{estado.jugador.vida_max}", True, COLOR_TEXTO), (x, y))
        y += 22
        pygame.draw.rect(pantalla, COLOR_VIDA_FONDO, (x, y, ANCHO_PANEL_HUD - 32, 10))
        if estado.jugador.vida_max:
            lleno = int((ANCHO_PANEL_HUD - 32) * estado.jugador.vida / estado.jugador.vida_max)
            pygame.draw.rect(pantalla, COLOR_VIDA, (x, y, max(0, lleno), 10))
        y += 24
        pantalla.blit(fuente_chica.render(
            f"Ataque {estado.ataque}  Defensa {estado.defensa}  Vel {estado.velocidad}",
            True, COLOR_TEXTO), (x, y))
        y += 24
        equipo = estado.arma_equipada or "sin arma"
        if estado.armadura_equipada:
            equipo += f", {estado.armadura_equipada}"
        pantalla.blit(fuente_chica.render(f"Equipo: {equipo}", True, COLOR_TEXTO_TENUE), (x, y))
        y += 26

        pantalla.blit(fuente.render("Efectos:", True, COLOR_ORO), (x, y)); y += 22
        if estado.efectos:
            for efecto in estado.efectos:
                pantalla.blit(fuente_chica.render(efecto, True, COLOR_VENENO), (x, y))
                y += 20
        else:
            pantalla.blit(fuente_chica.render("ninguno", True, COLOR_TEXTO_TENUE), (x, y))
            y += 20
        y += 8

        pantalla.blit(fuente.render("Salidas:", True, COLOR_ORO), (x, y)); y += 22
        for salida in estado.salidas:
            if salida.cerrada:
                estado_txt = "con llave" if salida.tiene_llave else "cerrada"
            else:
                estado_txt = "abierta"
            texto = f"{salida.direccion} {salida.nombre_destino} ({estado_txt})"
            color = COLOR_TEXTO if not salida.cerrada or salida.tiene_llave else COLOR_PELIGRO
            pantalla.blit(fuente_chica.render(texto, True, color), (x, y))
            y += 20
        y += 8

        if estado.proximos_turnos:
            pantalla.blit(fuente.render("Próximos turnos:", True, COLOR_ORO), (x, y)); y += 22
            for turno in estado.proximos_turnos[:CANTIDAD_PROXIMOS_TURNOS]:
                texto = f"t={turno.tiempo}  {turno.etiqueta}"
                pantalla.blit(fuente_chica.render(texto, True, COLOR_TEXTO_TENUE), (x, y))
                y += 20

    def _dibujar_mensajes(self, pantalla, assets, controlador):
        pygame.draw.rect(pantalla, (14, 16, 22), MENSAJES_RECT)
        pygame.draw.rect(pantalla, COLOR_METAL, MENSAJES_RECT, 2)
        fuente = assets.fuente(14)
        mensajes = controlador.mensajes()[-8:]   # las últimas caben en el panel visible
        y = MENSAJES_RECT.y + 6
        for mensaje in mensajes:
            pantalla.blit(fuente.render(mensaje, True, COLOR_TEXTO), (MENSAJES_RECT.x + 8, y))
            y += 18

    def _dibujar_ayuda(self, pantalla, assets):
        overlay = pygame.Surface((ANCHO_LOGICO, ALTO_LOGICO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        pantalla.blit(overlay, (0, 0))
        fuente = assets.fuente(16)
        y = 40
        for linea in AYUDA.split("\n"):
            pantalla.blit(fuente.render(linea, True, COLOR_TEXTO), (80, y))
            y += 22
        pantalla.blit(assets.fuente(16).render("F1: cerrar esta ayuda", True, COLOR_AVISO),
                      (80, y + 10))

    def _dibujar_error(self, pantalla, assets):
        overlay = pygame.Surface((ANCHO_LOGICO, ALTO_LOGICO), pygame.SRCALPHA)
        overlay.fill((40, 0, 0, 200))
        pantalla.blit(overlay, (0, 0))
        fuente = assets.fuente(18)
        titulo = assets.fuente(26).render("Error inesperado en el modelo", True, COLOR_PELIGRO)
        pantalla.blit(titulo, (80, 60))
        y = 110
        for linea in self._error_mostrado.strip().split("\n")[-20:]:
            pantalla.blit(fuente.render(linea[:140], True, COLOR_TEXTO), (80, y))
            y += 20
