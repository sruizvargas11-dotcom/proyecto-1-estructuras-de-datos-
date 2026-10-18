"""Caída y fundidos visuales de muerte, con tiempos fijos y sin azar."""
import pygame
from vista_pygame.render.rig_actores import cuadros_jugador

DURACION_CAIDA_MS = 1050
INICIO_FUNDIDO_MS = 600
FIN_FUNDIDO_MS = 1550
INICIO_TEXTO_MS = 1450
DURACION_MUERTE_MS = 2300


class AnimacionMuerte:
    def __init__(self, fondo, sprite, posicion, cuadros=None):
        self._tiempo = 0
        self._fondo = fondo.copy()
        self._posicion = posicion
        # Se generan una vez; durante el render solo se selecciona un cuadro.
        self._caida = cuadros if cuadros is not None else cuadros_jugador(sprite,'muerte')
        self._sombra = pygame.Surface(fondo.get_size()).convert()
        self._sombra.fill((24, 0, 4))

    @property
    def terminada(self):
        return self._tiempo >= DURACION_MUERTE_MS

    @property
    def opacidad_menu(self):
        fase = max(0, min(1, (self._tiempo-INICIO_TEXTO_MS)/(DURACION_MUERTE_MS-INICIO_TEXTO_MS)))
        return round(255*fase)

    @property
    def opacidad_fondo(self):
        fase = max(0, min(1, (self._tiempo-INICIO_FUNDIDO_MS)/(FIN_FUNDIDO_MS-INICIO_FUNDIDO_MS)))
        return round(210*fase)

    @property
    def cuadro(self):
        fase = min(1, self._tiempo/DURACION_CAIDA_MS)
        return min(len(self._caida)-1, int(fase*(len(self._caida)-1)))

    def actualizar(self, dt_ms):
        self._tiempo = min(DURACION_MUERTE_MS, self._tiempo+max(0,dt_ms))

    def dibujar(self, pantalla):
        pantalla.blit(self._fondo,(0,0))
        imagen,offset = self._caida[self.cuadro]
        pantalla.blit(imagen,(self._posicion[0]+offset[0],self._posicion[1]+offset[1]))
        self._sombra.set_alpha(self.opacidad_fondo)
        pantalla.blit(self._sombra,(0,0))
