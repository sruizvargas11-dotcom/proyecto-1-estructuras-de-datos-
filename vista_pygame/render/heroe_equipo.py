"""Ocho equipos visuales, siempre a partir de fotogramas completos."""
from pathlib import Path
import pygame
from vista_pygame.render.heroe_compartido import PIES, _figura

NOMBRES = ('vacio', 'espada', 'antorcha', 'espada_antorcha', 'armadura',
           'armadura_espada', 'armadura_antorcha', 'armadura_espada_antorcha')
ESTADOS = ('reposo', 'caminar', 'ataque', 'muerte', 'recoger')


def clave_equipo(estado):
    """La luz depende de una antorcha encendida en el inventario, no de poseerla."""
    antorcha = any(o.clase == 'antorcha' and o.encendida for o in getattr(estado, "inventario", ()))
    return int(bool(getattr(estado,"arma_equipada",None))) | (int(antorcha)<<1) | (int(bool(getattr(estado,"armadura_equipada",None)))<<2)


def figuras_atlas(ruta, filas, columnas):
    atlas = pygame.image.load(str(ruta)).convert_alpha()
    mascara = pygame.mask.from_surface(atlas, 100)
    componentes = mascara.connected_components(350)
    if len(componentes) < filas*columnas:
        # Dos poses verticales pueden tocarse por un único píxel (la punta
        # de una llama y una bota). Se separa ese puente solo en la máscara
        # de extracción; el PNG original permanece intacto. Nunca se recorta
        # una celda rectangular que partiría la espada de otro fotograma.
        for componente in componentes:
            r = componente.get_bounding_rects()[0]
            if r.height <= atlas.get_height()/filas*1.6:continue
            margen = max(1, round(r.height*.08))
            candidatos = [(sum(componente.get_at((x,y)) for x in range(r.left,r.right)),y)
                          for y in range(r.centery-margen,r.centery+margen)]
            cantidad, corte = min(candidatos)
            if cantidad <= max(2,round(r.width*.02)):
                for x in range(r.left,r.right):mascara.set_at((x,corte),0)
        componentes = mascara.connected_components(350)
    if len(componentes) != filas*columnas:
        raise ValueError(f'{Path(ruta).name}: se esperaban {filas*columnas} figuras completas, hay {len(componentes)}')
    # Aislar por componente permite conservar una espada que sobrepasa la
    # división nominal de celda, sin tomar fragmentos del vecino.
    componentes.sort(key=lambda c:c.get_bounding_rects()[0].centery)
    resultado = []
    for fila in range(filas):
        grupo = componentes[fila*columnas:(fila+1)*columnas]
        grupo.sort(key=lambda c:c.get_bounding_rects()[0].x)
        resultado.append([_figura(atlas,c) for c in grupo])
    return resultado


class HeroeEquipo:
    def __init__(self, carpeta, clave):
        filas = figuras_atlas(Path(carpeta)/f'equipo_{NOMBRES[clave]}.png', 5, 4)
        # La llama ocupa altura adicional: el CUERPO conserva la escala al
        # alternar equipo. La escala de agacharse/morir tampoco se normaliza.
        altura = 96 if clave & 2 else 78
        escala = altura/max(im.get_height() for im in filas[0])
        self._filas = []
        for fila in filas:
            registrados = []
            for im in fila:
                im = pygame.transform.scale(im, (max(1,round(im.get_width()*escala)), max(1,round(im.get_height()*escala))))
                apoyo = [x for y in range(max(0,im.get_height()-3),im.get_height())
                         for x in range(im.get_width()) if im.get_at((x,y)).a>100]
                centro = round(sum(apoyo)/len(apoyo)) if apoyo else im.get_width()//2
                frame = pygame.Surface((256,192),pygame.SRCALPHA)
                frame.blit(im,(PIES[0]-centro,PIES[1]-im.get_height()))
                registrados.append(frame)
            self._filas.append(tuple(registrados))
        self._secuencias=[]

    def cuadros(self, estado):
        if estado not in ESTADOS:estado='reposo'
        for clave, frames in self._secuencias:
            if clave==estado:return frames
        poses=self._filas[ESTADOS.index(estado)]
        cantidad=48 if estado in ('reposo','muerte') else 32
        frames=tuple(poses[min(3,i*4//cantidad)] for i in range(cantidad))
        self._secuencias.append((estado,frames))
        return frames


class VestuarioHeroe:
    def __init__(self, carpeta):
        self.carpeta=Path(carpeta)
        self._variantes=[]
        self._espaldas=None
        self._ciclos_espaldas=[]

    def cuadros(self, estado, clave):
        for k, heroe in self._variantes:
            if k==clave:return heroe.cuadros(estado)
        heroe=HeroeEquipo(self.carpeta,clave)
        self._variantes.append((clave,heroe))
        return heroe.cuadros(estado)

    def pasos_espalda(self, clave):
        for k,poses in self._ciclos_espaldas:
            if k==clave:return poses
        nombre=('caminar_espaldas_vacio.png' if clave==0 else
                'caminar_espaldas.png' if clave==3 else f'salida_espaldas_{clave}.png')
        poses=tuple(im for fila in figuras_atlas(self.carpeta/nombre,2,4) for im in fila)
        self._ciclos_espaldas.append((clave,poses))
        return poses

    def espalda(self, clave):
        if self._espaldas is None:
            self._espaldas=tuple(im for fila in figuras_atlas(self.carpeta/'equipo_espaldas.png',2,4) for im in fila)
        return self._espaldas[clave]
