"""Escena de partida: sala actual, HUD, enemigos y el bucle de una acción
del jugador = una llamada al controlador (ver ControladorPygame.enviar_comando).

No decide nada del juego: traduce teclas a comandos de texto (igual que la
consola), lee EstadoPartida/eventos ya publicados por ControladorPygame, y
dibuja. Nunca llama a un método del modelo directamente.
"""
import pygame
from dataclasses import replace

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
                                                siguiente_objetivo, posiciones_actores, POS_JUGADOR)
from vista_pygame.render.render_sala import calcular_layout_minimapa, dibujar_minimapa, dibujar_sala
from vista_pygame.render.animaciones import ColaAnimaciones
from vista_pygame.render.panel_mazmorra import PanelMazmorra
from vista_pygame.render.transiciones_cripta import TransicionSala,EfectoTrampa
from vista_pygame.render.entrada_cripta import EntradaCripta
from vista_pygame.render.boton_cerrar import dibujar_cerrar
from vista_pygame.render.panel_inventario import PanelInventario
from vista_pygame.render.panel_equipo import PanelEquipo
from vista_pygame.render.heroe_equipo import clave_equipo
from vista_pygame.render.iluminacion_sala import IluminacionSala
from vista_pygame.render.interaccion_candado import InteraccionCandado, rect_candado
from vista_pygame.render.reja_animada import dibujar_rejas
from vista_pygame.render.recogida_objeto import RecogidaObjeto
from vista_pygame.render.estado_animado import preparar_vidas,aplicar_impactos
from vista_pygame.render.escenografia_sala import posiciones_objetos
from vista_pygame.render.render_sala import presentacion_objeto

HUD_RECT = pygame.Rect(ANCHO_LOGICO - ANCHO_PANEL_HUD, 0, ANCHO_PANEL_HUD, ALTO_LOGICO)
MINIMAPA_RECT = pygame.Rect(ANCHO_LOGICO - ANCHO_PANEL_HUD + 16, 16,
                            ANCHO_PANEL_HUD - 32, 100)
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
        cinematica=bool(getattr(self.contexto,'entrada_cinematica',False)) and datos is not None
        id_entrada=datos[0] if cinematica else ''
        buscar_nombre=getattr(self.contexto.controlador,'nombre_cripta',lambda id:id)
        self._entrada=EntradaCripta(getattr(self.contexto,'fondo_entrada',None),id_entrada,
                                   buscar_nombre(id_entrada)) if cinematica else None
        self._inicio_pendiente=datos if cinematica else None
        self._arranque_solicitado=False
        if cinematica:self.contexto.entrada_cinematica=False
        self._transicion=TransicionSala()
        self._efecto_trampa=EfectoTrampa()
        self._recogida=None
        self._comando_diferido=None
        self._eventos_diferidos=[]
        self._comando_enviado=False
        self._tiempo_ambiente=0
        self._puerta_direccion=None
        self._puerta_cerrando=False
        self._puerta_ms=700
        if datos is not None and not cinematica:
            id_cripta, nombre_jugador, semilla = datos
            self.contexto.controlador.iniciar_partida(id_cripta, nombre_jugador, semilla)
        self._paneles=PanelMazmorra()
        self._inventario=PanelInventario()
        self._equipo=PanelEquipo()
        self._scroll_info=0
        self._max_scroll_info=0
        self._rect_info=pygame.Rect(974,405,292,110)
        self._iluminacion=IluminacionSala()
        self._candado=None
        self._indicadores=pygame.Surface((1280,720),pygame.SRCALPHA)
        self._objetivo_indice = None
        self._mostrar_ayuda = False
        self._cerrar_ayuda=pygame.Rect(1195,28,38,38)
        self._mostrar_minimapa = True
        self._layout_minimapa = None
        self._animaciones = ColaAnimaciones()
        self._estado_visual = None if cinematica else self.contexto.controlador.estado()
        self._ultimo_tiempo = self._estado_visual.tiempo if self._estado_visual else None
        self._sala_observada_id = self._estado_visual.sala_id if self._estado_visual else None
        self._sala_regreso_id = None
        self._revision_sesion = getattr(self.contexto.controlador, 'revision_sesion', lambda: None)()
        self._ocultar_jugador = False
        self._fin_enviado = False
        self._error_mostrado = None

    def al_salir(self):
        self._layout_minimapa = None
        self._animaciones.limpiar()

    # -- entrada -----------------------------------------------------

    @property
    def bloqueada(self):
        return (self._entrada is not None or self._transicion.activa or self._efecto_trampa.activa
                or self._puerta_ms<700 or self._comando_enviado or self._recogida is not None
                or self._animaciones.ocupada or self._candado is not None)

    def manejar_evento(self, evento):
        if self._candado is not None:
            self._candado.manejar_evento(evento,self.contexto.controlador.estado())
            if self._candado.terminada:self._candado=None
            return
        if (self._entrada is not None and self._error_mostrado is not None
                and evento.type==pygame.KEYDOWN and evento.key==pygame.K_ESCAPE):
            from vista_pygame.config_vista import ESCENA_MENU
            self.contexto.cambiar_escena(ESCENA_MENU)
            return
        if self.bloqueada or getattr(evento,'repeat',False):return
        estado = self.contexto.controlador.estado()
        if self._fin_enviado or (estado is not None and estado.estado in ('victoria','derrota')):
            return
        if self._error_mostrado is not None:
            return   # con un error de fondo no se aceptan más acciones
        if (estado is not None and self._estado_visual is not None
                and estado.sala_id!=self._estado_visual.sala_id):return
        if self._mostrar_ayuda:
            if ((evento.type==pygame.KEYDOWN and evento.key==pygame.K_F1) or
                (evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1 and self._cerrar_ayuda.collidepoint(evento.pos))):
                self._mostrar_ayuda=False
            return
        if self.contexto.controlador.esperando_red():return
        if evento.type==pygame.MOUSEWHEEL and self._rect_info.collidepoint(getattr(evento,'pos',(-1,-1))):
            self._scroll_info=max(0,min(self._max_scroll_info,self._scroll_info-evento.y*25))
            return
        capturado, comando = self._inventario.manejar_evento(evento, estado)
        if capturado:
            self.contexto.objeto_inventario_seleccionado = self._inventario.seleccion
            if comando is not None:
                self._comando_enviado = True
                self.contexto.controlador.enviar_comando(comando)
            return
        if estado is not None and evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1:
            from vista_pygame.render.render_sala import SALA_RECT
            for salida in estado.salidas:
                if salida.cerrada and rect_candado(salida.direccion,SALA_RECT).collidepoint(evento.pos):
                    self._candado=InteraccionCandado(salida)
                    return
        accion = accion_para_evento(evento)
        if accion is None:
            return
        categoria, valor = accion
        controlador = self.contexto.controlador

        if categoria == "comando":
            if self._animaciones.ocupada or controlador.esperando_red():
                return
            texto = valor
            if valor == "A":
                texto = f"A {self._objetivo_indice}" if self._objetivo_indice else "A"
            if texto=='R' and estado is not None and estado.objetos_suelo:
                indice,objeto,punto=posiciones_objetos(estado.objetos_suelo,estado.sala_id)[0]
                sprite,_,punto=presentacion_objeto(self.contexto.assets,indice,objeto,punto)
                self._recogida=RecogidaObjeto(estado.jugador.instancia_id,objeto,punto,
                                             POS_JUGADOR,sprite,self._animaciones)
                return
            if texto in ('EQ','U','T') and estado is not None and estado.inventario:
                elegido=getattr(self.contexto,'objeto_inventario_seleccionado',None)
                indice=next((i for i,o in enumerate(estado.inventario) if o.instancia_id==elegido),None)
                if indice is None and texto=='EQ':
                    indice=next((i for i,o in enumerate(estado.inventario) if o.clase in ('arma','armadura') and not o.equipado),None)
                if indice is None and texto=='U':
                    indice=next((i for i,o in enumerate(estado.inventario) if o.clase in ('pocion','antidoto','pocion_velocidad')),None)
                texto=f'{texto} {(indice if indice is not None else 0)+1}'
            if texto in ('N','S','E','O') and estado is not None:
                salida=next((x for x in estado.salidas if x.direccion==texto),None)
                if salida is not None and not salida.cerrada:
                    self._transicion.salir(self._captura_sala())
                    self._comando_diferido=texto
                    return
            self._comando_enviado=True
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
            from vista_pygame.config_vista import ESCENA_INVENTARIO
            if valor == ESCENA_INVENTARIO:
                self._inventario.abierto = not self._inventario.abierto
            else:self.contexto.cambiar_escena(valor)

    # -- actualización -------------------------------------------------

    def _captura_sala(self):
        imagen=pygame.Surface((ANCHO_LOGICO,ALTO_LOGICO))
        self._dibujar_contenido(imagen)
        return imagen

    def actualizar(self, dt_ms):
        controlador = self.contexto.controlador
        if self._entrada is None and not controlador.esperando_red():
            foto_regreso = controlador.estado()
            revision = getattr(controlador, 'revision_sesion', lambda: None)()
            if revision != self._revision_sesion:
                self._sala_regreso_id = None
                self._sala_observada_id = foto_regreso.sala_id if foto_regreso is not None else None
                self._revision_sesion = revision
            self._observar_regreso(foto_regreso)
        self._tiempo_ambiente+=max(0,dt_ms)
        foto_luz=self._estado_visual or controlador.estado()
        self._iluminacion.actualizar(dt_ms, bool(foto_luz is not None and clave_equipo(foto_luz)&2))
        self._puerta_ms=min(700,self._puerta_ms+max(0,dt_ms))
        if self._puerta_ms>=700:self._puerta_direccion=None
        if self._candado is not None:
            candado=self._candado
            candado.actualizar(dt_ms)
            if candado.solicita_comando:
                candado.enviado=True;candado.fase='espera';self._comando_enviado=True
                controlador.enviar_comando(f'AB {candado.direccion}')
                return
            if candado.fase=='espera' and not controlador.esperando_red():
                foto=controlador.estado()
                salida=next((s for s in foto.salidas if s.direccion==candado.direccion),None) if foto else None
                candado.confirmar(salida is not None and not salida.cerrada)
                self._comando_enviado=False
            if not candado.terminada:return
            self._candado=None
        if self._recogida is not None:
            r=self._recogida
            r.actualizar(dt_ms)
            if r.solicita_comando:
                r.enviado=True;self._comando_enviado=True
                controlador.enviar_comando('R 1')
                return
            if r.enviado and not r.confirmado and not controlador.esperando_red():
                foto=controlador.estado()
                exito=(foto is not None and foto.sala_id==self._estado_visual.sala_id and
                       not any(o.instancia_id==r.objeto_id for o in foto.objetos_suelo))
                r.confirmar(exito)
            self._error_mostrado=controlador.error_pendiente()
            if r.activa:return
            self._recogida=None
        if self._entrada is not None:
            self._entrada.actualizar(dt_ms)
            if self._entrada.terminada:
                if not self._arranque_solicitado:
                    self._arranque_solicitado=True
                    self.contexto.arrancar_partida(self._inicio_pendiente)
                elif not self.contexto.iniciando():
                    self._error_mostrado=(getattr(self.contexto,'error_inicio',None) or controlador.error_pendiente())
                    foto=controlador.estado()
                    if self._error_mostrado is None and foto is not None:
                        self._estado_visual=foto;self._ultimo_tiempo=foto.tiempo
                        self._entrada=None;self._transicion.entrar(foto)
                        self._eventos_diferidos.extend(controlador.eventos_nuevos())
                        self._estado_visual=preparar_vidas(self._estado_visual,self._eventos_diferidos)
            return
        if self._transicion.activa:
            self._transicion.actualizar(dt_ms)
            if self._transicion.fase=='espera':
                if self._comando_diferido is not None:
                    comando=self._comando_diferido;self._comando_diferido=None
                    self._comando_enviado=True;controlador.enviar_comando(comando)
                    return
                foto=controlador.estado()
                if foto is not None and not controlador.esperando_red():
                    self._estado_visual=foto;self._ultimo_tiempo=foto.tiempo
                    self._animaciones.limpiar();self._objetivo_indice=None
                    self._eventos_diferidos.extend(controlador.eventos_nuevos())
                    self._estado_visual=preparar_vidas(self._estado_visual,self._eventos_diferidos)
                    self._transicion.entrar(foto)
            if self._transicion.activa:return
        foto=controlador.estado()
        if (foto is not None and foto.estado=='en_curso' and self._estado_visual is not None
                and foto.sala_id!=self._estado_visual.sala_id):
            self._transicion.salir(self._captura_sala())
            return
        if not controlador.esperando_red():self._comando_enviado=False
        if foto is not None and self._estado_visual is not None:
            for anterior in self._estado_visual.salidas:
                nueva=next((x for x in foto.salidas if x.direccion==anterior.direccion),None)
                if nueva is not None and anterior.cerrada != nueva.cerrada:
                    self._puerta_direccion=nueva.direccion;self._puerta_ms=0
                    self._puerta_cerrando=nueva.cerrada
                    # La puerta se actualiza una vez; las vidas siguen su propia
                    # secuencia. Evita reiniciar la reja mientras hay ataques.
                    self._estado_visual=replace(self._estado_visual,salidas=foto.salidas)
                    break
        self._error_mostrado = controlador.error_pendiente()

        if self._layout_minimapa is None and controlador.topologia_cripta():
            self._layout_minimapa = calcular_layout_minimapa(
                controlador.topologia_cripta(), controlador.sala_inicial_id())

        estado = controlador.estado()
        if (estado is not None and self._ultimo_tiempo is not None
                and estado.tiempo < self._ultimo_tiempo):
            self._animaciones.limpiar()
            self._estado_visual = estado
        if estado is not None:
            self._ultimo_tiempo = estado.tiempo
        if self._estado_visual is None:
            self._estado_visual = estado
        if self._estado_visual is not None:
            self._animaciones.preparar(posiciones_actores(self._estado_visual))
        eventos = self._eventos_diferidos+controlador.eventos_nuevos()
        self._eventos_diferidos=[]
        if eventos:
            if any(getattr(e, 'tipo', None) == 'mensaje' and
                   getattr(e, 'texto', '').startswith(('Partida cargada:', 'Lees el pergamino:'))
                   for e in eventos):
                self._animaciones.limpiar()
                self._estado_visual = estado
                self._layout_minimapa = None
                self._sala_regreso_id = None
                self._sala_observada_id = estado.sala_id if estado is not None else None
                if estado is not None:
                    self._animaciones.preparar(posiciones_actores(estado))
            if not self._animaciones.ocupada:
                self._estado_visual=preparar_vidas(self._estado_visual,eventos)
            hay_trampa=any(getattr(e,'tipo',None)=='trampa' for e in eventos)
            for evento in eventos:
                texto=getattr(evento,'texto','')
                if getattr(evento,'tipo',None)=='trampa':
                    self._efecto_trampa.iniciar('¡Una trampa se activa! '+evento.nombre,evento,self._estado_visual)
                elif not hay_trampa and texto.startswith('¡Una trampa se activa!'):
                    self._efecto_trampa.iniciar(texto,estado=self._estado_visual)
            self._animaciones.agregar_desde_eventos(eventos)
            for evento in eventos:
                tipo = getattr(evento, "tipo", None)
                if tipo in ("ataque", "movimiento", "mensaje"):
                    self.contexto.audio.reproducir_sfx(tipo)
        # La trampa se ve antes de los ataques que ocurrieron después en el reloj.
        if self._efecto_trampa.activa:
            self._efecto_trampa.actualizar(dt_ms)
            self._estado_visual=aplicar_impactos(self._estado_visual,self._efecto_trampa.extraer_impactos())
        elif self._puerta_ms>=700:
            self._animaciones.actualizar(dt_ms)
            self._estado_visual=aplicar_impactos(self._estado_visual,self._animaciones.extraer_impactos())
        if not self._animaciones.ocupada and not self._efecto_trampa.activa:
            self._estado_visual = estado

        estado = controlador.estado()
        if (not self._fin_enviado and estado is not None
                and estado.estado in ("victoria", "derrota") and not self._animaciones.ocupada
                and not self._efecto_trampa.activa):
            resumen = controlador.resumen_fin()
            if resumen is not None:
                self._capturar_fin(estado)
                self._fin_enviado = True
                self.contexto.cambiar_escena(ESCENA_FIN_PARTIDA, resumen)

    def _capturar_fin(self, estado):
        self.contexto.fondo_fin = None
        self.contexto.jugador_fin = None
        self.contexto.equipo_fin=clave_equipo(estado)
        self.contexto.nombre_cripta_actual=getattr(estado,'cripta_nombre','')
        if estado.estado=='victoria':
            fondo=pygame.Surface((ANCHO_LOGICO,ALTO_LOGICO))
            self._dibujar_contenido(fondo)
            self.contexto.fondo_fin=fondo
            return
        if estado.estado != 'derrota':
            return
        fondo = pygame.Surface((ANCHO_LOGICO, ALTO_LOGICO))
        self._ocultar_jugador = True
        try:
            self.dibujar(fondo)
        finally:
            self._ocultar_jugador = False
        self.contexto.equipo_fin=clave_equipo(estado)
        if hasattr(self.contexto.assets,'fotograma_jugador_equipado'):
            sprite,_=self.contexto.assets.fotograma_jugador_equipado('reposo',0,self.contexto.equipo_fin)
        else:sprite = self.contexto.assets.sprite_jugador('parado','S')
        self.contexto.fondo_fin = fondo
        self.contexto.jugador_fin = (sprite, POS_JUGADOR)

    # -- dibujo ----------------------------------------------------------

    def _observar_regreso(self, estado):
        """Referencia visual del último cruce; no supone direcciones opuestas."""
        if estado is None:
            return
        retroceso = self._ultimo_tiempo is not None and estado.tiempo < self._ultimo_tiempo
        if retroceso:
            self._sala_regreso_id = None
        elif self._sala_observada_id is not None and estado.sala_id != self._sala_observada_id:
            self._sala_regreso_id = self._sala_observada_id
        self._sala_observada_id = estado.sala_id

    def _texto_regreso(self, estado):
        origen = self._sala_regreso_id
        if origen is None or origen == estado.sala_id:
            return None
        salida = next((s for s in estado.salidas if s.sala_destino_id == origen), None)
        if salida is None:
            return f'Volver a sala {origen}: no hay salida directa.'
        nombres = (('N', 'Norte'), ('S', 'Sur'), ('E', 'Este'), ('O', 'Oeste'))
        direccion = next((nombre for clave, nombre in nombres if clave == salida.direccion), salida.direccion)
        situacion = 'cerrada: abrir primero' if salida.cerrada else 'abierta'
        return f'Volver a sala {origen}: {salida.direccion} ({direccion}) · {situacion}'

    def _dibujar_regreso(self, pantalla, assets, estado):
        texto = self._texto_regreso(estado)
        if texto is not None:
            from vista_pygame.render.render_sala import SALA_RECT
            salida = next((s for s in estado.salidas if s.sala_destino_id == self._sala_regreso_id), None)
            if salida is not None:
                # Flecha de píxeles: la fuente del juego no incluye estos glifos.
                dx,dy=next((x,y) for d,x,y in (('N',0,-1),('S',0,1),('E',1,0),('O',-1,0)) if d==salida.direccion)
                cx,cy=SALA_RECT.x+23,SALA_RECT.bottom+11
                punta=(cx+dx*6,cy+dy*6)
                pygame.draw.line(pantalla,COLOR_ORO,(cx-dx*5,cy-dy*5),punta,2)
                pygame.draw.lines(pantalla,COLOR_ORO,False,
                                  [(punta[0]-dx*4-dy*3,punta[1]-dy*4+dx*3),punta,
                                   (punta[0]-dx*4+dy*3,punta[1]-dy*4-dx*3)],2)
            PanelEquipo.texto(pantalla, assets, texto, (SALA_RECT.x+38, SALA_RECT.bottom+2),
                              15, COLOR_ORO, ancho=SALA_RECT.w-54)

    def dibujar(self,pantalla):
        if self._entrada is not None:
            self._entrada.dibujar(pantalla,self.contexto.assets,self._error_mostrado)
            return
        self._dibujar_contenido(pantalla)
        self._efecto_trampa.dibujar(pantalla,self.contexto.assets)
        if self._candado is not None:
            self._candado.dibujar(pantalla,self.contexto.assets,self.contexto.controlador.estado())
        self._transicion.dibujar(pantalla,self.contexto.assets)

    def _dibujar_contenido(self, pantalla):
        pantalla.fill(COLOR_FONDO)
        assets = self.contexto.assets
        controlador = self.contexto.controlador
        estado = self._estado_visual or controlador.estado()

        if estado is None:
            texto = assets.fuente(26).render("Entrando a la cripta...", True, COLOR_TEXTO)
            pantalla.blit(texto, texto.get_rect(center=(ANCHO_LOGICO // 2, ALTO_LOGICO // 2)))
            return

        oculto=self._recogida.objeto_id if self._recogida is not None and self._recogida.exito else None
        dibujar_sala(pantalla, assets, estado, self._tiempo_ambiente,
                     (self._puerta_direccion,1-self._puerta_ms/700 if self._puerta_cerrando else self._puerta_ms/700),oculto)
        actores = self._estado_visual or estado
        animacion_jugador=self._recogida or self._animaciones
        self._indicadores.fill((0,0,0,0))
        if not self._ocultar_jugador:
            dibujar_jugador(pantalla, assets, actores, controlador.nombre_jugador or "Jugador", animacion_jugador, pantalla_ui=self._indicadores)
        dibujar_enemigos(pantalla, assets, actores, self._objetivo_indice, self._animaciones,pantalla_ui=self._indicadores)
        if self._recogida is not None:self._recogida.dibujar_objeto(pantalla)

        luz_x,luz_y=POS_JUGADOR[0]+65,POS_JUGADOR[1]+12
        if animacion_jugador is not None:
            dx,dy,_=animacion_jugador.pose(estado.jugador.instancia_id)
            luz_x+=dx;luz_y+=dy
        luces_suelo=[p for _,o,p in posiciones_objetos(estado.objetos_suelo,estado.sala_id)
                     if o.clase=='antorcha' and o.encendida]
        from vista_pygame.render.render_sala import SALA_RECT
        if not getattr(estado,'es_sala_salida',False):
            self._iluminacion.dibujar(pantalla,SALA_RECT,(luz_x,luz_y),luces_suelo)
            # Reja y candado se presentan juntos, con contraste suficiente;
            # nunca queda un candado brillante flotando sobre un arco vacío.
            progreso=1-self._puerta_ms/700 if self._puerta_cerrando else self._puerta_ms/700
            dibujar_rejas(pantalla,SALA_RECT,estado.salidas,(self._puerta_direccion,progreso),solo_existentes=True)
        pantalla.blit(self._indicadores,(0,0))
        self._animaciones.dibujar(pantalla)
        self._dibujar_hud(pantalla, assets, estado)
        self._dibujar_regreso(pantalla, assets, estado)
        self._dibujar_mensajes(pantalla, assets, controlador)
        if self._mostrar_minimapa and self._layout_minimapa:
            dibujar_minimapa(pantalla, MINIMAPA_RECT, self._layout_minimapa,
                             estado.salas_visitadas, estado.sala_id, assets.fuente(14))
        if self._mostrar_ayuda:
            self._dibujar_ayuda(pantalla, assets)
        if self._error_mostrado is not None:
            self._dibujar_error(pantalla, assets)

    def _dibujar_hud(self, pantalla, assets, estado):
        self._paneles.dibujar(pantalla,HUD_RECT)
        x=HUD_RECT.x+16
        fuente=assets.fuente(15)
        pantalla.blit(fuente.render(f't = {estado.tiempo}',False,COLOR_TEXTO_TENUE),(x,130))
        pantalla.blit(fuente.render(f'Vida {estado.jugador.vida}/{estado.jugador.vida_max}',False,COLOR_TEXTO),(x,152))
        PanelEquipo.barra(pantalla,pygame.Rect(x,174,ANCHO_PANEL_HUD-32,10),
                          estado.jugador.vida,estado.jugador.vida_max,COLOR_VIDA)
        PanelEquipo.texto(pantalla,assets,
                          f'Ataque {estado.ataque}  Defensa {estado.defensa}  Vel {estado.velocidad}',
                          (x,193),13,ancho=286)
        self._equipo.dibujar(pantalla,assets,estado)
        self._dibujar_detalles_hud(pantalla,assets,estado)
        self._inventario.dibujar(pantalla,assets,estado,
                                  self.bloqueada or self.contexto.controlador.esperando_red())

    def _dibujar_detalles_hud(self,pantalla,assets,estado):
        lineas=[('Efectos:',COLOR_ORO)]
        lineas.extend((efecto,COLOR_VENENO) for efecto in estado.efectos)
        if not estado.efectos:lineas.append(('ninguno',COLOR_TEXTO_TENUE))
        lineas.append(('Salidas:',COLOR_ORO))
        for salida in estado.salidas:
            situacion=('con llave' if salida.tiene_llave else 'cerrada') if salida.cerrada else 'abierta'
            color=COLOR_TEXTO if not salida.cerrada or salida.tiene_llave else COLOR_PELIGRO
            lineas.append((f'{salida.direccion} {salida.nombre_destino} ({situacion})',color))
        if self._objetivo_indice and self._objetivo_indice<=len(estado.enemigos_activos):
            lineas.append((f'Objetivo: {estado.enemigos_activos[self._objetivo_indice-1].instancia_id}',COLOR_ORO))
        if estado.proximos_turnos:
            lineas.append(('Próximos turnos:',COLOR_ORO))
            lineas.extend((f't={turno.tiempo}  {turno.etiqueta}',COLOR_TEXTO_TENUE)
                          for turno in estado.proximos_turnos[:CANTIDAD_PROXIMOS_TURNOS])
        self._max_scroll_info=max(0,len(lineas)*19-self._rect_info.h)
        self._scroll_info=min(self._scroll_info,self._max_scroll_info)
        clip=pantalla.get_clip();pantalla.set_clip(self._rect_info)
        try:
            for i,(texto,color) in enumerate(lineas):
                PanelEquipo.texto(pantalla,assets,texto,
                                  (self._rect_info.x+2,self._rect_info.y+i*19-self._scroll_info),
                                  13,color,ancho=self._rect_info.w-4)
        finally:pantalla.set_clip(clip)
        if self._max_scroll_info:
            PanelEquipo.texto(pantalla,assets,'Rueda aquí: efectos, salidas y turnos',
                              (self._rect_info.x+2,520),10,COLOR_TEXTO_TENUE,ancho=286)

    def _dibujar_mensajes(self, pantalla, assets, controlador):
        self._paneles.dibujar(pantalla,MENSAJES_RECT)
        fuente = assets.fuente(14)
        mensajes = controlador.mensajes()[-8:]   # las últimas caben en el panel visible
        y = MENSAJES_RECT.y + 6
        for mensaje in mensajes:
            texto=str(mensaje)
            while fuente.size(texto)[0]>MENSAJES_RECT.width-16 and len(texto)>1:
                texto=texto[:-2]+'…'
            pantalla.blit(fuente.render(texto, True, COLOR_TEXTO), (MENSAJES_RECT.x + 8, y))
            y += 18

    def _dibujar_ayuda(self, pantalla, assets):
        overlay = pygame.Surface((ANCHO_LOGICO, ALTO_LOGICO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        pantalla.blit(overlay, (0, 0))
        dibujar_cerrar(pantalla,self._cerrar_ayuda)
        fuente = assets.fuente(16)
        y = 40
        for linea in AYUDA.split("\n"):
            pantalla.blit(fuente.render(linea, True, COLOR_TEXTO), (80, y))
            y += 22
        pantalla.blit(assets.fuente(16).render("X roja o F1: cerrar esta ayuda", True, COLOR_AVISO),
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
