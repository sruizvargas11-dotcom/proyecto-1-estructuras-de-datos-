"""Luz, perspectiva atmosférica y oclusión del ojo sobre la piedra original."""
import math
from pathlib import Path
import pygame

REGION = pygame.Rect(454, 34, 144, 200)
CENTRO = (526, 94)
_cache_clave = None
_cache_cuadros = None


def remodelar_cuenca(base, cielo):
    """Sustituye solo el cuenco antiguo, conservando la silueta original."""
    ruta = Path(__file__).resolve().parents[2]/'assets/ui/torre_cuenca_integrada.png'
    arte = pygame.image.load(str(ruta)).convert()
    arte = pygame.transform.scale(arte,REGION.size)
    base = base.copy()
    cielo = cielo.copy()
    for y in range(62,162):
        for x in range(490,563):
            mezcla = max(0,min(1,(x-490)/6,(563-x)/6,(y-62)/6,(162-y)/10))
            a=base.get_at((x,y));b=arte.get_at((x-REGION.x,y-REGION.y))
            base.set_at((x,y),tuple(round(a[i]*(1-mezcla)+b[i]*mezcla) for i in range(3)))
            # El hueco liberado por el cuenco vuelve a ser cielo animado.
            if (501<=x<=551 and 70<=y<=136) or (512<=x<=540 and 136<y<=143):
                cielo.set_at((x,y),(255,255,255,255))
    return base,cielo


def preparar_integracion(base, cielo, ojos):
    """Precalcula la composición local; el render no altera ni lee texturas."""
    global _cache_clave, _cache_cuadros
    clave = (pygame.image.tobytes(base.subsurface(REGION),'RGB'),
             pygame.image.tobytes(cielo.subsurface(REGION),'RGBA'),tuple(id(im) for im in ojos))
    if clave == _cache_clave:
        return _cache_cuadros
    resultados = []
    # Intensidad de la luz reflejada: disminuye al cerrarse los párpados.
    intensidades = (1, .95, .8, .6, .4, .6, .85, 1)
    for ojo, intensidad in zip(ojos, intensidades):
        capa = pygame.Surface(REGION.size, pygame.SRCALPHA)
        for yy in range(REGION.h):
            y = REGION.y+yy
            for xx in range(REGION.w):
                x = REGION.x+xx
                dx, dy = x-CENTRO[0], y-CENTRO[1]
                distancia = (dx/58)**2+(dy/65)**2
                halo = round(19*math.exp(-distancia*2)*intensidad)
                if halo:
                    capa.set_at((xx,yy),(167,77,25,halo))
                # Solo la geometría original recibe reflejos; nunca se pinta
                # un rectángulo de pared sobre el cielo ni sobre las nubes.
                if cielo.get_at((x,y)).a>20:
                    continue
                color = base.get_at((x,y))
                caida = math.exp(-((dx/55)**2+((y-100)/82)**2))
                # Caras interiores hacia el ojo: cálidas. Caras exteriores:
                # penumbra fría. Se conserva la textura de cada bloque.
                interior = max(0,1-abs(dx)/61)
                luz = caida*intensidad*interior
                sombra = caida*(1-interior)*.22
                r = round(color.r*(1-sombra)+31*luz)
                g = round(color.g*(1-sombra)+13*luz)
                b = round(color.b*(1-sombra)+2*luz)
                # Sombra de contacto bajo la cuenca del ojo.
                contacto = math.exp(-((dx/26)**2+((y-121)/8)**2))*.2
                capa.set_at((xx,yy),(min(255,round(r*(1-contacto))),
                    min(255,round(g*(1-contacto))),min(255,round(b*(1-contacto))),255))
        # Menor contraste y temperatura acorde a la distancia de la torre.
        im = pygame.transform.scale(ojo,(62,44))
        for y in range(im.get_height()):
            for x in range(im.get_width()):
                r,g,b,a = im.get_at((x,y))
                d = ((x-31)/29)**2+((y-22)/19)**2
                borde = max(0,min(1,(1.22-d)/.42))
                im.set_at((x,y),(round(r*.78+10),round(g*.85+9),
                                  min(255,round(b*.85+15)),round(a*borde)))
        pos = (CENTRO[0]-REGION.x-im.get_width()//2,
               CENTRO[1]-REGION.y-im.get_height()//2)
        capa.blit(im,pos)
        # La piedra está DELANTE del ojo en las puntas y en el labio inferior.
        # Se recuperan sus píxeles ya iluminados, sin añadir soportes nuevos.
        for yy in range(REGION.h):
            y = REGION.y+yy
            for xx in range(REGION.w):
                x = REGION.x+xx
                delante = (x<494 or x>558) or y>=113
                if not delante or cielo.get_at((x,y)).a>20:
                    continue
                c = base.get_at((x,y))
                # El metal oscuro del borde interrumpe el halo del ojo.
                if y<137 and max(c[:3])<100:
                    luz = math.exp(-(((x-526)/45)**2+((y-100)/55)**2))*intensidad
                    capa.set_at((xx,yy),(min(255,round(c.r+15*luz)),
                                         min(255,round(c.g+6*luz)),c.b,255))
        resultados.append(capa)
    _cache_clave, _cache_cuadros = clave, tuple(resultados)
    return _cache_cuadros
