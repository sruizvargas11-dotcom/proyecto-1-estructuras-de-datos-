"""Modelo de rastrillo en 16 poses, proyectado sobre cada arco de la sala."""
import math
import pygame

CANTIDAD_CUADROS=16
_cache=[]
# Coordenadas medidas sobre el fondo en su tamaño lógico de 760 x 470.
# Los umbrales laterales bajan hacia el interior de la sala: no son rectángulos frontales.
PORTALES=(
    ('N',((350,9),(411,9),(411,91),(350,91))),
    ('S',((350,384),(411,384),(411,469),(350,469))),
    ('O',((18,166),(54,180),(54,258),(18,244))),
    ('E',((706,180),(742,166),(742,244),(706,258))),
)
_N=((352,42),(355,32),(360,23),(369,16),(378,12),(384,12),(393,16),(401,24),(407,35),(409,44),(409,90),(352,90))
_S=((352,418),(357,406),(364,398),(372,392),(380,387),(388,392),(399,400),(407,414),(409,425),(409,468),(352,468))
_O=((19,204),(24,192),(30,183),(37,179),(43,181),(48,190),(52,204),(52,248),(46,254),(33,249),(22,242),(19,237))
APERTURAS=(('N',_N),('S',_S),('O',_O),('E',tuple((760-x,y) for x,y in _O)))


def _escalar(puntos,tamano):
    return tuple((round(x*tamano[0]/760),round(y*tamano[1]/470)) for x,y in puntos)


def _plano(direccion,tamano):
    return _escalar(next(p for d,p in PORTALES if d==direccion),tamano)


def apertura_reja(direccion,tamano):
    return _escalar(next(p for d,p in APERTURAS if d==direccion),tamano)


def _modelo(ancho,alto,progreso,llave):
    im=pygame.Surface((ancho,alto),pygame.SRCALPHA)
    if progreso>=1:return im
    # Aceleración y frenado del mecanismo; toda la estructura sube unida.
    u=progreso*progreso*(3-2*progreso)
    subir=round((alto+8)*u)
    for n in range(5):
        x=round(4+n*(ancho-9)/4)
        pygame.draw.rect(im,(14,20,27),(x-1,-subir,4,alto+2))
        pygame.draw.line(im,(91,101,109),(x,-subir),(x,alto-subir),1)
        pygame.draw.line(im,(41,48,54),(x+2,-subir),(x+2,alto-subir),1)
        pygame.draw.line(im,(83,52,34),(x+1,alto//3-subir),(x+1,alto//3+5-subir),1)
    for y in (round(alto*.32),round(alto*.72),alto-5):
        y-=subir
        pygame.draw.rect(im,(18,25,33),(1,y,ancho-2,4))
        pygame.draw.line(im,(104,111,115),(2,y),(ancho-3,y),1)
        for x in (5,ancho//2,ancho-6):
            pygame.draw.rect(im,(126,130,127),(x,y+1,1,1))
    if llave:
        x,y=ancho//2,round(alto*.56)-subir
        pygame.draw.rect(im,(59,43,27),(x-5,y-1,10,12))
        pygame.draw.rect(im,(161,124,65),(x-4,y,8,10))
        pygame.draw.circle(im,(14,18,23),(x,y+4),1)
        pygame.draw.line(im,(14,18,23),(x,y+4),(x,y+7),1)
    return im


def fotogramas_reja(direccion,tamano,llave=False):
    clave=(direccion,tuple(tamano),bool(llave))
    for k,valor in _cache:
        if k==clave:return valor
    p=_plano(direccion,tamano)
    izquierda=min(x for x,y in p);arriba=min(y for x,y in p)
    ancho=max(x for x,y in p)-izquierda+1
    alto=max(y for x,y in p)-arriba+1
    altura_modelo=round(((p[3][1]-p[0][1])+(p[2][1]-p[1][1]))/2)+1
    contorno=apertura_reja(direccion,tamano)
    mascara=pygame.Surface((ancho,alto),pygame.SRCALPHA)
    pygame.draw.polygon(mascara,(255,255,255),[(x-izquierda,y-arriba) for x,y in contorno])
    cuadros=[]
    for n in range(CANTIDAD_CUADROS):
        modelo=_modelo(ancho,altura_modelo,n/(CANTIDAD_CUADROS-1),llave)
        proyectado=pygame.Surface((ancho,alto),pygame.SRCALPHA)
        # Columnas enteras, sin antialias: travesaños y cerradura comparten perspectiva.
        for x in range(ancho):
            u=x/max(1,ancho-1)
            techo=round(p[0][1]+u*(p[1][1]-p[0][1]))-arriba
            suelo=round(p[3][1]+u*(p[2][1]-p[3][1]))-arriba
            columna=pygame.transform.scale(modelo.subsurface((x,0,1,altura_modelo)),(1,suelo-techo+1))
            proyectado.blit(columna,(x,techo))
        proyectado.blit(mascara,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        cuadros.append(proyectado)
    valor=(tuple(cuadros),(izquierda,arriba))
    if len(_cache)>=32:_cache.clear()
    _cache.append((clave,valor))
    return valor


_tapiados=[]


def pared_tapiada(direccion,tamano,piedra=(46,54,64)):
    """Sin salida en el mapa: hueco sellado con piedra, sin candado falso."""
    clave=(direccion,tuple(tamano),tuple(piedra))
    for k,valor in _tapiados:
        if k==clave:return valor
    puntos=apertura_reja(direccion,tamano)
    x=min(x for x,y in puntos);y=min(y for x,y in puntos)
    w=max(px for px,py in puntos)-x+1;h=max(py for px,py in puntos)-y+1
    im=pygame.Surface((w,h),pygame.SRCALPHA);im.fill(piedra)
    sombra=tuple(max(0,c-25) for c in piedra)
    borde=tuple(min(255,c+19) for c in piedra)
    for yy in range(0,h,13):
        pygame.draw.line(im,sombra,(0,yy),(w,yy),2)
        for xx in range(-10+(yy//13%2)*12,w,25):
            pygame.draw.line(im,sombra,(xx,yy),(xx,yy+12),2)
            pygame.draw.line(im,borde,(xx+2,yy+3),(xx+21,yy+3),1)
    for n in range(max(1,w*h//28)):
        px=(n*17+3)%w;py=(n*29+7)%h
        im.set_at((px,py),tuple(min(255,c+4+n%12) for c in piedra))
    mascara=pygame.Surface((w,h),pygame.SRCALPHA)
    pygame.draw.polygon(mascara,(255,255,255),[(px-x,py-y) for px,py in puntos])
    im.blit(mascara,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    valor=(im,(x,y));_tapiados.append((clave,valor));return valor


def dibujar_rejas(pantalla,rect,salidas,puerta=None,solo_existentes=False,piedra=(46,54,64)):
    for direccion,_ in PORTALES:
        salida=next((s for s in salidas if s.direccion==direccion),None)
        if salida is None:
            if not solo_existentes:
                pared,pos=pared_tapiada(direccion,rect.size,piedra)
                pantalla.blit(pared,(rect.x+pos[0],rect.y+pos[1]))
            continue
        progreso=0 if salida.cerrada else 1
        if puerta is not None and puerta[0]==direccion:progreso=max(0,min(1,puerta[1]))
        # El candado pertenece al mismo modelo y proyección que la reja. Se
        # dibuja aunque el jugador todavía no tenga la llave correspondiente.
        cuadros,pos=fotogramas_reja(direccion,rect.size,salida.cerrada)
        cuadro=min(CANTIDAD_CUADROS-1,round(progreso*(CANTIDAD_CUADROS-1)))
        pantalla.blit(cuadros[cuadro],(rect.x+pos[0],rect.y+pos[1]))
