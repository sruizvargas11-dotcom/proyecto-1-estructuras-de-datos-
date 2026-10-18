"""Portada pixel art por capas; animación visual determinista y precalculada."""
from pathlib import Path
import math
import pygame
from vista_pygame.render.respiracion_portada import respiracion_portada
from vista_pygame.render.parpadeo_portada import preparar_parpadeos, fase_parpadeo
from vista_pygame.render.fuego_pixel import cuadros_llama as _llamas
from vista_pygame.render.ojo_torre import cargar_ojo, cuadro_ojo
from vista_pygame.render.aura_ojo import preparar_aura
from vista_pygame.render.integracion_ojo import preparar_integracion, remodelar_cuenca, REGION

RAIZ = Path(__file__).resolve().parents[2]
RUTA_LIMPIA = RAIZ / 'assets/ui/portada/portada_base_v3.png'
RUTA_PERSONAJES = RAIZ / 'assets/ui/portada/personajes_menu_pixelart.png'
RUTA_NUBES = RAIZ / 'assets/ui/portada/nubes_menu.png'
RUTA_SILUETA = RAIZ / 'assets/ui/portada/portada_silueta.png'
RUTA_FUEGO = RAIZ / 'assets/ui/portada/fuego_menu_pixelart.png'

# Coordenadas del arte, compartidas con el fondo incluso en ventanas no 16:9.
BRASEROS = ((526, 108, 22, 44), (1042, 409, 15, 34),
            (1373, 452, 17, 39), (1598, 493, 18, 42))
RAYOS_MS = (9000, 23000, 38000)
CICLO_TORMENTA_MS = 49000


def _cuadros_atlas(atlas):
    """Lee poses dibujadas completas: no separa ni deforma miembros por filas.

    El atlas tiene márgenes artísticos, por eso sus bandas se expresan como
    proporciones. Se registra cada pose por los pies, con escala común por fila.
    """
    w, h = atlas.get_size()
    bandas = ((.01, .219), (.220, .431), (.435, .623),
              (.624, .815), (.816, 1.0))
    resultado = []
    for y0, y1 in bandas:
        banda = atlas.subsurface((0, round(y0*h), w, round(y1*h)-round(y0*h)))
        mascara = pygame.mask.from_surface(banda, 100)
        partes = mascara.connected_components(800)
        rects = [parte.get_bounding_rects()[0] for parte in partes]
        rects = sorted(sorted(rects, key=lambda r: r.w*r.h, reverse=True)[:4], key=lambda r: r.x)
        if len(rects) != 4:
            raise ValueError('El atlas del menú debe contener cuatro poses por personaje')
        escala = 88 / max(r.h for r in rects)
        preparadas = []
        for rect in rects:
            original = banda.subsurface(rect).copy()
            # Muestreo nearest a una cuadrícula pequeña y fija: píxeles nítidos.
            mini = pygame.transform.scale(original, (round(rect.w*escala), round(rect.h*escala)))
            pies = [(x, y) for y in range(max(0, mini.get_height()-6), mini.get_height())
                    for x in range(mini.get_width()) if mini.get_at((x, y)).a > 128]
            centro = round(sum(x for x, _ in pies)/len(pies))
            preparadas.append((mini,centro))
        # El centro de los pies no es el centro de la silueta: una espada
        # o una mano extendida puede quedar muy lejos a un lado.
        radio = max(max(c,mini.get_width()-c) for mini,c in preparadas)+8
        ancho = radio*2
        cuadros = []
        antorchas = []
        for mini,centro in preparadas:
            lienzo = pygame.Surface((ancho, 94), pygame.SRCALPHA)
            px, py = ancho//2-centro, 92-mini.get_height()
            lienzo.blit(mini, (px, py))
            cima = [(x, y) for y in range(min(5, mini.get_height()))
                        for x in range(mini.get_width()) if mini.get_at((x, y)).a > 128]
            antorchas.append((px+round(sum(x for x, _ in cima)/len(cima)), py+5))
            cuadros.append(lienzo)
        resultado.append((tuple(cuadros), tuple(antorchas)))
    return resultado




class PortadaAnimada:
    def __init__(self):
        self.disponible = False
        self._tamano = None
        self._tiempo = 0
        try:
            self._base = pygame.image.load(str(RUTA_LIMPIA)).convert()
            atlas = pygame.image.load(str(RUTA_PERSONAJES)).convert_alpha()
            self._nubes_original = pygame.image.load(str(RUTA_NUBES)).convert_alpha()
            fuego=pygame.image.load(str(RUTA_FUEGO)).convert_alpha()
            silueta = pygame.image.load(str(RUTA_SILUETA)).convert_alpha()
            self._mascara_original = pygame.mask.from_surface(silueta,80).to_surface(
                setcolor=(255,255,255,0),unsetcolor=(255,255,255,255)).convert_alpha()
            # La extracción conserva algo de halo ámbar dentro de la U de
            # la torre. Ese aire debe dejar pasar las nubes; el cuenco no.
            for y in range(55,150):
                for x in range(485,567):
                    if 503<=x<=551 and 94<=y<=145:continue
                    r,g,b=self._base.get_at((x,y))[:3]
                    if r>g*1.3 and r>b*1.7:
                        self._mascara_original.set_at((x,y),(255,255,255,255))
            self._base,self._mascara_original = remodelar_cuenca(self._base,self._mascara_original)
            self._capas = _cuadros_atlas(atlas)
            for i in range(len(self._capas)):
                cuadros,anclas=self._capas[i]
                respiracion=respiracion_portada(cuadros[0],i)
                if i==0:
                    anclas=(anclas[0],)*len(respiracion)
                self._capas[i]=(respiracion,anclas)
        except (OSError, ValueError, pygame.error):
            return
        self.disponible = True
        self._fuegos = tuple(_llamas(w, h,fuego) for _, _, w, h in BRASEROS)
        self._fuego_heroe = _llamas(14, 27,fuego)
        self._aura = preparar_aura(self._mascara_original)
        self._ojo = cargar_ojo()
        self._ojo_integrado = preparar_integracion(self._base,self._mascara_original,self._ojo)

    def _punto(self, x, y):
        return (round(self._origen[0]+x*self._escala),
                round(self._origen[1]+y*self._escala))

    def ajustar(self, tamano):
        if self._tamano == tamano or not self.disponible:
            return
        self._tamano = tamano
        w, h = tamano
        bw, bh = self._base.get_size()
        self._escala = max(w/bw, h/bh)
        size = (math.ceil(bw*self._escala), math.ceil(bh*self._escala))
        self._origen = ((w-size[0])//2, (h-size[1])//2)
        self._fondo = pygame.Surface(tamano)
        self._fondo.blit(pygame.transform.scale(self._base, size), self._origen)
        # Recorte del contorno real del arte; no polígonos aproximados
        # que dejen triángulos de cielo vacío alrededor de las almenas.
        self._mascara_cielo = pygame.Surface(tamano, pygame.SRCALPHA)
        self._mascara_cielo.blit(pygame.transform.scale(self._mascara_original,size),self._origen)
        self._cielo = pygame.Surface(tamano, pygame.SRCALPHA)
        self._nubes = []
        for factor, alto, alpha in ((1.5, 290, 115), (1.25, 265, 190)):
            capa = pygame.transform.scale(self._nubes_original,
                (round(size[0]*factor), round(alto*self._escala)))
            capa.set_alpha(alpha)
            self._nubes.append(capa)
        self._actores = []
        self._parpadeos = []
        posiciones = ((300,698,240), (1450,705,205), (1580,750,200),
                      (1300,738,214), (1465,844,200))
        for indice,((cuadros, antorchas), (x,y,alto)) in enumerate(zip(self._capas, posiciones)):
            escala = alto*self._escala/94
            self._parpadeos.append(preparar_parpadeos(cuadros,indice,escala))
            dimensiones = (round(cuadros[0].get_width()*escala), round(cuadros[0].get_height()*escala))
            frames = tuple(pygame.transform.scale(c, dimensiones) for c in cuadros)
            pies = self._punto(x,y)
            esquina = (pies[0]-dimensiones[0]//2, pies[1]-dimensiones[1])
            anclas = tuple((esquina[0]+round(ax*escala),esquina[1]+round(ay*escala))
                           for ax,ay in antorchas)
            self._actores.append((frames, esquina, pies, anclas))
        self._fuegos_escalados = tuple(tuple(pygame.transform.scale(im,
            (max(1,round(im.get_width()*self._escala)),
             max(1,round(im.get_height()*self._escala)))) for im in frames)
            for frames in self._fuegos)
        # El fuego del héroe usa la misma escala que su cuerpo.
        eh = posiciones[0][2]*self._escala/94
        self._raiz_fuego_heroe = round(6*eh)
        self._heroe_llamas = tuple(pygame.transform.scale(im,
            (max(1,round(im.get_width()*eh)),max(1,round(im.get_height()*eh))))
            for im in self._fuego_heroe)
        self._ojo_escalado = tuple(pygame.transform.scale(im,
            (max(1,round(im.get_width()*self._escala)),max(1,round(im.get_height()*self._escala))))
            for im in self._ojo_integrado)
        tamano_aura=self._ojo_escalado[0].get_size()
        self._aura_escalada=tuple(tuple(pygame.transform.scale(im,tamano_aura) for im in capas)
                                 for capas in self._aura)
        self._hierros = []
        for x,y,_,_ in BRASEROS:
            rect=pygame.Rect(x-23,y-4,46,32).clip(self._base.get_rect())
            metal=pygame.Surface(rect.size,pygame.SRCALPHA)
            for yy in range(rect.h):
                for xx in range(rect.w):
                    color=self._base.get_at((rect.x+xx,rect.y+yy))
                    if max(color[:3])<100 and color.r<color.b*1.6+8:
                        metal.set_at((xx,yy),color)
            self._hierros.append((pygame.transform.scale(metal,
                (max(1,round(rect.w*self._escala)),max(1,round(rect.h*self._escala)))),
                self._punto(rect.x,rect.y)))
        self._resplandores=[]
        for radio in (70,35,40,43,29):
            radio=max(4,round(radio*self._escala));glow=pygame.Surface((radio*2,radio*2),pygame.SRCALPHA)
            for rr in range(radio,0,-1):
                a=round(30*(1-rr/radio)**2)
                pygame.draw.circle(glow,(244,103,29,a),(radio,radio),rr)
            self._resplandores.append(glow)
        self._sombras = pygame.Surface(tamano, pygame.SRCALPHA)
        suelo=pygame.Surface(tamano,pygame.SRCALPHA)
        for poligono in (((0,555),(125,608),(309,617),(526,642),(549,659),(420,719),(270,766),(0,797)),
                         ((916,594),(1000,536),(1140,475),(1672,584),(1672,941),(1200,941),(1050,840))):
            pygame.draw.polygon(suelo,(255,255,255,255),[self._punto(*p) for p in poligono])
        for frames, esquina, pies, _ in self._actores:
            recorte=frames[0].get_bounding_rect()
            centro_pies=pies[0]-esquina[0]-recorte.left
            forma=pygame.mask.from_surface(frames[0].subsurface(recorte)).to_surface(
                setcolor=(5,9,18,105),unsetcolor=(0,0,0,0)).convert_alpha()
            forma=pygame.transform.flip(forma,False,True)
            sh=max(3,round(forma.get_height()*.24));sw=forma.get_width()
            forma=pygame.transform.scale(forma,(sw,sh))
            proyeccion=pygame.Surface((sw+sh+8,sh+4),pygame.SRCALPHA)
            for yy in range(sh):
                fila=forma.subsurface((0,yy,sw,1)).copy()
                fila.set_alpha(round(220*(1-yy/sh)))
                proyeccion.blit(fila,(sh-yy,yy))
            suave=pygame.transform.smoothscale(proyeccion,
                (max(1,proyeccion.get_width()//3),max(1,proyeccion.get_height()//3)))
            suave=pygame.transform.smoothscale(suave,proyeccion.get_size())
            self._sombras.blit(suave,(pies[0]-centro_pies-sh,pies[1]-round(6*self._escala)))
            sw=max(6,round(frames[0].get_width()*.34));sh=max(3,round(12*self._escala))
            contacto=pygame.Surface((sw,sh),pygame.SRCALPHA)
            for n in range(7):
                pygame.draw.ellipse(contacto,(4,8,15,18+n*17),
                    (n,round(n*sh/20),max(1,sw-2*n),max(1,sh-round(n*sh/10))))
            self._sombras.blit(contacto,(pies[0]-sw//2,pies[1]-sh+round(2*self._escala)))
        self._sombras.blit(suelo,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        self._rayos = []
        for x in (930,1180,680):
            rayo = pygame.Surface(tamano, pygame.SRCALPHA)
            puntos = [(x,65),(x-25,118),(x+6,108),(x-22,176),
                      (x+3,165),(x-37,250),(x-48,318)]
            pygame.draw.lines(rayo,(94,126,181,70),False,
                              [self._punto(*p) for p in puntos],max(2,round(7*self._escala)))
            pygame.draw.lines(rayo,(209,226,249,240),False,
                              [self._punto(*p) for p in puntos],max(1,round(2*self._escala)))
            pygame.draw.lines(rayo,(153,184,224,180),False,
                [self._punto(x-22,176),self._punto(x-65,205),self._punto(x-90,259)],
                max(1,round(self._escala)))
            self._rayos.append(rayo)

    def actualizar(self, dt):
        self._tiempo += max(0, dt)

    def cuadro_actor(self,i):
        periodo=3600 if i==0 else 2400+i*130
        cantidad=len(self._capas[i][0])
        return int(((self._tiempo+i*470)%periodo)*cantidad/periodo)

    def estado_rayo(self):
        instante = self._tiempo % CICLO_TORMENTA_MS
        for i, inicio in enumerate(RAYOS_MS):
            t = instante-inicio
            if 0 <= t < 75:
                return i, 1-t/100
            if 125 <= t < 225:
                return i, .65*(1-(t-125)/100)
        return None

    def dibujar(self, pantalla):
        if not self.disponible:
            return
        self.ajustar(pantalla.get_size())
        pantalla.blit(self._fondo,(0,0))
        self._cielo.fill((0,0,0,0))
        rayo = self.estado_rayo()
        if rayo:
            i, fuerza = rayo
            self._cielo.fill((117,151,203,round(22*fuerza)))
            self._rayos[i].set_alpha(round(255*fuerza))
            self._cielo.blit(self._rayos[i],(0,0))
        for i, capa in enumerate(self._nubes):
            dx = round(self._tiempo*(.005+i*.004)*self._escala)%capa.get_width()
            y = self._punto(0,-40+i*32)[1]
            self._cielo.blit(capa,(-dx,y))
            self._cielo.blit(capa,(capa.get_width()-dx,y))
        self._cielo.blit(self._mascara_cielo,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        pantalla.blit(self._cielo,(0,0))
        pantalla.blit(self._sombras,(0,0))
        for i,(frames, esquina, _, _) in enumerate(self._actores):
            # Respiración continua de una silueta, con pies registrados.
            # Cadencias distintas evitan que todos respiren al unísono.
            cuadro=self.cuadro_actor(i)
            pantalla.blit(frames[cuadro],esquina)
            ojos=self._parpadeos[i][cuadro][fase_parpadeo(self._tiempo,i)]
            if ojos is not None:
                parche,offset=ojos
                pantalla.blit(parche,(esquina[0]+offset[0],esquina[1]+offset[1]))
        cuadro = int(self._tiempo//105)%12
        for i,((x,y,_,_), frames) in enumerate(zip(BRASEROS,self._fuegos_escalados)):
            if i==0:
                # El ojo reemplaza únicamente la llama de la torre distante.
                im=self._ojo_escalado[cuadro_ojo(self._tiempo)]
                posicion=self._punto(REGION.x,REGION.y)
                aura,reflejo=self._aura_escalada[int(self._tiempo//55)%48]
                pantalla.blit(aura,posicion)
                pantalla.blit(im,posicion)
                pantalla.blit(reflejo,posicion)
                continue
            im=frames[cuadro];p=self._punto(x,y)
            posicion=(p[0]-im.get_width()//2,p[1]-im.get_height()+round(5*self._escala))
            glow=self._resplandores[i]
            pantalla.blit(glow,glow.get_rect(center=p))
            pantalla.blit(im,posicion)
            # Solo el hierro opaco cruza la llama, nunca un parche de pared.
            metal,esquina=self._hierros[i];pantalla.blit(metal,esquina)
        im=self._heroe_llamas[cuadro]
        x,y=self._actores[0][3][self.cuadro_actor(0)]
        glow=self._resplandores[-1]
        pantalla.blit(glow,glow.get_rect(center=(x,y)))
        # El borde visible de la llama llega a la mitad del cabezal de madera.
        base_visible=im.get_bounding_rect().bottom
        pantalla.blit(im,(x-im.get_width()//2,y+self._raiz_fuego_heroe-base_visible))
