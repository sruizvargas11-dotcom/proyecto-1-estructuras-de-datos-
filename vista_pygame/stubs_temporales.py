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
from vista_pygame.render.boton_cerrar import dibujar_cerrar

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

from vista_pygame.render.panel_mazmorra import PanelMazmorra
_PANEL_PIEDRA=PanelMazmorra()

def _panel(pantalla, rect, titulo, fuente):
    _PANEL_PIEDRA.dibujar(pantalla, rect)
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
        _panel(pantalla, pygame.Rect(360, 120, 560, 420), "CRIPTA", self._fuente)
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
        self._fuente=self.contexto.assets.fuente(20)
        self._cerrar=pygame.Rect(970,112,34,34)
        self._seleccion=0;self._saliendo=False
        estado=self.contexto.controlador.estado()
        elegido=getattr(self.contexto,'objeto_inventario_seleccionado',None)
        if estado is not None:
            self._seleccion=next((i for i,o in enumerate(estado.inventario) if o.instancia_id==elegido),0)

    def manejar_evento(self,evento):
        if self._saliendo:return
        if ((evento.type==pygame.KEYDOWN and evento.key==pygame.K_ESCAPE) or
            (evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1 and self._cerrar.collidepoint(evento.pos))):
            self._saliendo=True;self.contexto.cambiar_escena(ESCENA_PARTIDA);return
        estado=self.contexto.controlador.estado()
        if estado is None or not estado.inventario:return
        cantidad=len(estado.inventario)
        if evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1:
            for i in range(cantidad):
                if pygame.Rect(282,158+i*34,716,32).collidepoint(evento.pos):self._seleccion=i
        elif evento.type==pygame.KEYDOWN:
            if evento.key in (pygame.K_UP,pygame.K_DOWN):
                self._seleccion=(self._seleccion+(-1 if evento.key==pygame.K_UP else 1))%cantidad
            comando=next((c for k,c in ((pygame.K_c,'EQ'),(pygame.K_u,'U'),(pygame.K_t,'T'),(pygame.K_f,'T')) if k==evento.key),None)
            if evento.key==pygame.K_RETURN:
                comando='EQ' if estado.inventario[self._seleccion].clase in ('arma','armadura') else 'U'
            if comando:
                self.contexto.objeto_inventario_seleccionado=estado.inventario[self._seleccion].instancia_id
                self._saliendo=True
                self.contexto.controlador.enviar_comando(f'{comando} {self._seleccion+1}')
                self.contexto.cambiar_escena(ESCENA_PARTIDA)
                return
        self.contexto.objeto_inventario_seleccionado=estado.inventario[self._seleccion].instancia_id

    def actualizar(self,dt_ms):pass

    def dibujar(self,pantalla):
        pantalla.fill(COLOR_FONDO)
        _panel(pantalla,pygame.Rect(260,100,760,500),'Inventario',self._fuente)
        dibujar_cerrar(pantalla,self._cerrar)
        estado=self.contexto.controlador.estado()
        if estado:
            for i,objeto in enumerate(estado.inventario):
                r=pygame.Rect(282,158+i*34,716,32)
                if i==self._seleccion:
                    pygame.draw.rect(pantalla,(59,53,37),r)
                    pygame.draw.rect(pantalla,COLOR_ORO,r,1)
                marca=' [equipado]' if objeto.equipado else ''
                texto=f'{i+1}. {objeto.nombre}{marca}'
                pantalla.blit(self._fuente.render(texto,False,COLOR_TEXTO),(300,r.y+5))
            if not estado.inventario:
                pantalla.blit(self._fuente.render('El inventario está vacío.',False,COLOR_TEXTO_TENUE),(300,174))
        fuente=self.contexto.assets.fuente(17)
        for i,linea in enumerate(('Flechas o clic: elegir   C: equipar   U: usar   T: soltar',
                                  'X roja o Esc: volver sin gastar turno')):
            pantalla.blit(fuente.render(linea,False,COLOR_TEXTO_TENUE),(282,535+i*29))


class EscenaPausaTemporal(EscenaBase):
    def al_entrar(self, datos=None):
        self._fuente=self.contexto.assets.fuente(22)
        self._cerrar=pygame.Rect(812,175,30,30)
        self._botones=tuple(pygame.Rect(450,235+i*67,380,50) for i in range(4))
        self._seleccion=0;self._pendiente=False;self._saliendo=False;self._mensaje=''
        app=getattr(self.contexto,'_app',None)
        lienzo=getattr(app,'_lienzo',None)
        self._fondo=lienzo.copy() if lienzo is not None else pygame.Surface((1280,720))

    def _activar(self, opcion):
        if self._pendiente or self._saliendo:return
        c=self.contexto.controlador
        if opcion==0:
            self._saliendo=True;self.contexto.cambiar_escena(ESCENA_PARTIDA)
        elif opcion in (1,2):
            self._pendiente=True
            self._mensaje='Guardando…' if opcion==1 else 'Cargando…'
            if opcion==1:c.guardar()
            else:c.cargar()
        else:
            self._saliendo=True;c.salir();self.contexto.cambiar_escena(ESCENA_MENU)

    def manejar_evento(self, evento):
        if self._pendiente or self._saliendo or getattr(evento,'repeat',False):return
        if evento.type==pygame.MOUSEMOTION:
            for i,r in enumerate(self._botones):
                if r.collidepoint(evento.pos):self._seleccion=i;break
        elif evento.type==pygame.MOUSEBUTTONDOWN and evento.button==1:
            if self._cerrar.collidepoint(evento.pos):self._activar(0);return
            for i,r in enumerate(self._botones):
                if r.collidepoint(evento.pos):self._seleccion=i;self._activar(i);return
        elif evento.type==pygame.KEYDOWN:
            if evento.key==pygame.K_UP:self._seleccion=(self._seleccion-1)%4
            elif evento.key==pygame.K_DOWN:self._seleccion=(self._seleccion+1)%4
            elif evento.key in (pygame.K_RETURN,pygame.K_KP_ENTER):self._activar(self._seleccion)
            else:
                for tecla,opcion in ((pygame.K_ESCAPE,0),(pygame.K_g,1),(pygame.K_l,2),(pygame.K_q,3)):
                    if evento.key==tecla:self._activar(opcion);return

    def actualizar(self, dt_ms):
        if self._pendiente and not self.contexto.controlador.esperando_red():
            self._pendiente=False
            mensajes=self.contexto.controlador.mensajes()
            error=self.contexto.controlador.error_pendiente()
            self._mensaje=('Error: '+error.strip().splitlines()[-1]) if error else (mensajes[-1] if mensajes else 'Operación terminada.')

    def dibujar(self, pantalla):
        pantalla.blit(self._fondo,(0,0))
        velo=pygame.Surface((1280,720),pygame.SRCALPHA);velo.fill((4,8,15,180));pantalla.blit(velo,(0,0))
        _panel(pantalla,pygame.Rect(420,160,440,415),'',self._fuente)
        titulo=self.contexto.assets.fuente(34).render('PAUSA',False,COLOR_ORO)
        pantalla.blit(titulo,titulo.get_rect(center=(640,194)))
        dibujar_cerrar(pantalla,self._cerrar)
        for i,(rect,texto) in enumerate(zip(self._botones,('Continuar  [Esc]','Guardar partida  [G]',
                                                       'Cargar partida  [L]','Volver al menú  [Q]'))):
            _PANEL_PIEDRA.dibujar(pantalla,rect,self._seleccion==i and not self._pendiente)
            im=self._fuente.render(texto,False,COLOR_TEXTO_TENUE if self._pendiente else COLOR_TEXTO)
            pantalla.blit(im,im.get_rect(center=rect.center))
        texto=self._mensaje
        while self.contexto.assets.fuente(14).size(texto)[0]>394 and len(texto)>1:texto=texto[:-2]+'…'
        im=self.contexto.assets.fuente(14).render(texto,False,COLOR_TEXTO_TENUE)
        pantalla.blit(im,im.get_rect(center=(640,538)))


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
        _panel(pantalla, pygame.Rect(360, 140, 560, 420), "Fin de la partida",
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
