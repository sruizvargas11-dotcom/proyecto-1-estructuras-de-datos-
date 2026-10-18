"""Ataques visuales FIFO: mismos eventos y tiempos producen la misma imagen.

No consulta el modelo, no usa azar y no avanza el reloj virtual.
"""
import math
import pygame
from types import SimpleNamespace
from estructuras.cola import Cola
from vista_pygame.contratos import ColaAnimaciones as ContratoAnimaciones

DURACION_ATAQUE_MS = 780


class ColaAnimaciones(ContratoAnimaciones):
    def __init__(self):
        self._cola = Cola(capacidad_maxima=128)
        self._actual = None
        self._transcurrido = 0
        self._posiciones = []
        self._id_jugador = 'jugador'
        self._tiempo_visual = 0
        self._impactos=[]
        self._golpe_emitido=False
        self._fuente = None
        self._impactos=[]
        self._golpe_emitido=False
        self._tiempo_visual = 0

    def preparar(self, posiciones):
        self._posiciones = list(posiciones)
        if self._posiciones:self._id_jugador=self._posiciones[0][0]

    def _posicion(self, instancia_id):
        for identificador, posicion in self._posiciones:
            if identificador == instancia_id:
                return posicion
        return None

    @property
    def ocupada(self):
        return self._actual is not None or len(self._cola) > 0

    def agregar_desde_eventos(self, eventos):
        for evento in eventos:
            if getattr(evento, 'tipo', None) != 'ataque':
                continue
            origen = self._posicion(evento.atacante_id)
            destino = self._posicion(evento.objetivo_id)
            if origen is not None and destino is not None:
                # Copia de datos planos: no retener un evento mutable del emisor.
                self._cola.encolar((evento.atacante_id, evento.objetivo_id,
                                    evento.dano, origen, destino,SimpleNamespace(
                                        objetivo_id=evento.objetivo_id,dano=evento.dano,
                                        vida_despues=getattr(evento,'vida_despues',None),
                                        tiempo=getattr(evento,'tiempo',None))))
        if self._actual is None:
            self._actual = self._cola.desencolar()

    def actualizar(self, dt_ms):
        self._tiempo_visual += max(0, dt_ms)
        restante = max(0, dt_ms)
        while self._actual is not None:
            falta = DURACION_ATAQUE_MS - self._transcurrido
            tramo=min(restante,falta)
            if not self._golpe_emitido and self._transcurrido+tramo>=DURACION_ATAQUE_MS*.5:
                self._impactos.append(self._actual[5]);self._golpe_emitido=True
            if restante < falta:
                self._transcurrido += restante
                break
            restante -= falta
            self._transcurrido = 0
            self._golpe_emitido=False
            self._actual = self._cola.desencolar()

    def extraer_impactos(self):
        impactos,self._impactos=self._impactos,[]
        return impactos

    def pose(self, instancia_id):
        if self._actual is None:
            return (0, 0, False)
        atacante, objetivo, _, origen, destino, _ = self._actual
        fase = self._transcurrido / DURACION_ATAQUE_MS
        if instancia_id == atacante:
            dx, dy = destino[0]-origen[0], destino[1]-origen[1]
            distancia = math.hypot(dx, dy)
            recorrido = max(0, distancia-76) / distancia if distancia else 0
            if fase < .14:
                avance=-.025*math.sin(math.pi*fase/.14)
            elif fase < .5:
                u=(fase-.14)/.36
                avance=u*u*(3-2*u)
            elif fase < .74:
                avance=1
            else:
                u=min(1,(fase-.74)/.26)
                avance=1-u*u*(3-2*u)
            paso=0
            if .14<fase<.5:paso=round(-abs(math.sin((fase-.14)/.36*math.pi*4))*1.5)
            return (round(dx*recorrido*avance), round(dy*recorrido*avance)+paso, False)
        if instancia_id == objetivo and .5 <= fase < .74:
            return (4 if int(fase*40) % 2 == 0 else -4, 0, True)
        return (0, 0, False)

    def estado_actor(self, instancia_id):
        if self._actual is not None:
            atacante,objetivo,_,_,_,_=self._actual
            fase=self._transcurrido/DURACION_ATAQUE_MS
            if instancia_id == atacante:
                if instancia_id==self._id_jugador:
                    if .14<=fase<.5:return ('caminar',min(31,int((fase-.14)/.36*32)))
                    if fase>=.74:return ('caminar',min(31,int((fase-.74)/.26*32)))
                    golpe=max(0,min(1,(fase-.5)/.24))
                    return ('ataque',min(31,round(7+golpe*20)))
                return ('ataque',min(9,int(fase*10)))
            if instancia_id == objetivo and .5<=fase<.74:
                return ('golpeado',min(7,int((fase-.5)/.24*8)))
        # Desfase estable por instancia: dos ratas no respiran al unísono.
        desfase=0 if instancia_id==self._id_jugador else sum(ord(c) for c in str(instancia_id))
        intervalo=50 if instancia_id==self._id_jugador else 120
        return ('reposo',int(self._tiempo_visual//intervalo)+desfase)

    def dibujar(self, pantalla):
        if self._actual is None:
            return
        fase = self._transcurrido / DURACION_ATAQUE_MS
        if .5 <= fase < .9:
            _, _, dano, _, (x, y), _ = self._actual
            if self._fuente is None:
                self._fuente = pygame.font.SysFont('consolas', 24, bold=True)
            # El número es el daño ya calculado por el modelo.
            texto = self._fuente.render(f'-{dano}', False, (255, 210, 122))
            pantalla.blit(texto, (x+12, y-24-round((fase-.5)*36)))
            if fase < .74:
                pygame.draw.line(pantalla, (245, 215, 122), (x+5, y+58), (x+56, y+8), 4)
                pygame.draw.line(pantalla, (232, 238, 245), (x+18, y+60), (x+62, y+20), 2)

    def limpiar(self):
        self._cola = Cola(capacidad_maxima=128)
        self._actual = None
        self._transcurrido = 0
        self._posiciones = []
        self._id_jugador = 'jugador'
        self._tiempo_visual = 0
        self._impactos=[]
        self._golpe_emitido=False
