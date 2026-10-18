"""Sprites del paquete de arte, con carga perezosa y caché en Vector."""
from pathlib import Path
import unicodedata
import pygame

from estructuras.vector_dinamico import Vector
from vista_pygame.recursos.fuente_cripta import FuenteCripta
from vista_pygame.render.rata_dibujada import RataDibujada
from vista_pygame.render.criatura_dibujada import CriaturaDibujada,familia_criatura
from vista_pygame.render.heroe_compartido import heroe_compartido, OFFSET
from vista_pygame.render.heroe_equipo import VestuarioHeroe
from vista_pygame.render.rig_actores import cuadros_jugador, cuadros_rata, cuadros_criatura
from vista_pygame.contratos import CargadorAssets as ContratoAssets


def _nombre(valor):
    texto = ''.join(c for c in unicodedata.normalize('NFD', str(valor))
                    if unicodedata.category(c) != 'Mn').lower()
    return texto if texto and all(c.isalnum() or c in '_-' for c in texto) else 'generico'


class CargadorAssets(ContratoAssets):
    def __init__(self, carpeta=None):
        self.carpeta = Path(carpeta) if carpeta else Path(__file__).resolve().parents[2] / 'assets'
        self._superficies = Vector()
        self._fuentes = Vector()
        self._objetos_nuevos = None
        self._llaves = Vector()
        self._rata_nueva = None
        self._criaturas_nuevas = []
        self._vestuario = VestuarioHeroe(self.carpeta/'sprites/jugador')
        self._textos = Vector()
        self._resueltas = Vector()
        self._animados = Vector()
        self._usa_heroe_compartido = (self.carpeta/'sprites/jugador/animaciones_heroe.png').is_file()

    def _imagen(self, candidatos, tamano=(32, 32)):
        clave_resuelta = (tuple(candidatos), tamano)
        for clave, imagen in self._resueltas:
            if clave == clave_resuelta:
                return imagen
        imagen = self._cargar(candidatos, tamano)
        if len(self._resueltas) >= 256:
            self._resueltas = Vector()
        self._resueltas.agregarValor((clave_resuelta, imagen))
        return imagen

    def _cargar(self, candidatos, tamano):
        for relativo in candidatos:
            ruta = self.carpeta / relativo
            for clave, superficie in self._superficies:
                if clave == str(ruta):
                    return superficie
            try:
                imagen = pygame.image.load(str(ruta))
                # convert_alpha exige un modo de vídeo; la aplicación lo abre
                # antes de construir el cargador. Las pruebas pueden usar Surface.
                if pygame.display.get_surface() is not None:
                    imagen = imagen.convert_alpha()
                imagen = pygame.transform.scale(imagen, (imagen.get_width()*2, imagen.get_height()*2))
            except (OSError, ValueError, pygame.error):
                continue
            self._superficies.agregarValor((str(ruta), imagen))
            return imagen
        clave = ('fallback', tamano)
        for k, imagen in self._superficies:
            if k == clave:
                return imagen
        imagen = pygame.Surface((tamano[0]*2, tamano[1]*2), pygame.SRCALPHA)
        pygame.draw.rect(imagen, (82, 86, 98), imagen.get_rect().inflate(-8, -8))
        pygame.draw.rect(imagen, (198, 158, 74), imagen.get_rect().inflate(-8, -8), 2)
        self._superficies.agregarValor((clave, imagen))
        return imagen

    def tiene_heroe_compartido(self):
        return self._usa_heroe_compartido

    def _imagen_heroe_base(self):
        for k,im in self._superficies:
            if k=='heroe-compartido-base':return im
        frame=heroe_compartido().cuadros('reposo')[0]
        im=frame.subsurface(frame.get_bounding_rect()).copy()
        self._superficies.agregarValor(('heroe-compartido-base',im))
        return im

    def fotograma_jugador_equipado(self, estado, cuadro, equipo):
        if not (self.carpeta/'sprites/jugador/equipo_vacio.png').is_file():
            return self.fotograma_jugador(estado,cuadro)
        frames=self._vestuario.cuadros(estado,equipo)
        return frames[cuadro%len(frames)],OFFSET

    def cuadros_muerte_equipo(self, equipo):
        if not (self.carpeta/'sprites/jugador/equipo_vacio.png').is_file():return self.cuadros_muerte()
        return tuple((im,OFFSET) for im in self._vestuario.cuadros('muerte',equipo))

    def cuadros_espalda_equipo(self, equipo):
        return self._vestuario.pasos_espalda(equipo)

    def sprite_espalda_equipo(self, equipo):
        return self._vestuario.espalda(equipo)

    def cuadros_muerte(self):
        if self.tiene_heroe_compartido():
            return tuple((im,OFFSET) for im in heroe_compartido().cuadros('muerte'))
        return None

    def sprite_jugador(self, estado, direccion):
        if self.tiene_heroe_compartido():
            return self._imagen_heroe_base()
        estado, direccion = _nombre(estado), _nombre(direccion)
        return self._imagen((f'sprites/jugador/{estado}_{direccion}.png',
                             f'sprites/jugador/{estado}.png', 'sprites/jugador/idle.png'), (34, 50))

    def _rata(self):
        if self._rata_nueva is None:
            self._rata_nueva=RataDibujada(self.carpeta/'sprites/enemigos/rata_animada.png')
        return self._rata_nueva

    def _criatura(self,tipo,rol):
        familia=familia_criatura(_nombre(tipo),_nombre(rol))
        for nombre,criatura in self._criaturas_nuevas:
            if nombre==familia:return criatura
        ruta=self.carpeta/f'sprites/enemigos/{familia}_animado.png'
        if not ruta.is_file():return None
        criatura=CriaturaDibujada(ruta)
        self._criaturas_nuevas.append((familia,criatura))
        return criatura

    def sprite_enemigo(self, id_tipo, comportamiento):
        if 'rata' in str(id_tipo).lower() and (self.carpeta/'sprites/enemigos/rata_animada.png').is_file():
            return self._rata().base
        criatura=self._criatura(id_tipo,comportamiento)
        if criatura is not None:return criatura.base
        tipo, rol = _nombre(id_tipo), _nombre(comportamiento)
        return self._imagen((f'sprites/enemigos/{tipo}.png',
                             f'sprites/enemigos/{tipo.removeprefix("ent_")}.png',
                             f'sprites/enemigos/{rol}.png', 'sprites/enemigos/generico.png'))

    def sprite_objeto(self, id_tipo, clase):
        tipo, clase = _nombre(id_tipo), _nombre(clase)
        if clase=='llave':
            for clave,imagen in self._llaves:
                if clave==tipo:return imagen
            nombre=tipo.removeprefix('itm_')
            if nombre=='llave_salida':nombre='llave_negra'
            rutas=(f'sprites/objetos/{nombre}_detallada.png',f'sprites/objetos/{tipo}.png')
            for relativa in rutas:
                ruta=self.carpeta/relativa
                if not ruta.is_file():continue
                imagen=pygame.image.load(str(ruta)).convert_alpha()
                imagen=imagen.subsurface(imagen.get_bounding_rect(min_alpha=100)).copy()
                factor=22/max(imagen.get_size())
                imagen=pygame.transform.scale(imagen,(max(1,round(imagen.get_width()*factor)),
                                                      max(1,round(imagen.get_height()*factor))))
                imagen=pygame.transform.scale(imagen,(imagen.get_width()*2,imagen.get_height()*2))
                if len(self._llaves)>=64:self._llaves=Vector()
                self._llaves.agregarValor((tipo,imagen))
                return imagen
        atlas=self.carpeta/'sprites/objetos/objetos_detallados.png'
        if atlas.is_file():
            if self._objetos_nuevos is None:
                hoja=pygame.image.load(str(atlas)).convert_alpha();aw,ah=hoja.get_size();self._objetos_nuevos=[]
                for n in range(12):
                    x0,y0=round(n%4*aw/4),round(n//4*ah/3)
                    im=hoja.subsurface((x0,y0,round((n%4+1)*aw/4)-x0,round((n//4+1)*ah/3)-y0))
                    im=im.subsurface(im.get_bounding_rect(min_alpha=100)).copy()
                    factor=22/max(im.get_size());im=pygame.transform.scale(im,(max(1,round(im.get_width()*factor)),max(1,round(im.get_height()*factor))))
                    im=pygame.transform.scale(im,(im.get_width()*2,im.get_height()*2))
                    self._objetos_nuevos.append(im)
            indice=next((n for nombre,n in (('arma',0),('armadura',1),('llave',2),('pocion',3),
                        ('antidoto',4),('antorcha',5),('pocion_velocidad',6),('pergamino_retroceso',7)) if clase==nombre),11)
            if 'velocidad' in tipo:indice=6
            if clase=='llave' and any(p in tipo for p in ('salida','negra','negro')):indice=8
            return self._objetos_nuevos[indice]
        return self._imagen((f'sprites/objetos/{tipo}.png',
                             f'sprites/objetos/{tipo.removeprefix("itm_")}.png',
                             f'sprites/objetos/{clase}.png', 'sprites/objetos/generico.png'))

    def sprite_entorno(self, nombre):
        return self._imagen((f'sprites/entorno/{_nombre(nombre)}.png',))

    def sprite_efecto(self, nombre):
        return self._imagen((f'sprites/efectos/{_nombre(nombre)}.png',), (18, 18))

    def icono(self, nombre):
        return self._imagen((f'ui/icono_{_nombre(nombre)}.png',), (18, 18))

    def fuente(self, tamano):
        for numero, fuente in self._fuentes:
            if numero == tamano:
                return fuente
        fuente = FuenteCripta(tamano)
        self._fuentes.agregarValor((tamano, fuente))
        return fuente

    def texto(self, texto, tamano, color):
        clave = (str(texto), tamano, tuple(color))
        for k, imagen in self._textos:
            if k == clave:
                return imagen
        imagen = self.fuente(tamano).render(str(texto), False, color)
        # Los mensajes y el reloj cambian continuamente: caché acotada.
        if len(self._textos) >= 256:
            self._textos = Vector()
        self._textos.agregarValor((clave, imagen))
        return imagen


    def _cuadros(self, sprite, estado, familia):
        clave=(id(sprite),estado,familia)
        for k,cuadros in self._animados:
            if k == clave:
                return cuadros
        if familia == 'jugador':
            cuadros=cuadros_jugador(sprite,estado)
        elif familia == 'rata':
            cuadros=cuadros_rata(sprite,estado)
        else:
            cuadros=cuadros_criatura(sprite,estado)
        if len(self._animados)>=64:
            self._animados=Vector()
        self._animados.agregarValor((clave,cuadros))
        return cuadros

    def fotograma_jugador(self, estado, cuadro):
        if self.tiene_heroe_compartido():
            frames=heroe_compartido().cuadros(estado)
            return frames[cuadro%len(frames)],OFFSET
        sprite=self.sprite_jugador('parado','S')
        cuadros=self._cuadros(sprite,estado,'jugador')
        return cuadros[cuadro%len(cuadros)]

    def fotograma_enemigo(self, tipo_id, comportamiento, estado, cuadro):
        if 'rata' in str(tipo_id).lower() and (self.carpeta/'sprites/enemigos/rata_animada.png').is_file():
            return self._rata().fotograma(estado,cuadro)
        criatura=self._criatura(tipo_id,comportamiento)
        if criatura is not None:return criatura.fotograma(estado,cuadro)
        sprite=self.sprite_enemigo(tipo_id,comportamiento)
        familia='rata' if sprite.get_width()>sprite.get_height()*1.15 else 'criatura'
        cuadros=self._cuadros(sprite,estado,familia)
        return cuadros[cuadro%len(cuadros)]
