"""Bucle principal de la vista Pygame: ventana, reloj de FPS, cambio de
escenas y cierre controlado. No contiene reglas del juego: eso vive en el
modelo, detrás de ControladorPygame (hilo de fondo, ver ese módulo).

Las escenas se registran en una lista indexada por las constantes de
config_vista.py (ESCENA_MENU, ESCENA_PARTIDA, ...), nunca un dict.
"""
import pygame
import threading

from vista_pygame.config_vista import (
    ALTO_LOGICO, ANCHO_LOGICO, CANTIDAD_ESCENAS, ESCENA_FIN_PARTIDA, ESCENA_INVENTARIO,
    ESCENA_MENU, ESCENA_PARTIDA, ESCENA_PAUSA, FPS_OBJETIVO, TITULO_VENTANA,
)
from controlador.controlador_pygame import ControladorPygame
from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.escenas.inicio import EscenaInicio
from vista_pygame.escenas.partida import EscenaPartida
from vista_pygame.escenas.fin_partida import EscenaFinPartida
from vista_pygame.stubs_temporales import (
    EscenaInventarioTemporal,
    EscenaPausaTemporal, GestorAudioTemporal,
)


class Contexto:
    """Lo que recibe cada escena (ver vista_pygame.contratos.EscenaBase): controlador, assets,
    audio y cambiar_escena. La app real detrás de cambiar_escena no es parte
    del contrato, por eso queda privada."""

    def __init__(self, controlador, assets, audio, app):
        self.controlador = controlador
        self.assets = assets
        self.audio = audio
        # Captura de presentación para la transición de muerte. No es estado
        # del modelo: se libera al abandonar la pantalla final.
        self.fondo_fin = None
        self.jugador_fin = None
        self.equipo_fin = 0
        self._app = app
        self.entrada_cinematica=False
        self.fondo_entrada=None
        self._hilo_inicio=None
        self.error_inicio=None
        self.objeto_inventario_seleccionado=None

    def cambiar_escena(self, id_escena, datos=None):
        self._app.cambiar_escena(id_escena, datos)


    def iniciar_cripta(self,datos):
        self.objeto_inventario_seleccionado=None
        self.fondo_entrada=self._app._pantalla.copy()
        self.entrada_cinematica=True
        self.cambiar_escena(ESCENA_PARTIDA,datos)

    def arrancar_partida(self,datos):
        self.error_inicio=None
        def arrancar():
            try:self.controlador.iniciar_partida(*datos)
            except Exception as error:self.error_inicio=str(error)
        self._hilo_inicio=threading.Thread(target=arrancar,name='cripta-arranque',daemon=False)
        self._hilo_inicio.start()

    def iniciando(self):
        return self._hilo_inicio is not None and self._hilo_inicio.is_alive()


class AppPygame:
    def __init__(self, fuente, carpeta_cache=None, cache_size=25, partidas_dir="partidas", reportes=None):
        pygame.init()
        self._pantalla = pygame.display.set_mode((ANCHO_LOGICO, ALTO_LOGICO),pygame.RESIZABLE)
        pygame.display.set_caption(TITULO_VENTANA)
        self._lienzo = pygame.Surface((ANCHO_LOGICO,ALTO_LOGICO))
        self._pantalla_completa = False
        self._tamano_ventana = (ANCHO_LOGICO,ALTO_LOGICO)
        self._reloj = pygame.time.Clock()

        controlador = ControladorPygame(fuente, carpeta_cache, cache_size, partidas_dir, reportes)
        assets = CargadorAssets()
        audio = GestorAudioTemporal()
        self._contexto = Contexto(controlador, assets, audio, self)

        self._escenas = [None] * CANTIDAD_ESCENAS
        self._escenas[ESCENA_MENU] = EscenaInicio(self._contexto)
        self._escenas[ESCENA_PARTIDA] = EscenaPartida(self._contexto)
        self._escenas[ESCENA_INVENTARIO] = EscenaInventarioTemporal(self._contexto)
        self._escenas[ESCENA_PAUSA] = EscenaPausaTemporal(self._contexto)
        self._escenas[ESCENA_FIN_PARTIDA] = EscenaFinPartida(self._contexto)

        self._actual = ESCENA_MENU
        self._escenas[self._actual].al_entrar()
        self._corriendo = True
        self._fundido = None
        self._fundido_ms = 700

    def cambiar_escena(self, id_escena, datos=None):
        reanudar=(id_escena==ESCENA_PARTIDA and datos is None and self._actual in (ESCENA_INVENTARIO,ESCENA_PAUSA))
        # La entrada y la muerte tienen su propia secuencia de fundidos.
        if id_escena not in (ESCENA_PARTIDA,ESCENA_FIN_PARTIDA):
            self._fundido=self._pantalla.copy();self._fundido_ms=0
        self._escenas[self._actual].al_salir()
        self._actual = id_escena
        if reanudar:
            # Mantener la foto anterior: los impactos pendientes aún deben verse.
            self._escenas[self._actual]._comando_enviado=self._contexto.controlador.esperando_red()
        else:self._escenas[self._actual].al_entrar(datos)

    def _viewport(self):
        w,h=self._pantalla.get_size();escala=min(w/ANCHO_LOGICO,h/ALTO_LOGICO)
        rect=pygame.Rect(0,0,round(ANCHO_LOGICO*escala),round(ALTO_LOGICO*escala))
        rect.center=(w//2,h//2)
        return rect

    def _alternar_pantalla_completa(self):
        if self._pantalla_completa:
            self._pantalla=pygame.display.set_mode(self._tamano_ventana,pygame.RESIZABLE)
        else:
            self._tamano_ventana=self._pantalla.get_size()
            self._pantalla=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
        self._pantalla_completa=not self._pantalla_completa
        self._escenas[ESCENA_MENU].establecer_tamano(self._pantalla.get_size())

    def ejecutar(self):
        """Todas las llamadas a pygame ocurren aquí, en el hilo principal."""
        try:
            while self._corriendo:
                dt_ms = self._reloj.tick(FPS_OBJETIVO)
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        self._corriendo = False
                    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
                        self._alternar_pantalla_completa()
                    elif evento.type == pygame.VIDEORESIZE and not self._pantalla_completa:
                        self._pantalla = pygame.display.set_mode((max(640,evento.w),max(400,evento.h)),pygame.RESIZABLE)
                        self._escenas[ESCENA_MENU].establecer_tamano(self._pantalla.get_size())
                    else:
                        if self._fundido_ms<700:continue
                        if evento.type == pygame.MOUSEWHEEL:
                            evento = pygame.event.Event(evento.type, dict(evento.dict, pos=pygame.mouse.get_pos()))
                        if self._actual != ESCENA_MENU and hasattr(evento,'pos'):
                            viewport=self._viewport()
                            if not viewport.collidepoint(evento.pos):
                                continue
                            nuevo=pygame.event.Event(evento.type,evento.dict)
                            nuevo.pos=(round((evento.pos[0]-viewport.x)*ANCHO_LOGICO/viewport.w),
                                       round((evento.pos[1]-viewport.y)*ALTO_LOGICO/viewport.h))
                            evento=nuevo
                        self._escenas[self._actual].manejar_evento(evento)
                self._escenas[self._actual].actualizar(dt_ms)
                if self._actual == ESCENA_MENU:
                    self._escenas[self._actual].dibujar(self._pantalla)
                else:
                    self._escenas[self._actual].dibujar(self._lienzo)
                    self._pantalla.fill((12,14,20))
                    viewport=self._viewport()
                    self._pantalla.blit(pygame.transform.scale(self._lienzo,viewport.size),viewport)

                if self._fundido is not None:
                    self._fundido_ms=min(700,self._fundido_ms+max(0,dt_ms))
                    if self._fundido_ms<300:
                        self._pantalla.blit(pygame.transform.scale(self._fundido,self._pantalla.get_size()),(0,0))
                        alpha=round(255*self._fundido_ms/300)
                    else:alpha=round(255*(1-(self._fundido_ms-300)/400))
                    velo=pygame.Surface(self._pantalla.get_size(),pygame.SRCALPHA)
                    velo.fill((5,8,14,max(0,alpha)));self._pantalla.blit(velo,(0,0))
                    if self._fundido_ms>=700:self._fundido=None
                pygame.display.flip()
        finally:
            # Cierre ordenado: pide salir y espera (join) a que el hilo de
            # modelo termine de verdad, nunca lo abandona a medias.
            try:
                self._contexto.controlador.cancelar_red()
                if self._contexto._hilo_inicio is not None:
                    self._contexto._hilo_inicio.join()
                consulta = getattr(self._escenas[ESCENA_MENU], '_hilo_carga', None)
                if consulta is not None:
                    consulta.join()
                self._contexto.controlador.salir()
            finally:
                pygame.quit()


def ejecutar(fuente, carpeta_cache=None, cache_size=25, partidas_dir="partidas", reportes=None):
    AppPygame(fuente, carpeta_cache, cache_size, partidas_dir, reportes).ejecutar()
