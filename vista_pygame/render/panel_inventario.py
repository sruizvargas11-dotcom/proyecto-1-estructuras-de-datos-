"""Inventario integrado: vistas ordenadas y acciones sobre índices reales."""
import pygame
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar
from vista_pygame.render.panel_mazmorra import PanelMazmorra
from vista_pygame.render.boton_cerrar import dibujar_cerrar
from vista_pygame.render.panel_equipo import PanelEquipo
from vista_pygame.config_vista import COLOR_TEXTO, COLOR_TEXTO_TENUE, COLOR_ORO


class PanelInventario:
    RECT = pygame.Rect(974, 538, 292, 172)
    FILAS = 3
    ALTO_FILA = 43
    CRITERIOS = ('real', 'nombre', 'peso', 'valor')

    def __init__(self):
        self._panel = PanelMazmorra()
        self.desplazamiento = 0
        self.abierto = True
        self.criterio = 'real'
        self.seleccion = None
        self.cerrar = pygame.Rect(self.RECT.right-30, self.RECT.top+8, 20, 20)
        self.anterior = pygame.Rect(self.RECT.right-82, self.RECT.top+8, 22, 20)
        self.siguiente = pygame.Rect(self.RECT.right-57, self.RECT.top+8, 22, 20)
        self.orden = pygame.Rect(self.RECT.x+120, self.RECT.top+8, 79, 20)

    def objetos(self, estado):
        objetos = Vector()
        for i, o in enumerate(estado.inventario, 1):objetos.agregarValor((i, o))
        if self.criterio != 'real':
            def comparar(a, b):
                ka, kb = getattr(a[1], self.criterio), getattr(b[1], self.criterio)
                if self.criterio == 'nombre':ka, kb = ka.casefold(), kb.casefold()
                return (ka > kb)-(ka < kb)
            ordenar(objetos, comparar)
        return list(objetos)

    def filas(self, estado):
        objetos = self.objetos(estado)
        self.desplazamiento = max(0, min(self.desplazamiento, max(0, len(objetos)-self.FILAS)))
        resultado = []
        for n, (indice, objeto) in enumerate(objetos[self.desplazamiento:self.desplazamiento+self.FILAS]):
            fila = pygame.Rect(self.RECT.x+10, self.RECT.y+33+n*self.ALTO_FILA, self.RECT.width-20, self.ALTO_FILA-2)
            boton = pygame.Rect(fila.x+40, fila.y+20, 102, 20)
            resultado.append((indice, objeto, fila, boton))
        return resultado

    @staticmethod
    def boton_soltar(fila):return pygame.Rect(fila.x+150, fila.y+20, 70, 20)

    @staticmethod
    def accion(objeto, indice):
        if objeto.clase in ('arma', 'armadura'):
            return ('Desequipar', f'DEQ {indice}') if objeto.equipado else ('Equipar', f'EQ {indice}')
        if objeto.clase == 'antorcha':
            if objeto.encendida:return 'Apagar', f'AP {indice}'
            return ('Agotada', None) if getattr(objeto, 'agotada', False) else ('Encender', f'U {indice}')
        if objeto.clase in ('pocion', 'pocion_velocidad', 'antidoto'):return 'Consumir', f'U {indice}'
        if objeto.clase == 'pergamino_retroceso':return 'Usar', 'P'
        if objeto.clase == 'llave':return 'Al abrir puerta', None
        return 'Sin uso directo', None

    def manejar_evento(self, evento, estado):
        """Devuelve (capturado, comando); recorrer nunca consume tiempo."""
        if estado is None:return False, None
        cabecera = pygame.Rect(self.RECT.x, self.RECT.y, self.RECT.width, 32)
        if evento.type == pygame.MOUSEWHEEL and self.abierto and hasattr(evento, 'pos'):
            if self.RECT.collidepoint(evento.pos):
                self.desplazamiento -= evento.y;self.filas(estado)
                return True, None
        if evento.type != pygame.MOUSEBUTTONDOWN:return False, None
        pos = evento.pos
        if not self.abierto:
            if evento.button == 1 and cabecera.collidepoint(pos):
                self.abierto = True
                return True, None
            return False, None
        if not self.RECT.collidepoint(pos):return False, None
        if evento.button in (4, 5):
            self.desplazamiento += -1 if evento.button == 4 else 1
        elif evento.button == 1:
            if self.cerrar.collidepoint(pos):self.abierto = False
            elif self.anterior.collidepoint(pos):self.desplazamiento -= 1
            elif self.siguiente.collidepoint(pos):self.desplazamiento += 1
            elif self.orden.collidepoint(pos):
                self.criterio = self.CRITERIOS[(self.CRITERIOS.index(self.criterio)+1)%len(self.CRITERIOS)]
                self.desplazamiento = 0
            else:
                for indice, objeto, fila, boton in self.filas(estado):
                    if fila.collidepoint(pos):
                        self.seleccion = objeto.instancia_id
                        if boton.collidepoint(pos):return True, self.accion(objeto, indice)[1]
                        if self.boton_soltar(fila).collidepoint(pos):return True, f'T {indice}'
        self.filas(estado)
        return True, None

    def dibujar(self, pantalla, assets, estado, bloqueado=False):
        rect = self.RECT if self.abierto else pygame.Rect(self.RECT.x, self.RECT.y, self.RECT.width, 32)
        self._panel.dibujar(pantalla, rect)
        fuente = assets.fuente(14)
        titulo = f'Inventario ({len(estado.inventario)})' if self.abierto else 'Inventario  +'
        pantalla.blit(fuente.render(titulo, False, COLOR_ORO), (rect.x+12, rect.y+10))
        if not self.abierto:return
        dibujar_cerrar(pantalla, self.cerrar)
        pygame.draw.rect(pantalla, (39, 46, 55), self.orden)
        t = assets.fuente(12).render(self.criterio.capitalize(), False, COLOR_TEXTO)
        pantalla.blit(t, t.get_rect(center=self.orden.center))
        filas = self.filas(estado)
        for r, texto, disponible in ((self.anterior, '<', self.desplazamiento > 0),
                                    (self.siguiente, '>', self.desplazamiento+self.FILAS < len(estado.inventario))):
            pygame.draw.rect(pantalla, (47, 54, 62), r)
            t = fuente.render(texto, False, COLOR_TEXTO if disponible else (77, 83, 90))
            pantalla.blit(t, t.get_rect(center=r.center))
        if not filas:
            pantalla.blit(fuente.render('Vacío. Recoge objetos con R.', False, COLOR_TEXTO_TENUE), (rect.x+12, rect.y+58))
        for indice, objeto, fila, boton in filas:
            pygame.draw.rect(pantalla, (30, 40, 49) if objeto.instancia_id == self.seleccion else (18, 25, 34), fila)
            sprite = assets.sprite_objeto(objeto.tipo_id, objeto.clase)
            w, h = sprite.get_size();factor = min(32/max(1, w), 34/max(1, h))
            icono = pygame.transform.scale(sprite, (max(1, int(w*factor)), max(1, int(h*factor))))
            pantalla.blit(icono, icono.get_rect(center=(fila.x+18, fila.centery)))
            if objeto.clase=='antorcha' and getattr(objeto,'tiempo_restante',None) is not None:
                PanelEquipo.barra(pantalla,pygame.Rect(fila.x+3,fila.bottom-5,30,4),
                                  objeto.tiempo_restante,objeto.duracion)
            nombre = ('[E] ' if objeto.equipado else '')+objeto.nombre
            while fuente.size(nombre)[0] > fila.width-43 and len(nombre) > 1:nombre = nombre[:-2]+'…'
            pantalla.blit(fuente.render(nombre, False, COLOR_ORO if objeto.equipado else COLOR_TEXTO), (fila.x+40, fila.y+2))
            etiqueta, comando = self.accion(objeto, indice)
            for r, texto, deshabilitado in ((boton, etiqueta, bloqueado or comando is None),
                                            (self.boton_soltar(fila), 'Soltar', bloqueado)):
                pygame.draw.rect(pantalla, (31, 37, 43) if deshabilitado else (56, 65, 54), r)
                pygame.draw.rect(pantalla, (62, 69, 72) if deshabilitado else (117, 127, 106), r, 1)
                t = assets.fuente(12).render(texto, False, COLOR_TEXTO_TENUE if deshabilitado else COLOR_TEXTO)
                pantalla.blit(t, t.get_rect(center=r.center))
