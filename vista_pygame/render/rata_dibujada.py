"""Rata pixel art en poses completas, con un único registro de patas y cola."""
import pygame


class RataDibujada:
    def __init__(self,ruta):
        atlas=pygame.image.load(str(ruta)).convert_alpha();w,h=atlas.get_size();poses=[]
        for n in range(16):
            x0,y0=round(n%4*w/4),round(n//4*h/4)
            im=atlas.subsurface((x0,y0,round((n%4+1)*w/4)-x0,round((n//4+1)*h/4)-y0)).copy()
            # Algunas colas cruzan la cuadrícula del atlas: descartar los
            # fragmentos del vecino antes de recortar y calcular la escala.
            figura=pygame.mask.from_surface(im,100).connected_component()
            limpia=pygame.Surface(im.get_size(),pygame.SRCALPHA)
            figura.to_surface(surface=limpia,setsurface=im,unsetcolor=(0,0,0,0))
            poses.append(limpia.subsurface(limpia.get_bounding_rect(min_alpha=100)).copy())
        factor=min(124/max(im.get_width() for im in poses),43/max(im.get_height() for im in poses))
        self.poses=[]
        for original in poses:
            mini=pygame.transform.scale(original,(max(1,round(original.get_width()*factor/2)),max(1,round(original.get_height()*factor/2))))
            mini=pygame.transform.scale(mini,(mini.get_width()*2,mini.get_height()*2))
            puntos=[x for y in range(max(0,mini.get_height()-4),mini.get_height()) for x in range(mini.get_width()) if mini.get_at((x,y)).a>100]
            centro=round(sum(puntos)/len(puntos))
            frame=pygame.Surface((160,88),pygame.SRCALPHA)
            frame.blit(mini,(66-centro,64-mini.get_height()))
            self.poses.append(frame)
        self._reposo=tuple((self.poses[i//3],(-32,-24)) for i in range(24))
        self._ataque=tuple((self.poses[8+min(7,i*8//10)],(-32,-24)) for i in range(10))
        self.base=pygame.transform.scale(self.poses[0].subsurface(self.poses[0].get_bounding_rect()),(68,40))

    def fotograma(self,estado,cuadro):
        frames=self._ataque if estado=='ataque' else self._reposo
        return frames[cuadro%len(frames)]
