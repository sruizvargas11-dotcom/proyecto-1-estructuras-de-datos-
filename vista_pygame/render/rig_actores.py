"""Animación por huesos cortos y siluetas completas, sin recortes del cuerpo."""
import math
import pygame

CONTORNO=(20,24,31)
CAPA=(74,107,66)
PIEL=(217,167,126)


def _rotar(v,a):
    a=math.radians(a);x,y=v
    return (x*math.cos(a)+y*math.sin(a),-x*math.sin(a)+y*math.cos(a))


def _p(p):return (round(p[0]),round(p[1]))


def _sum(a,b):return (a[0]+b[0],a[1]+b[1])


def _miembro(s,puntos,color,ancho):
    """Los discos de las articulaciones cubren la unión entre los huesos."""
    puntos=[_p(p) for p in puntos]
    pygame.draw.lines(s,CONTORNO,False,puntos,ancho+2)
    for p in puntos:pygame.draw.circle(s,CONTORNO,p,(ancho+2)//2)
    pygame.draw.lines(s,color,False,puntos,ancho)
    for p in puntos:pygame.draw.circle(s,color,p,max(1,ancho//2))


def _poligono(s,puntos,color):
    puntos=[_p(p) for p in puntos]
    pygame.draw.polygon(s,color,puntos);pygame.draw.lines(s,CONTORNO,True,puntos,1)


def _llama(s,base,cuadro,fuerza=1):
    if fuerza<=0:return
    x,y=base;p=cuadro%8
    sesgos=(-1,0,1,1,0,-1,0,1);altos=(9,11,10,8,12,10,9,11)
    alto=max(2,round(altos[p]*fuerza))
    _poligono(s,[(x-3,y),(x-4,y-4),(x+sesgos[p],y-alto),(x+1,y-5),(x+4,y-3),(x+3,y)],(255,122,26))
    pygame.draw.polygon(s,(255,179,71),[_p(q) for q in ((x-2,y),(x-1,y-5),(x+sesgos[p],y-alto+3),(x+2,y-2),(x+1,y))])
    pygame.draw.polygon(s,(255,210,122),[_p(q) for q in ((x-1,y),(x,y-5),(x+1,y))])
    if p in (1,4,6):s.set_at(_p((x+sesgos[p]*2,y-alto-2)),(255,179,71))


def cuadros_jugador(sprite,estado):
    referencia=pygame.transform.scale(sprite,(34,50))
    # Solo la cara se reutiliza como una pieza íntegra; todo el cuerpo se
    # dibuja conectado. Los huesos pequeños nunca dejan rectángulos vacíos.
    cara=referencia.subsurface((11,2,14,17)).copy()
    cantidad=18 if estado=='muerte' else 10 if estado=='ataque' else 8
    cuadros=[]
    for i in range(cantidad):
        fase=i/max(1,cantidad-1);onda=math.sin(i*math.tau/8)
        torso=onda*.8;rodilla=0;caer=0;bajar=0;retroceso=0;arma=onda*2;fuego=1
        respiracion=1 if estado=='reposo' and i in (2,3,4) else 0
        if estado=='reposo':
            # Respira el pecho; los objetos rígidos no oscilan por su cuenta.
            torso=0;arma=0
        if estado=='caminar':
            torso=onda*3;bajar=-abs(onda);arma=onda*8
        elif estado=='ataque':
            torso=(0,4,8,3,-5,-12,-10,-6,-2,0)[i]
            arma=(0,30,75,125,155,115,85,45,15,0)[i]
            bajar=2 if i in (1,2) else -1 if i in (4,5) else 0
        elif estado=='golpeado':
            impacto=math.sin(math.pi*fase);torso=impacto*12;retroceso=-impacto*2
        elif estado=='muerte':
            # Reacción, pérdida de apoyo, caída acelerada y asentamiento.
            rodilla=(0,0,.1,.3,.6,.85,1,1,.9,.8,.7,.65,.6,.6,.6,.6,.6,.6)[i]
            torso=(0,4,7,5,2,-3,-10,-20,-34,-52,-73,-88,-94,-89,-91,-90,-90,-90)[i]
            caer=max(0,min(1,(fase-.25)/.5))
            bajar=7*rodilla;arma=-12*caer
            fuego=max(0,1-max(0,fase-.45)*4)
        s=pygame.Surface((96,80),pygame.SRCALPHA)
        pelvis=(41+retroceso+3*caer,55+bajar)
        def cuerpo(x,y):
            punto=_sum(pelvis,_rotar((x-17,y-35),torso))
            return (punto[0],punto[1]-respiracion) if y<=21 else punto
        # Muslo, rodilla, pantorrilla, tobillo y bota de cada pierna.
        for lado in (-1,1):
            cadera=_sum(pelvis,(lado*2,0))
            paso=onda*12*lado if estado in ('caminar','ataque') else 0
            raiz=torso*.88 if estado=='muerte' else 0
            muslo=raiz+paso+lado*30*rodilla;espinilla=raiz-paso-lado*45*rodilla
            knee=_sum(cadera,_rotar((0,6),muslo));tobillo=_sum(knee,_rotar((0,6),espinilla))
            _miembro(s,[cadera,knee,tobillo],(90,62,39),4)
            if estado=='muerte':
                def bota(x,y):return _sum(tobillo,_rotar((x,y),raiz))
                _poligono(s,[bota(-3,-1),bota(3,-1),bota(3,4),bota(-3,4)],(58,42,29))
            else:
                pygame.draw.rect(s,CONTORNO,(*_p((tobillo[0]-3,tobillo[1]-1)),7,5))
                pygame.draw.rect(s,(58,42,29),(*_p((tobillo[0]-2,tobillo[1])),5,3))
        # Capa, cadera, torso y cuello son superficies solapadas completas.
        _poligono(s,[cuerpo(9,17),cuerpo(24,17),cuerpo(27,43),cuerpo(23,44),cuerpo(19,33),cuerpo(13,33),cuerpo(10,44),cuerpo(5,43)],CAPA)
        _poligono(s,[cuerpo(12,19),cuerpo(21,19),cuerpo(22,33),cuerpo(12,34)],(201,181,142))
        _poligono(s,[cuerpo(12,19),cuerpo(15,19),cuerpo(15,33),cuerpo(12,33)],(122,85,54))
        _poligono(s,[cuerpo(18,19),cuerpo(21,19),cuerpo(21,33),cuerpo(18,33)],(122,85,54))
        _miembro(s,[cuerpo(13,31),cuerpo(20,31)],(58,42,29),2)
        _miembro(s,[cuerpo(17,20),cuerpo(17,15)],PIEL,4)
        # Brazo de antorcha: hombro, codo y muñeca conservan continuidad.
        hombro=cuerpo(11,21);codo=cuerpo(8,25);mano=cuerpo(7,19)
        balance=0 if estado in ('reposo','muerte') else math.sin(i*math.tau/8)*.7
        if estado=='reposo':mano=(31,39)  # agarre fijo, el hombro absorbe la respiración
        codo=(codo[0]+balance,codo[1]);mano=(mano[0]+balance,mano[1])
        _miembro(s,[hombro,codo,mano],(122,85,54),4)
        pygame.draw.circle(s,PIEL,_p(mano),2)
        palo_a=_sum(mano,_rotar((0,-11),torso));palo_b=_sum(mano,_rotar((0,8),torso))
        _miembro(s,[palo_a,palo_b],(123,83,48),2)
        _llama(s,palo_a,i,fuego)
        # Brazo de espada, con flexión independiente en codo y muñeca.
        hombro=cuerpo(22,21)
        if estado=='reposo':hombro=(46,41)
        codo=_sum(hombro,_rotar((3,4),torso+arma*.55))
        mano=_sum(codo,_rotar((1,-2),torso+arma))
        _miembro(s,[hombro,codo,mano],(122,85,54),4)
        pygame.draw.circle(s,PIEL,_p(mano),2)
        angulo=torso+arma
        def espada(x,y):return _sum(mano,_rotar((x,y),angulo))
        _poligono(s,[espada(-1,3),espada(1,3),espada(1,17),espada(0,19),espada(-1,17)],(201,212,224))
        _miembro(s,[espada(-3,2),espada(3,2)],(184,134,46),1)
        # Cabeza íntegra sobre un cuello ancho, no separada por una línea de corte.
        cabeza=cuerpo(17,16)
        if estado=='muerte':
            # El pivote está en el cuello: rotar alrededor del centro de la
            # cara y pegar su midbottom separaba la cabeza al inclinarse.
            imagen=pygame.transform.rotate(cara,torso)
            centro=_sum(_sum(cabeza,_rotar((0,2),torso)),_rotar((0,-8.5),torso))
            s.blit(imagen,imagen.get_rect(center=_p(centro)))
        else:
            imagen=pygame.transform.rotate(cara,torso*.72)
            s.blit(imagen,imagen.get_rect(midbottom=_p(_sum(cabeza,(0,2)))))
        if estado=='reposo' and i==6:
            for x in (14,18):
                ojo=cuerpo(x,11);pygame.draw.line(s,(91,58,34),_p(ojo),_p(_sum(ojo,(1,0))))
        if estado=='muerte':
            # El suelo limita la caída completa, no cada parte por separado.
            # Después del contacto quedan quietos cuerpo, manos y equipo.
            limite=s.get_bounding_rect().bottom
            apoyado=pygame.Surface(s.get_size(),pygame.SRCALPHA)
            apoyado.blit(s,(0,72-limite));s=apoyado
        cuadros.append((pygame.transform.scale(s,(192,160)),(-48,-40)))
    return tuple(cuadros)


def cuadros_rata(sprite,estado):
    cantidad=10 if estado=='ataque' else 12;cuadros=[]
    for i in range(cantidad):
        fase=i/max(1,cantidad-1);onda=math.sin(i*math.tau/cantidad)
        salto=-4*math.sin(math.pi*max(0,min(1,(fase-.2)/.65))) if estado=='ataque' else 0
        respiracion=1 if i in (2,3,4,5) else 0
        s=pygame.Surface((72,44),pygame.SRCALPHA);x,y=16,12+salto
        # Cola con cinco huesos cortos; la curva llega hasta la grupa.
        puntos=[(x+26,y+13)]
        for n in range(1,6):
            puntos.append((x+26+n*1.2,y+13+n*1.3+math.sin(i*.55-n*.65)*n*.35))
        pygame.draw.lines(s,(184,134,127),False,[_p(p) for p in puntos],1)
        # Patas: muslo, corvejón y dedos apoyados bajo el cuerpo.
        for px,desfase in ((12,0),(23,math.pi)):
            avance=math.sin(i*math.tau/cantidad+desfase)*(2 if estado=='ataque' else .5)
            _miembro(s,[(x+px,y+15),(x+px+avance,y+18),(x+px-1,y+20)],(61,69,82),2)
        pygame.draw.ellipse(s,CONTORNO,pygame.Rect(x+6,y+3+respiracion,24,16))
        pygame.draw.ellipse(s,(90,99,114),pygame.Rect(x+7,y+4+respiracion,22,14))
        pygame.draw.ellipse(s,(110,120,132),pygame.Rect(x+10,y+5+respiracion,13,5))
        # Cuello y hocico se superponen al torso en todos los cuadros.
        hocico=onda*.5;hy=y+11+respiracion
        _poligono(s,[(x+1,hy+1),(x+8,hy-5),(x+14,hy-2),(x+13,hy+4),(x+4,hy+4)],(90,99,114))
        pygame.draw.ellipse(s,CONTORNO,pygame.Rect(x+7,hy-8,6,7))
        pygame.draw.ellipse(s,(184,134,127),pygame.Rect(x+8,hy-7,4,5))
        ojo=(round(x+5+hocico),round(hy-1))
        pygame.draw.line(s,(61,69,82) if estado=='reposo' and i in (9,10) else (255,59,42),ojo,(ojo[0]+1,ojo[1]))
        pygame.draw.circle(s,(184,134,127),(x+1,round(hy+1)),1)
        if estado=='ataque' and 3<=i<=6:
            pygame.draw.line(s,CONTORNO,(x+1,round(hy+3)),(x+8,round(hy+3)),2)
        pygame.draw.line(s,(232,238,245),(x+3,round(hy+3)),(x+4,round(hy+4)))
        cuadros.append((pygame.transform.scale(s,(144,88)),(-32,-24)))
    return tuple(cuadros)


def cuadros_criatura(sprite,estado):
    ancho,alto=sprite.get_size();cuadros=[]
    for i in range(8):
        alto_nuevo=max(1,alto+round(math.sin(i*math.tau/8)*2))
        cuadros.append((pygame.transform.scale(sprite,(ancho,alto_nuevo)),(0,alto-alto_nuevo)))
    return tuple(cuadros)
