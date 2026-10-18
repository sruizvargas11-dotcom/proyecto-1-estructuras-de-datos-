"""Criaturas en ocho poses completas: cuatro de reposo y cuatro de ataque."""
import pygame


class CriaturaDibujada:
    def __init__(self,ruta):
        hoja=pygame.image.load(str(ruta)).convert_alpha();w,h=hoja.get_size()
        figuras=[]
        for n in range(8):
            x0,y0=round(n%4*w/4),round(n//4*h/2)
            celda=hoja.subsurface((x0,y0,round((n%4+1)*w/4)-x0,round((n//4+1)*h/2)-y0)).copy()
            mascara=pygame.mask.from_surface(celda,100).connected_component()
            limpia=pygame.Surface(celda.get_size(),pygame.SRCALPHA)
            mascara.to_surface(surface=limpia,setsurface=celda,unsetcolor=(0,0,0,0))
            figuras.append(limpia.subsurface(limpia.get_bounding_rect(min_alpha=100)).copy())
        factor=84/max(im.get_height() for im in figuras[:4])
        self.poses=[]
        for figura in figuras:
            # Cuadrícula de dos píxeles, igual que los demás actores de la sala.
            im=pygame.transform.scale(figura,(max(1,round(figura.get_width()*factor/2)),max(1,round(figura.get_height()*factor/2))))
            im=pygame.transform.scale(im,(im.get_width()*2,im.get_height()*2))
            pies=[x for y in range(im.get_height()-3,im.get_height()) for x in range(im.get_width()) if im.get_at((x,y)).a>100]
            frame=pygame.Surface((224,160),pygame.SRCALPHA)
            frame.blit(im,(112-round(sum(pies)/len(pies)),128-im.get_height()))
            self.poses.append(frame)
        self.base=pygame.transform.scale(self.poses[0].subsurface(self.poses[0].get_bounding_rect()),(68,86))
        self._reposo=tuple((self.poses[min(3,i//6)],(-78,-42)) for i in range(24))
        self._ataque=tuple((self.poses[4+min(3,round(i/3))],(-78,-42)) for i in range(10))

    def fotograma(self,estado,cuadro):
        frames=self._ataque if estado=='ataque' else self._reposo
        return frames[cuadro%len(frames)]


def familia_criatura(tipo,rol):
    for palabra,familia in (('guardian','guardian'),('guardia','guardian'),
                            ('esqueleto','esqueleto'),('skeleton','esqueleto'),
                            ('necrofago','necrofago'),('ghoul','necrofago'),
                            ('trasgo','trasgo'),('goblin','trasgo'),('errante','errante')):
        if palabra in tipo:return familia
    if rol=='guardian':return 'guardian'
    if rol=='errante':return 'errante'
    if rol=='rastreador':return 'necrofago'
    return 'generico'
