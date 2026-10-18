"""Primer plano desde atrás: representa daño ya decidido por el modelo."""
import math
import unicodedata
from pathlib import Path
import pygame
from vista_pygame.render.heroe_equipo import clave_equipo
from vista_pygame.recursos.temas_cripta import tema_estado
from vista_pygame.render.fuego_pixel import cargar_llamas


def familia_trampa(nombre, tipos=()):
    texto=' '.join((nombre, *tipos)).casefold()
    texto=''.join(c for c in unicodedata.normalize('NFD',texto) if unicodedata.category(c)!='Mn')
    grupos=(('dardos',('dardo','flecha','proyectil')),
            ('pinchos',('pincho','clavo','pua','estaca','spike')),
            ('gas',('veneno','gas','toxic')),
            ('fuego',('fuego','llama','lava','brasas')),
            ('hielo',('hielo','escarcha','congel')),
            ('rocas',('roca','techo','aplast','piedra')),
            ('electricidad',('electric','rayo','descarga')))
    return next((grupo for grupo,palabras in grupos if any(p in texto for p in palabras)),'mecanismo')


class EfectoTrampa:
    DURACION=1900
    IMPACTO=950

    def __init__(self):
        self.tiempo=self.DURACION;self.texto='';self.evento=None
        self._impactos=[];self._aplicado=False;self.equipo=0
        self.familia='mecanismo';self._fondo=None;self._fuegos=None
        self.tema=tema_estado(None)

    @property
    def activa(self):return self.tiempo<self.DURACION

    def iniciar(self,texto,evento=None,estado=None):
        self.tiempo=0;self.texto=texto;self.evento=evento
        self._impactos=[];self._aplicado=False
        self.equipo=clave_equipo(estado) if estado is not None else 0
        tema=tema_estado(estado)
        if tema!=self.tema:self._fondo=None
        self.tema=tema
        self.familia=familia_trampa(getattr(evento,'nombre',texto),getattr(evento,'tipos',()))

    def actualizar(self,dt):
        self.tiempo=min(self.DURACION,self.tiempo+max(0,dt))
        if self.evento is not None and not self._aplicado and self.tiempo>=self.IMPACTO:
            self._impactos.append(self.evento);self._aplicado=True

    def extraer_impactos(self):
        impactos,self._impactos=self._impactos,[]
        return impactos

    def _recursos(self,assets):
        if self._fondo is not None:return
        carpeta=getattr(assets,'carpeta',Path(__file__).resolve().parents[2]/'assets')
        self._fondo=pygame.transform.scale(pygame.image.load(str(self.tema.recurso(carpeta,'sala'))).convert(),(640,360))
        self._fondo.fill((135,145,158),special_flags=pygame.BLEND_RGB_MULT)
        self._fuegos=cargar_llamas(30,74)

    def _peligro(self,capa,u):
        familia=self.familia
        # Los elementos avanzan desde el fondo de la sala hacia los pies del
        # personaje; u=1 es el contacto, nunca una oportunidad de esquiva.
        avance=max(0,min(1,u))
        if familia=='dardos':
            for i in range(4):
                lado=-1 if i%2==0 else 1
                inicio=320+lado*260
                x=round(inicio+(320-inicio)*avance)
                y=round(130+i*17+(242-(130+i*17))*avance)
                pygame.draw.ellipse(capa,(6,10,15),(inicio-10,125+i*17,20,10))
                pygame.draw.line(capa,(82,50,27),(x+lado*34,y-5),(x,y),3)
                pygame.draw.polygon(capa,(178,191,194),((x,y),(x+lado*10,y-5),(x+lado*8,y+5)))
                pygame.draw.line(capa,(217,225,220),(x,y),(x+lado*8,y-4),1)
        elif familia in ('pinchos','hielo'):
            for fila in range(3):
                profundidad=max(0,min(1,avance-fila*.1))
                cy=round(188+profundidad*119+fila*4)
                ancho=round(38+profundidad*100)
                pygame.draw.ellipse(capa,(7,12,17),(320-ancho,cy-6,ancho*2,17))
                for j in range(-2,3):
                    x=320+j*ancho//3;alto=round((12+profundidad*55)*max(0,min(1,avance*2)))
                    color=(107,140,157) if familia=='hielo' else (82,94,104)
                    pygame.draw.polygon(capa,(17,25,33),((x-9,cy),(x,cy-alto-3),(x+11,cy+1)))
                    pygame.draw.polygon(capa,color,((x-6,cy),(x,cy-alto),(x+2,cy)))
                    pygame.draw.line(capa,(203,220,225),(x,cy-alto),(x+1,cy-2),1)
        elif familia=='fuego':
            for j in range(5):
                x=250+j*37;y=round(193+avance*113)
                im=self._fuegos[(self.tiempo//60+j*2)%len(self._fuegos)]
                alto=max(2,round(im.get_height()*avance))
                im=pygame.transform.scale(im,(30,alto))
                capa.blit(im,im.get_rect(midbottom=(x,y)))
        elif familia=='gas':
            humo=pygame.Surface(capa.get_size(),pygame.SRCALPHA)
            for i in range(28):
                angulo=i*2.4+self.tiempo*.002
                radio=30+(i%5)*17
                x=320+round(math.cos(angulo)*radio)
                y=round(270-avance*70+math.sin(angulo*.8)*25)
                pygame.draw.circle(humo,(74+i%3*12,111+i%4*9,47,round(75*avance)),(x,y),10+i%6*3)
            capa.blit(humo,(0,0))
        elif familia=='rocas':
            for i in range(5):
                x=250+i*35;y=round(-30+avance*285)+i%2*11
                pygame.draw.polygon(capa,(10,15,21),((x-18,y-14),(x+11,y-21),(x+24,y+4),(x+6,y+22),(x-22,y+9)))
                pygame.draw.polygon(capa,(87,91,98),((x-15,y-13),(x+9,y-18),(x+18,y+2),(x+4,y+17)))
                pygame.draw.line(capa,(124,132,139),(x-15,y-13),(x+9,y-18),2)
        elif familia=='electricidad':
            for lado in (-1,1):
                puntos=[(320+lado*230,150)]
                for i in range(1,9):
                    x=round(320+lado*(230-i*28*avance));y=150+i*11+round(math.sin(i*3+self.tiempo*.04)*13)
                    puntos.append((x,y))
                pygame.draw.lines(capa,(71,99,161),False,puntos,7)
                pygame.draw.lines(capa,(185,221,250),False,puntos,2)
        else:
            # Ficha desconocida: mostrar presión y fragmentos de mecanismo,
            # sin fingir que sabemos qué trampa describe el catálogo.
            ancho=round(100+avance*110)
            pygame.draw.ellipse(capa,(13,18,25),(320-ancho//2,280,ancho,24),4)
            for i in range(8):
                x=320+round(math.cos(i*.79)*avance*90);y=293+round(math.sin(i*.79)*avance*20)
                pygame.draw.rect(capa,(91,100,106),(x,y-8,5,8))

    def dibujar(self,pantalla,assets):
        if not self.activa:return
        self._recursos(assets)
        capa=self._fondo.copy()
        t=self.tiempo
        avance=max(0,min(1,(t-250)/(self.IMPACTO-250)))
        self._peligro(capa,avance)
        heroe=(assets.sprite_espalda_equipo(self.equipo) if hasattr(assets,'sprite_espalda_equipo')
               else assets.sprite_jugador('parado','S'))
        alto=124 if self.equipo&2 else 100
        factor=alto/heroe.get_height()
        heroe=pygame.transform.scale(heroe,(max(1,round(heroe.get_width()*factor)),alto))
        sacudida=max(0,1-abs(t-self.IMPACTO)/280)
        if sacudida:
            heroe=pygame.transform.rotate(heroe,round(-5*sacudida))
        pygame.draw.ellipse(capa,(7,10,15),(283,296,74,14))
        capa.blit(heroe,heroe.get_rect(midbottom=(320+round(3*sacudida),303)))
        if t>=self.IMPACTO and sacudida:
            rojo=pygame.Surface((640,360),pygame.SRCALPHA);rojo.fill((104,12,18,round(72*sacudida)))
            capa.blit(rojo,(0,0))
        grande=pygame.transform.scale(capa,pantalla.get_size())
        titulo=assets.fuente(32).render('TRAMPA ACTIVADA',False,(224,190,140))
        grande.blit(titulo,titulo.get_rect(center=(640,55)))
        nombre=getattr(self.evento,'nombre','Mecanismo oculto')
        texto=assets.fuente(24).render(nombre,False,(220,220,210))
        grande.blit(texto,texto.get_rect(center=(640,95)))
        if self.evento is not None:
            golpe=t>=self.IMPACTO
            vida=self.evento.vida_despues if golpe else self.evento.vida_antes
            aviso=f'-{self.evento.dano} de vida' if golpe else '¡Un chasquido a tus espaldas!'
            texto=assets.fuente(26).render(aviso,False,(247,139,116) if golpe else (191,182,156))
            grande.blit(texto,texto.get_rect(center=(640,650)))
            if vida is not None:
                texto=assets.fuente(20).render(f'Vida: {vida}',False,(230,224,208))
                grande.blit(texto,texto.get_rect(center=(640,682)))
        alpha=min(1,t/180,(self.DURACION-t)/260)
        grande.set_alpha(round(max(0,alpha)*255))
        pantalla.blit(grande,(0,0))
