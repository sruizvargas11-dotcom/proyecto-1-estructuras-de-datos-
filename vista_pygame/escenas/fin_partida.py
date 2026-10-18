"""Resultado final, últimos mensajes y clasificación de la cripta jugada."""
import pygame
from vista_pygame.recursos.fuente_cripta import fuente_pixel_legible
from pathlib import Path
from vista_pygame.render.panel_mazmorra import PanelMazmorra
from vista_pygame.render.transiciones_cripta import suave
from vista_pygame.contratos import EscenaBase
from vista_pygame.render.muerte import AnimacionMuerte
from vista_pygame.render.victoria_cripta import SalidaCripta
from vista_pygame.recursos.temas_cripta import tema_por_cripta
from vista_pygame.render.boton_cerrar import dibujar_cerrar
from vista_pygame.config_vista import (
    COLOR_FONDO, COLOR_MADERA, COLOR_METAL, COLOR_ORO, COLOR_TEXTO,
    COLOR_TEXTO_TENUE, COLOR_PELIGRO, ESCENA_MENU,
)


class EscenaFinPartida(EscenaBase):
    def al_entrar(self, datos=None):
        self._paneles=PanelMazmorra()
        self._fuentes_legibles=[]
        self._stats_ms=1000
        self._fundido_stats=None
        self._fondo_stats=pygame.Surface((1280,720));self._fondo_stats.fill((12,17,25))
        self._resumen = datos or self.contexto.controlador.resumen_fin()
        tema=tema_por_cripta(self._resumen.id_cripta if self._resumen else '',
                            getattr(self.contexto,'nombre_cripta_actual',''))
        ruta=tema.recurso(Path(__file__).resolve().parents[2]/'assets','entrada')
        if ruta.is_file():
            self._fondo_stats=pygame.transform.scale(pygame.image.load(str(ruta)).convert(),(1280,720))
            self._fondo_stats.fill((53,60,76),special_flags=pygame.BLEND_RGB_MULT)
        self._filas = [fila for fila in self.contexto.controlador.tabla_puntajes()
                       if self._resumen is not None
                       and fila.id_cripta == self._resumen.id_cripta
                       and fila.version_cripta == self._resumen.version_cripta]
        self._mensajes = self.contexto.controlador.mensajes()[-4:]
        self._desplazamiento = 0
        self._seleccion = 1  # Enter vuelve al menú; salir exige selección explícita.
        self._viendo_stats = False
        self._cerrar=pygame.Rect(1210,24,38,38)
        self._botones = tuple(pygame.Rect(440,330+i*72,400,54) for i in range(3))
        self._volver = pygame.Rect(460,662,360,42)
        self._capa_menu = pygame.Surface((1280,720),pygame.SRCALPHA)
        self._muerte = None
        self._victoria = None
        fondo = getattr(self.contexto,'fondo_fin',None)
        jugador = getattr(self.contexto,'jugador_fin',None)
        if self._resumen and self._resumen.resultado=='victoria' and fondo is not None:
            self._victoria=SalidaCripta(self.contexto.assets,getattr(self.contexto,'equipo_fin',0),fondo,
                                         self._resumen.id_cripta,getattr(self.contexto,'nombre_cripta_actual',''))
            self._fondo_stats=self._victoria.fotograma_final()
        if self._resumen and self._resumen.resultado == 'derrota'  and fondo is not None and jugador:
            if hasattr(self.contexto.assets,'cuadros_muerte_equipo'):
                cuadros=self.contexto.assets.cuadros_muerte_equipo(getattr(self.contexto,'equipo_fin',0))
            else:cuadros=(self.contexto.assets.cuadros_muerte()
                         if hasattr(self.contexto.assets,'cuadros_muerte') else None)
            self._muerte = AnimacionMuerte(fondo,jugador[0],jugador[1],cuadros=cuadros)
        if self._resumen:
            self.contexto.audio.reproducir_musica(self._resumen.resultado)

    def al_salir(self):
        self._muerte = None
        self._victoria = None
        self.contexto.fondo_fin = None
        self.contexto.jugador_fin = None

    @property
    def interactiva(self):
        return ((self._muerte is None or self._muerte.terminada)
                and (self._victoria is None or self._victoria.terminada))

    def _cambiar_stats(self,valor):
        foto=pygame.Surface((1280,720));self._dibujar_pagina(foto)
        self._fundido_stats=foto;self._stats_ms=0;self._viendo_stats=valor

    def _activar(self):
        if self._viendo_stats:
            self._cambiar_stats(False)
            return
        if self._seleccion == 0:
            self._cambiar_stats(True)
        elif self._seleccion == 1:
            self.contexto.controlador.salir()
            self.contexto.cambiar_escena(ESCENA_MENU)
        else:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def manejar_evento(self, evento):
        if not self.interactiva or self._fundido_stats is not None:
            return
        if evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1 and self._cerrar.collidepoint(evento.pos):
            if self._viendo_stats:self._cambiar_stats(False)
            else:self._seleccion=1;self._activar()
            return
        if evento.type == pygame.KEYDOWN:
            if self._viendo_stats:
                if evento.key in (pygame.K_ESCAPE,pygame.K_RETURN):
                    self._cambiar_stats(False)
                elif evento.key in (pygame.K_PAGEUP,pygame.K_PAGEDOWN):
                    self._scroll(-6 if evento.key == pygame.K_PAGEUP else 6)
            elif evento.key in (pygame.K_LEFT,pygame.K_UP):
                self._seleccion = (self._seleccion-1)%3
            elif evento.key in (pygame.K_RIGHT,pygame.K_DOWN,pygame.K_TAB):
                cambio = -1 if getattr(evento,'mod',0)&pygame.KMOD_SHIFT else 1
                self._seleccion = (self._seleccion+cambio)%3
            elif evento.key in (pygame.K_RETURN,pygame.K_SPACE):
                self._activar()
            elif evento.key == pygame.K_ESCAPE:
                self._seleccion = 1
        elif evento.type == pygame.MOUSEWHEEL and self._viendo_stats:
            self._scroll(-evento.y)
        elif evento.type in (pygame.MOUSEMOTION,pygame.MOUSEBUTTONDOWN):
            if self._viendo_stats:
                if (evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1
                        and self._volver.collidepoint(evento.pos)):
                    self._cambiar_stats(False)
                return
            for indice,rect in enumerate(self._botones):
                if rect.collidepoint(evento.pos):
                    self._seleccion = indice
                    if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                        self._activar()

    def _scroll(self, delta):
        self._desplazamiento = max(0, min(max(0,len(self._filas)-6), self._desplazamiento+delta))

    def actualizar(self, dt_ms):
        self._stats_ms=min(1000,self._stats_ms+max(0,dt_ms))
        if self._stats_ms>=420:self._fundido_stats=None
        if self._muerte is not None:
            self._muerte.actualizar(dt_ms)
        if self._victoria is not None:self._victoria.actualizar(dt_ms)

    def _fuente(self,tamano):
        # Letras simples, con el mismo criterio de lectura del menú principal.
        for medida,fuente in self._fuentes_legibles:
            if medida==tamano:return fuente
        fuente=fuente_pixel_legible(tamano)
        self._fuentes_legibles.append((tamano,fuente))
        return fuente

    def _texto(self, pantalla, texto, posicion, tamano=18, color=COLOR_TEXTO, ancho=540):
        fuente = self._fuente(tamano)
        texto = str(texto)
        while fuente.size(texto)[0] > ancho and len(texto) > 1:
            texto = texto[:-2].rstrip('…')+'…'
        pantalla.blit(fuente.render(texto, False, color), posicion)

    def _panel(self, pantalla, rect):
        self._paneles.dibujar(pantalla,rect)

    def dibujar(self,pantalla):
        self._dibujar_pagina(pantalla)
        if self._fundido_stats is not None:
            self._fundido_stats.set_alpha(round(255*(1-suave(self._stats_ms/420))))
            pantalla.blit(self._fundido_stats,(0,0))

    def _dibujar_pagina(self, pantalla):
        if self._viendo_stats:
            self._dibujar_stats(pantalla)
            return
        if self._victoria is not None:
            self._victoria.dibujar(pantalla,self.contexto.assets)
            if self._victoria.opacidad_menu==0:return
        elif self._muerte is not None:
            self._muerte.dibujar(pantalla)
        else:
            pantalla.blit(self._fondo_stats,(0,0))
        capa = self._capa_menu
        capa.fill((0,0,0,0))
        resultado = self._resumen.resultado if self._resumen else 'en_curso'
        titulo = ('HAS MUERTO' if resultado == 'derrota' else
                  'VICTORIA' if resultado == 'victoria' else 'SESIÓN FINALIZADA')
        fuente = self._fuente(64)
        imagen = fuente.render(titulo,False,(245,235,218))
        sombra = fuente.render(titulo,False,(8,10,14))
        rect = imagen.get_rect(center=(640,145 if self._victoria else 220))
        if self._victoria:
            texto=self._fuente(24).render(f'Cripta superada · {self._victoria.tema.titulo}',False,(239,230,200))
            fondo_texto=self._fuente(24).render(f'Cripta superada · {self._victoria.tema.titulo}',False,(8,12,18))
            posicion=texto.get_rect(center=(640,196))
            for dx,dy in ((-2,0),(2,0),(0,-2),(0,2)):
                capa.blit(fondo_texto,posicion.move(dx,dy))
            capa.blit(texto,posicion)
        capa.blit(sombra,rect.move(3,3));capa.blit(imagen,rect)
        for i,(rect,nombre) in enumerate(zip(self._botones,
                ('Ver estadísticas','Volver al menú','Salir del juego'))):
            self._panel(capa,rect)
            color = COLOR_ORO if i == self._seleccion else COLOR_TEXTO
            if i == self._seleccion:
                pygame.draw.rect(capa,COLOR_ORO,rect,3)
            texto = self._fuente(26).render(nombre,False,color)
            capa.blit(texto,texto.get_rect(center=rect.center))
        dibujar_cerrar(capa,self._cerrar)
        capa.set_alpha(self._victoria.opacidad_menu if self._victoria else
                       self._muerte.opacidad_menu if self._muerte else 255)
        pantalla.blit(capa,(0,0))

    def _dibujar_stats(self, pantalla):
        pantalla.blit(self._fondo_stats,(0,0))
        dibujar_cerrar(pantalla,self._cerrar)
        r = self._resumen
        resultado = r.resultado if r else 'en_curso'
        titulo = ('HAS MUERTO' if resultado == 'derrota' else
                  'CRIPTA SUPERADA' if resultado == 'victoria' else 'SESIÓN FINALIZADA')
        color = COLOR_PELIGRO if resultado == 'derrota' else COLOR_ORO
        self._texto(pantalla, titulo, (50,35), 46, color, 1180)
        self._texto(pantalla, 'CRÓNICA DE LA EXPEDICIÓN · Tu nombre queda en la piedra.',
                    (52,100), 20, ancho=1180)
        self._panel(pantalla, pygame.Rect(48,150,550,380))
        self._panel(pantalla, pygame.Rect(630,150,602,380))
        self._texto(pantalla, 'Resumen de la partida', (68,170), 24, COLOR_ORO)
        if r:
            lineas = [f'Jugador: {r.nombre_jugador}', f'Cripta: {r.id_cripta}',
                      f'Versión: {r.version_cripta}',
                      f'Acciones: {r.acciones_jugador}   Enemigos: {r.enemigos_derrotados}',
                      f'Tiempo virtual: {r.tiempo_final}',
                      f'Red: {r.solicitudes_realizadas}/{r.presupuesto_solicitudes} solicitudes',
                      f'Caché: {r.aciertos_cache} aciertos / {r.fallos_cache} fallos']
            for i,linea in enumerate(lineas):
                self._texto(pantalla,linea,(68,220+i*36),18,ancho=510)
        self._texto(pantalla,'Puntajes de esta cripta y versión',(650,170),22,COLOR_ORO)
        columnas=(650,684,842,988,1058,1125)
        for x,nombre in zip(columnas,('N°','Jugador','Resultado','Bajas','Acc.','Tiempo')):
            self._texto(pantalla,nombre,(x,208),16,COLOR_TEXTO_TENUE,125)
        for indice,fila in enumerate(self._filas[self._desplazamiento:self._desplazamiento+6],self._desplazamiento+1):
            y=245+(indice-self._desplazamiento-1)*36
            if fila.es_actual:
                pygame.draw.rect(pantalla,(65,57,37),(644,y-3,572,29),border_radius=3)
            valores=(indice,fila.nombre_jugador[:14],fila.resultado,fila.enemigos_derrotados,fila.acciones_jugador,fila.tiempo_final)
            for x,valor,ancho in zip(columnas,valores,(28,150,140,64,64,84)):
                self._texto(pantalla,str(valor),(x,y),16,COLOR_ORO if fila.es_actual else COLOR_TEXTO,ancho)
        if not self._filas:
            self._texto(pantalla,'No hay puntajes disponibles.',(650,260),18)
        self._texto(pantalla,'Rueda o RePág/AvPág: recorrer puntajes',(650,500),16,COLOR_TEXTO_TENUE)
        self._panel(pantalla, pygame.Rect(48,546,1184,100))
        for i,mensaje in enumerate(self._mensajes):
            self._texto(pantalla,mensaje,(64,554+i*21),16,ancho=1150)
        self._panel(pantalla,self._volver)
        pygame.draw.rect(pantalla,COLOR_ORO,self._volver,3)
        self._texto(pantalla,'Volver  (Esc / Enter)',(self._volver.x+36,self._volver.y+10),20,COLOR_ORO,310)
