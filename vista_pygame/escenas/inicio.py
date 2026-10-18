"""Inicio, nueva expedición y selector de guardados sobre la misma portada."""
import threading
from datetime import datetime
import pygame
from vista_pygame.escenas.menu_criptas import EscenaMenuCriptas
from vista_pygame.config_vista import COLOR_FONDO, COLOR_TEXTO, COLOR_TEXTO_TENUE, COLOR_ORO, COLOR_PELIGRO, ESCENA_PARTIDA
from vista_pygame.render.boton_cerrar import dibujar_cerrar


class EscenaInicio(EscenaMenuCriptas):
    def al_entrar(self,datos=None):
        super().al_entrar(datos)
        self._pagina='inicio'
        self._eleccion_inicio=0
        self._guardados=[]
        self._indice_guardado=0
        self._primero_guardado=0
        self._leyendo_guardados=False
        self._cargando_partida=False
        self._carga_completada=False
        self._aviso_guardados=None
        self._generacion_menu=getattr(self,'_generacion_menu',0)+1

    def _rect_inicio(self,indice):
        w,h=self._tamano_layout
        ancho,alto=(300,48) if indice==2 else (430,62)
        rect=pygame.Rect(0,0,min(w-56,round(ancho*self._escala_texto)),round(alto*self._escala_texto))
        rect.center=(self._layout.centro_x,round(h*(.30+indice*.13)))
        return rect

    def _rect_volver(self):
        s=self._escala_texto
        return pygame.Rect(round(24*s),round(22*s),round(160*s),round(40*s))

    def _rect_refrescar(self):
        w,h=self._tamano_layout;s=self._escala_texto
        return pygame.Rect(w-round(190*s),round(22*s),round(164*s),round(40*s))

    def _rect_guardado(self,fila):
        w,h=self._tamano_layout;s=self._escala_texto
        r=pygame.Rect(0,round(h*.22+fila*82*s),min(w-60,round(660*s)),round(70*s))
        r.centerx=self._layout.centro_x
        return r

    def _abrir_guardados(self):
        self._pagina='cargar';self._leyendo_guardados=True;self._aviso_guardados=None
        generacion=self._generacion_menu
        self._consulta_guardados=getattr(self,'_consulta_guardados',0)+1
        consulta=self._consulta_guardados
        def leer():
            try:filas=self.contexto.controlador.listar_partidas_guardadas();error=None
            except (OSError,ValueError,RuntimeError) as exc:filas=[];error=f'No se pudieron listar las partidas: {exc}'
            with self._lock:
                if generacion!=self._generacion_menu or consulta!=self._consulta_guardados:return
                self._guardados=filas;self._aviso_guardados=error;self._leyendo_guardados=False
                self._indice_guardado=0;self._primero_guardado=0
        threading.Thread(target=leer,name='cripta-lista-guardados',daemon=True).start()

    def _cargar_seleccion(self):
        if self._leyendo_guardados or self._cargando_partida or not self._guardados:return
        elegido=self._guardados[self._indice_guardado]
        if elegido.error:
            self._aviso_guardados=elegido.error
            return
        self._cargando_partida=True;self._carga_completada=False;self._aviso_guardados=None
        def cargar():
            try:
                # Esperar a que la consulta del menú deje libre la fuente.
                if self._hilo_carga is not None:self._hilo_carga.join()
                self.contexto.controlador.cargar_partida_guardada(elegido.ruta)
                error=None
            except Exception as exc:error=f'No se pudo cargar: {exc}'
            with self._lock:
                self._aviso_guardados=error;self._carga_completada=True
        hilo=threading.Thread(target=cargar,name='cripta-cargar-menu',daemon=False)
        self.contexto._hilo_inicio=hilo
        hilo.start()

    def _mover_guardado(self,paso):
        if not self._guardados:return
        self._indice_guardado=max(0,min(len(self._guardados)-1,self._indice_guardado+paso))
        self._primero_guardado=min(self._primero_guardado,self._indice_guardado)
        self._primero_guardado=max(self._primero_guardado,self._indice_guardado-3)

    def manejar_evento(self,evento):
        if self._cargando_partida:return
        if self._pagina=='nueva':
            volver=(evento.type==pygame.KEYDOWN and evento.key==pygame.K_ESCAPE)
            volver|=(evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1 and self._rect_volver().collidepoint(evento.pos))
            if volver:
                if not self._iniciando:self._pagina='inicio'
                return
            return super().manejar_evento(evento)
        if evento.type==pygame.KEYDOWN:
            if evento.key==pygame.K_ESCAPE:
                if self._pagina=='cargar':self._pagina='inicio'
                else:pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif self._pagina=='inicio':
                if evento.key in (pygame.K_UP,pygame.K_DOWN,pygame.K_TAB):
                    paso=-1 if evento.key==pygame.K_UP or (evento.key==pygame.K_TAB and getattr(evento,'mod',0)&pygame.KMOD_SHIFT) else 1
                    self._eleccion_inicio=(self._eleccion_inicio+paso)%3
                elif evento.key in (pygame.K_RETURN,pygame.K_SPACE):self._elegir_inicio()
            elif not self._leyendo_guardados:
                if evento.key in (pygame.K_UP,pygame.K_DOWN):self._mover_guardado(-1 if evento.key==pygame.K_UP else 1)
                elif evento.key in (pygame.K_PAGEUP,pygame.K_PAGEDOWN):self._mover_guardado(-4 if evento.key==pygame.K_PAGEUP else 4)
                elif evento.key in (pygame.K_RETURN,pygame.K_SPACE):self._cargar_seleccion()
                elif evento.key==pygame.K_r:self._abrir_guardados()
        elif evento.type==pygame.MOUSEWHEEL and self._pagina=='cargar' and not self._leyendo_guardados:
            self._mover_guardado(-evento.y)
        elif evento.type in (pygame.MOUSEMOTION,pygame.MOUSEBUTTONDOWN):
            clic=evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1
            if self._pagina=='inicio':
                for i in range(3):
                    if self._rect_inicio(i).collidepoint(evento.pos):
                        self._eleccion_inicio=i
                        if clic:self._elegir_inicio()
            else:
                if clic and self._rect_volver().collidepoint(evento.pos):self._pagina='inicio';return
                if clic and self._rect_refrescar().collidepoint(evento.pos):self._abrir_guardados();return
                if self._leyendo_guardados:return
                for fila in range(min(4,len(self._guardados)-self._primero_guardado)):
                    if self._rect_guardado(fila).collidepoint(evento.pos):
                        self._indice_guardado=self._primero_guardado+fila
                        if clic:self._cargar_seleccion()

    def _elegir_inicio(self):
        if self._eleccion_inicio==0:self._pagina='nueva'
        elif self._eleccion_inicio==1:self._abrir_guardados()
        else:pygame.event.post(pygame.event.Event(pygame.QUIT))

    def actualizar(self,dt_ms):
        super().actualizar(dt_ms)
        if self._cargando_partida and self._carga_completada:
            c=self.contexto.controlador
            if self._aviso_guardados:
                self._cargando_partida=False;self._carga_completada=False
            elif c.error_pendiente():
                self._aviso_guardados='No se pudo reanudar la partida.'
                self._cargando_partida=False
            elif c.estado() is not None:
                self.contexto.entrada_cinematica=False
                self.contexto.objeto_inventario_seleccionado=None
                self.contexto.cambiar_escena(ESCENA_PARTIDA,None)

    def _etiqueta(self,pantalla,texto,centro,tamano=24,color=COLOR_TEXTO,ancho=None):
        fuente=self._fuente(tamano)
        if ancho is not None:
            while fuente.size(texto)[0]>ancho and len(texto)>1:texto=texto[:-2]+'…'
        im=fuente.render(texto,False,color);sombra=fuente.render(texto,False,(4,8,14))
        r=im.get_rect(center=centro)
        pantalla.blit(sombra,r.move(2,2));pantalla.blit(im,r)

    def _boton(self,pantalla,rect,texto,seleccionado=False):
        self._paneles.dibujar(pantalla,rect,seleccionado)
        self._etiqueta(pantalla,texto,rect.center,22,COLOR_ORO if seleccionado else COLOR_TEXTO,rect.w-30)

    def dibujar(self,pantalla):
        self.establecer_tamano(pantalla.get_size())
        if self._pagina=='nueva':
            super().dibujar(pantalla)
            self._boton(pantalla,self._rect_volver(),'Volver',False)
            # El pie de esta pantalla vuelve al inicio, no sale de la aplicación.
            zona=pygame.Rect(0,self._tamano_layout[1]-38,self._tamano_layout[0],38)
            pygame.draw.rect(pantalla,(9,14,22),zona)
            self._etiqueta(pantalla,'Tab/Flechas elegir · Enter jugar · Esc volver · F11 pantalla completa',zona.center,16)
            return
        pantalla.fill(COLOR_FONDO)
        if self._portada_animada.disponible:self._portada_animada.dibujar(pantalla)
        elif self._fondo is not None:pantalla.blit(self._fondo,(self._layout.offset_x,self._layout.offset_y))
        w,h=self._tamano_layout;s=self._escala_texto
        titulo=pygame.Rect(0,round(h*.055),round(390*s),round(60*s));titulo.centerx=self._layout.centro_x
        self._paneles.dibujar(pantalla,titulo)
        self._etiqueta(pantalla,'CRIPTA' if self._pagina=='inicio' else 'Cargar partida',titulo.center,34,COLOR_ORO)
        if self._pagina=='inicio':
            self._etiqueta(pantalla,'Una nueva expedición te espera',(self._layout.centro_x,round(h*.20)),20)
            for i,nombre in enumerate(('Crear nueva partida','Cargar partida','Salir del juego')):
                self._boton(pantalla,self._rect_inicio(i),nombre,i==self._eleccion_inicio)
            self._etiqueta(pantalla,'Flechas o clic para elegir · Enter continuar · Esc salir',(w//2,h-round(24*s)),16)
            return
        self._boton(pantalla,self._rect_volver(),'Volver')
        self._boton(pantalla,self._rect_refrescar(),'Actualizar')
        if self._leyendo_guardados:
            self._etiqueta(pantalla,'Buscando partidas guardadas…',(w//2,round(h*.33)),22)
        elif not self._guardados:
            vacio=pygame.Rect(0,round(h*.25),min(w-60,round(620*s)),round(110*s));vacio.centerx=self._layout.centro_x
            self._paneles.dibujar(pantalla,vacio)
            self._etiqueta(pantalla,'Todavía no hay partidas guardadas.',vacio.center,22)
            self._etiqueta(pantalla,'Guarda durante el juego con G o desde la pausa.',(vacio.centerx,vacio.bottom+round(28*s)),17)
        else:
            for fila,guardado in enumerate(self._guardados[self._primero_guardado:self._primero_guardado+4]):
                r=self._rect_guardado(fila);seleccionado=self._indice_guardado==self._primero_guardado+fila
                self._paneles.dibujar(pantalla,r,seleccionado)
                nombre=guardado.archivo if guardado.error else f'{guardado.nombre_jugador} · {guardado.cripta_id}'
                color=COLOR_PELIGRO if guardado.error else COLOR_ORO if seleccionado else COLOR_TEXTO
                self._etiqueta(pantalla,nombre,(r.centerx,r.y+round(23*s)),22,color,r.w-30)
                detalle=(guardado.error if guardado.error else
                         'Guardada el '+datetime.fromtimestamp(guardado.modificada).strftime('%d/%m/%Y · %H:%M'))
                self._etiqueta(pantalla,detalle,(r.centerx,r.y+round(49*s)),16,COLOR_TEXTO_TENUE,r.w-30)
            self._etiqueta(pantalla,f'{self._indice_guardado+1} / {len(self._guardados)} · Clic o Enter para continuar',
                           (self._layout.centro_x,round(h*.73)),17)
        aviso='Cargando partida…' if self._cargando_partida else self._aviso_guardados
        if aviso:
            rect=pygame.Rect(round(w*.12),round(h*.80),round(w*.76),round(62*s))
            self._paneles.dibujar(pantalla,rect)
            self._etiqueta(pantalla,aviso,rect.center,17,COLOR_TEXTO if self._cargando_partida else COLOR_PELIGRO,rect.w-28)
        self._etiqueta(pantalla,'Rueda/Flechas: recorrer · R: actualizar · Esc: volver',(w//2,h-round(24*s)),16)
