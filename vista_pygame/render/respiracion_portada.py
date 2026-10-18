"""Respiración de una sola silueta: sin redibujar caras, manos ni equipo."""
from pathlib import Path
import math
import pygame

_cache=[]


def respiracion_portada(imagen,clave,cantidad=48):
    for nombre,cuadros in _cache:
        if nombre==(clave,cantidad):return cuadros
    w,h=imagen.get_size()
    # Los cuadros del arte de producción vienen precalculados. Si faltan,
    # conservamos el generador determinista como recuperación.
    ruta=Path(__file__).resolve().parents[2]/f'assets/ui/portada/respiracion_menu_{clave}.png'
    if cantidad==48:
        try:
            atlas=pygame.image.load(str(ruta)).convert_alpha()
            if atlas.get_size()==(w*8,h*6):
                resultado=tuple(atlas.subsurface(((n%8)*w,(n//8)*h,w,h)).copy() for n in range(48))
                _cache.append(((clave,cantidad),resultado));return resultado
        except (OSError,pygame.error):pass
    src=pygame.image.tobytes(imagen,'RGBA')
    cuadros=[];pesos=[]
    cx=w*.56;cy=h*.47
    cabeza=None;contorno=()
    if clave==0:
        proteccion=pygame.Surface((w,h),pygame.SRCALPHA)
        pygame.draw.polygon(proteccion,(255,255,255,255),
            ((29,30),(29,24),(31,20),(32,15),(39,12),(45,10),
             (52,9),(56,12),(61,13),(62,17),(65,18),(66,22),
             (64,25),(63,31),(60,35),(57,38),(51,39),(45,37),
             (41,34),(35,34)))
        cabeza=pygame.mask.from_surface(proteccion)
        contorno=cabeza.outline()
    for y in range(h):
        for x in range(w):
            # Campo continuo: desplazamiento subpíxel, cero en pies y armas.
            pecho=math.exp(-((x-cx)/(w*.23))**4-((y-cy)/(h*.28))**4)
            if clave==0:
                # Los hombros tienen amplitud propia; la cabeza es una zona
                # rígida local, en vez de congelar toda la fila de la imagen.
                izquierdo=math.exp(-((x-30)/13)**2-((y-40)/10)**2)
                derecho=math.exp(-((x-60)/11)**2-((y-43)/9)**2)
                pecho=max(pecho,izquierdo,derecho)
                # La distancia al contorno deja subir el cuello verde sin
                # arrastrar la cara ni crear una unión rígida por rectángulos.
                if cabeza.get_at((x,y)):
                    separacion=0
                else:
                    separacion=min(math.hypot(x-px,y-py) for px,py in contorno)
                pecho*=min(1,separacion/5)
                pecho*=max(0,min(1,(y-29)/7))
                pecho*=max(0,min(1,(54-y)/7))
                pecho*=max(0,min(1,(72-x)/10))
            elif clave==1:
                # El cráneo no se deforma ni se interpola: respira el tórax.
                pecho*=max(0,min(1,(y-34)/7))
            apoyo=max(0,min(1,(h-9-y)/12))
            pesos.append(pecho*apoyo)
    for n in range(cantidad):
        fase=math.sin(n*math.tau/cantidad)
        if clave==0:
            # Sale de la postura original y vuelve a ella, sin hundir el cuello.
            fase=(1-math.cos(n*math.tau/cantidad))*.5
        dst=bytearray(w*h*4)
        for y in range(h):
            for x in range(w):
                peso=pesos[y*w+x]
                # La raíz de las manos y los objetos externos al pecho no cambia.
                amplitud=1.0 if clave==0 else .85
                sy=max(0,min(h-1,y+fase*amplitud*peso))
                sx=max(0,min(w-1,x-(x-cx)*fase*.018*peso))
                x0=int(sx);y0=int(sy);fx=sx-x0;fy=sy-y0
                vecinos=((x0,y0,(1-fx)*(1-fy)),(min(w-1,x0+1),y0,fx*(1-fy)),
                         (x0,min(h-1,y0+1),(1-fx)*fy),(min(w-1,x0+1),min(h-1,y0+1),fx*fy))
                a=r=g=b=0
                for xx,yy,v in vecinos:
                    p=(yy*w+xx)*4;alpha=src[p+3]*v
                    a+=alpha;r+=src[p]*alpha;g+=src[p+1]*alpha;b+=src[p+2]*alpha
                p=(y*w+x)*4
                if a:
                    dst[p:p+4]=bytes((round(r/a),round(g/a),round(b/a),round(a)))
        cuadros.append(pygame.image.frombytes(bytes(dst),(w,h),'RGBA'))
    resultado=tuple(cuadros)
    _cache.append(((clave,cantidad),resultado))
    return resultado
