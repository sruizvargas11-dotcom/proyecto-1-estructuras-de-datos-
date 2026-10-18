"""Aura pixelada precalculada; filamentos detrás de la piedra y luz sobre ella."""
import math
import pygame
from vista_pygame.render.integracion_ojo import REGION, CENTRO

_cache_clave = None
_cache = None


def preparar_aura(cielo):
    global _cache_clave, _cache
    mascara = cielo.subsurface(REGION)
    clave = pygame.image.tobytes(mascara,'RGBA')
    if clave == _cache_clave:
        return _cache
    cx,cy=CENTRO[0]-REGION.x,CENTRO[1]-REGION.y
    # Color volumétrico: amplitud suave e irregular, sin disco de borde duro.
    halo=pygame.Surface(REGION.size,pygame.SRCALPHA)
    for y in range(REGION.h):
        for x in range(REGION.w):
            d=((x-cx)/44)**2+((y-cy)/33)**2
            a=round(130*math.exp(-d*1.25))
            if a:halo.set_at((x,y),(204,84,22,a))
    frames=[]
    for n in range(48):
        fase=n*math.tau/48
        fondo=halo.copy();fondo.set_alpha(round(195+35*math.sin(fase)))
        # Convertimos el alpha global antes de componer otros trazos.
        bruma=pygame.Surface(REGION.size,pygame.SRCALPHA);bruma.blit(fondo,(0,0))
        fondo=bruma
        filamentos=pygame.Surface(REGION.size,pygame.SRCALPHA)
        # Dos corrientes suben desde la abertura hasta los extremos del ojo.
        for lado in (-1,1):
            puntos=[]
            for k in range(26):
                t=k/25
                x=cx+lado*(24-14*t)+math.sin(t*7-fase+lado)*4*math.sin(math.pi*t)
                y=142-REGION.y-48*t
                puntos.append((round(x),round(y)))
            pygame.draw.lines(filamentos,(191,76,24,18),False,puntos,3)
            for k in range(25):
                pulso=(math.sin(k*.4-fase*2+lado)+1)/2
                pygame.draw.line(filamentos,(246,142,45,round(22+120*pulso**3)),puntos[k],puntos[k+1],1)
        # Fragmentos curvos, no un anillo cerrado que parezca un marco.
        for j in range(3):
            puntos=[]
            for k in range(18):
                a=fase*.55+j*math.tau/3+k*.04
                puntos.append((round(cx+math.cos(a)*(34+j)),round(cy+math.sin(a)*22)))
            pygame.draw.lines(filamentos,(235,117,34,92),False,puntos,1)
        # Brasas pequeñas con recorrido determinista y desaparición suave.
        for j in range(8):
            t=(n/48+j*.137)%1
            x=cx+math.sin(j*4.1+t*3)*(12+15*t)
            y=cy+17-61*t
            a=round(180*math.sin(math.pi*t)**1.5)
            punto=(round(x),round(y))
            pygame.draw.circle(filamentos,(239,97,23,a//3),punto,2)
            pygame.draw.line(filamentos,(255,186,76,a),punto,(punto[0],punto[1]+1),1)
        # Los filamentos no atraviesan ni las puntas ni los bloques de la torre.
        filamentos.blit(mascara,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        fondo.blit(filamentos,(0,0))
        # Reflejo respirante sobre el material, separado del aura en el aire.
        reflejo=pygame.Surface(REGION.size,pygame.SRCALPHA)
        for y in range(REGION.h):
            for x in range(REGION.w):
                if mascara.get_at((x,y)).a>20:continue
                d=((x-cx)/48)**2+((y-cy)/68)**2
                a=round((30+12*math.sin(fase))*math.exp(-d*1.5))
                if a:reflejo.set_at((x,y),(220,104,29,a))
        frames.append((fondo,reflejo))
    _cache_clave,_cache=clave,tuple(frames)
    return _cache
