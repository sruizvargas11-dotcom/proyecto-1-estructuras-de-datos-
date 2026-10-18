"""Párpados locales: no se desplaza ni se deforma la cara al parpadear."""
import pygame

# Ojos y muestra de piel en la cuadrícula nativa de cada personaje del menú.
OJOS = (((48,25,6,5),(56,25,4,5)),
        ((43,23,3,3),(47,22,5,4)),
        ((36,20,4,3),(46,19,4,4)),
        ((37,22,4,3),(47,21,4,4)),
        ((21,22,4,4),(31,22,5,4)))
PIEL = ((54,31),(46,26),(43,24),(44,27),(28,20))


def fase_parpadeo(tiempo,indice):
    instante=max(0,tiempo)%(5900+indice*829)
    t=instante-(3400+indice*527)
    if 0<=t<70:return 1
    if 70<=t<140:return 2
    if 140<=t<215:return 1
    return 0


def preparar_parpadeos(frames,indice,escala):
    ojos=tuple(pygame.Rect(r) for r in OJOS[indice])
    zona=ojos[0].union(ojos[1])
    destino=(round(zona.x*escala),round(zona.y*escala))
    # Redondeo compartido con la posición de sus bordes en la imagen completa.
    tamano=(max(1,round(zona.right*escala)-destino[0]),
            max(1,round(zona.bottom*escala)-destino[1]))
    resultado=[]
    for original in frames:
        fases=[]
        for fase in range(3):
            if fase==0 and indice!=1:
                fases.append(None)
                continue
            parche=pygame.Surface(zona.size,pygame.SRCALPHA)
            piel=original.get_at(PIEL[indice])
            for ojo in ojos:
                local=ojo.move(-zona.x,-zona.y)
                if indice==1:
                    # Un cráneo no tiene párpados: se apaga y reaparece un
                    # reflejo tenue dentro de sus cuencas, sin taparlas de piel.
                    if fase<2:
                        brillo=pygame.Surface((1,1),pygame.SRCALPHA)
                        brillo.fill((193,145,79,135 if fase==0 else 55))
                        parche.blit(brillo,(local.centerx,local.centery))
                    continue
                alto=local.h if fase==2 else max(1,local.h//2)
                for y in range(alto):
                    sombra=.8+.16*y/max(1,local.h-1)
                    color=tuple(round(v*sombra) for v in piel[:3])
                    pygame.draw.line(parche,color,(local.x,local.y+y),(local.right-1,local.y+y))
                if fase==2:
                    # Un pliegue de un píxel, no una banda sobre toda la cara.
                    color=tuple(round(v*.3) for v in piel[:3])
                    pygame.draw.line(parche,color,(local.x,local.centery),
                                     (local.right-1,local.centery),1)
            fases.append((pygame.transform.scale(parche,tamano),destino))
        resultado.append(tuple(fases))
    return tuple(resultado)
