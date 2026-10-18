"""Equipo visible y combustible real; nunca simula desgaste en la vista."""
import pygame
from vista_pygame.config_vista import COLOR_TEXTO, COLOR_TEXTO_TENUE, COLOR_ORO
from vista_pygame.render.panel_mazmorra import PanelMazmorra


class PanelEquipo:
    RECT=pygame.Rect(974,220,292,178)

    def __init__(self):self._panel=PanelMazmorra()

    @staticmethod
    def ranuras(estado):
        arma=next((o for o in estado.inventario if o.clase=='arma' and o.equipado),None)
        armadura=next((o for o in estado.inventario if o.clase=='armadura' and o.equipado),None)
        antorchas=[o for o in estado.inventario if o.clase=='antorcha']
        antorcha=next((o for o in antorchas if o.encendida),None)
        if antorcha is None:
            antorcha=next((o for o in antorchas if not o.agotada),antorchas[0] if antorchas else None)
        return (('Arma',arma),('Armadura',armadura),('Luz',antorcha))

    @staticmethod
    def barra(pantalla,rect,restante,total,color=(222,151,51)):
        pygame.draw.rect(pantalla,(9,14,20),rect)
        fraccion=max(0,min(1,restante/max(1,total)))
        ancho=round((rect.w-2)*fraccion)
        if ancho:pygame.draw.rect(pantalla,color,(rect.x+1,rect.y+1,ancho,rect.h-2))
        pygame.draw.rect(pantalla,(87,91,92),rect,1)

    @staticmethod
    def texto(pantalla,assets,valor,pos,tamano=12,color=COLOR_TEXTO,ancho=238):
        fuente=assets.fuente(tamano);valor=str(valor)
        while fuente.size(valor)[0]>ancho and len(valor)>1:valor=valor[:-2]+'…'
        pantalla.blit(fuente.render(valor,False,color),pos)

    def dibujar(self,pantalla,assets,estado):
        r=self.RECT;self._panel.dibujar(pantalla,r)
        self.texto(pantalla,assets,'Equipo y luz',(r.x+12,r.y+9),14,COLOR_ORO)
        for i,(tipo,objeto) in enumerate(self.ranuras(estado)):
            y=r.y+31+i*47
            pygame.draw.line(pantalla,(43,50,59),(r.x+10,y-4),(r.right-10,y-4))
            if objeto is None:
                self.texto(pantalla,assets,f'{tipo}: sin equipar' if tipo!='Luz' else 'Luz: sin antorcha',
                           (r.x+12,y+8),12,COLOR_TEXTO_TENUE)
                continue
            im=assets.sprite_objeto(objeto.tipo_id,objeto.clase)
            factor=min(31/im.get_width(),34/im.get_height())
            im=pygame.transform.scale(im,(max(1,round(im.get_width()*factor)),max(1,round(im.get_height()*factor))))
            pantalla.blit(im,im.get_rect(center=(r.x+25,y+17)))
            x=r.x+46
            self.texto(pantalla,assets,objeto.nombre,(x,y),13,ancho=234)
            if objeto.clase=='antorcha':
                restante=getattr(objeto,'tiempo_restante',None)
                duracion=getattr(objeto,'duracion',0)
                estado_luz='Encendida' if objeto.encendida else 'Agotada' if objeto.agotada else 'Apagada'
                dato=f'{estado_luz} · {restante}/{duracion} ut' if restante is not None else estado_luz
                self.texto(pantalla,assets,dato,(x,y+15),11,COLOR_TEXTO_TENUE)
                if restante is not None:self.barra(pantalla,pygame.Rect(x,y+32,136,6),restante,duracion)
                self.texto(pantalla,assets,f'P{objeto.peso} · V{objeto.valor}',(x+145,y+28),10,COLOR_TEXTO_TENUE,ancho=85)
            else:
                bonus=(f'Ataque +{objeto.ataque_bonus}' if objeto.clase=='arma' else f'Defensa +{objeto.defensa_bonus}')
                self.texto(pantalla,assets,f'{bonus} · Peso {objeto.peso} · Valor {objeto.valor}',(x,y+15),11)
                self.texto(pantalla,assets,'Sin desgaste',(x,y+29),10,COLOR_TEXTO_TENUE)
