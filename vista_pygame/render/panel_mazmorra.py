"""Paneles de basalto y hierro; texturas deterministas cacheadas."""
import pygame


class PanelMazmorra:
    def __init__(self):
        self._cache=[]

    def dibujar(self,pantalla,rect,seleccionada=False):
        clave=(rect.size,seleccionada)
        for k,imagen in self._cache:
            if k==clave:
                pantalla.blit(imagen,(rect.x-7,rect.y-5));return
        w,h=rect.size
        im=pygame.Surface((w+14,h+16),pygame.SRCALPHA)
        r=pygame.Rect(7,5,w,h);corte=min(9,max(3,h//7))
        def poligono(z,c):
            return [(z.x+c,z.y),(z.right-c,z.y),(z.right,z.y+c),
                    (z.right,z.bottom-c),(z.right-c,z.bottom),
                    (z.x+c,z.bottom),(z.x,z.bottom-c),(z.x,z.y+c)]
        for n in range(6,0,-1):
            pygame.draw.polygon(im,(4,8,14,25+(6-n)*17),poligono(r.move(0,n+2).inflate(n,n),corte))
        pygame.draw.polygon(im,(74,78,82),poligono(r,corte))
        dentro=r.inflate(-12,-12)
        pygame.draw.polygon(im,(22,29,39),poligono(dentro,max(1,corte-2)))
        # Fisuras en grandes bloques de piedra, sin atravesar los bordes.
        for yy in range(24,h-8,28):
            pygame.draw.line(im,(12,18,25),(16,yy),(w-6,yy),1)
            for xx in range(27+(yy//28%2)*37,w-10,74):
                pygame.draw.line(im,(12,18,25),(xx,yy-26),(xx+2,yy),1)
        # Óxido por manchas irregulares sobre el hierro, nunca un marco naranja.
        for xx in range(9,w+4,3):
            for yy in (7,8,h+1,h+2):
                v=(xx*37+yy*73+xx*yy)%41
                if v<13:
                    pygame.draw.rect(im,(70+v*2,39+v,23),(xx,yy,2+v%3,1+v%2))
        for yy in range(12,h-3,4):
            for xx in (9,w+1):
                v=(xx*11+yy*43)%17
                if v<6:pygame.draw.rect(im,(92,51+v,28),(xx,yy,2,3))
        # Piedra irregular de poco contraste; el centro queda limpio para leer.
        for y in range(7,h-5,3):
            for x in range(7,w-5,4):
                v=(x*73+y*37+x*y*3)%29
                if v<5:
                    im.set_at((r.x+x,r.y+y),(25+v,33+v,44+v,255))
        pygame.draw.lines(im,(96,106,119),False,
            [(r.x+corte,r.y+1),(r.right-corte,r.y+1),(r.right-2,r.y+corte)],1)
        pygame.draw.lines(im,(9,14,23),False,
            [(r.x+1,r.y+corte),(r.x+1,r.bottom-corte),(r.x+corte,r.bottom-1),(r.right-corte,r.bottom-1)],2)
        pygame.draw.polygon(im,(8,14,23),poligono(dentro.inflate(-4,-4),max(1,corte-3)),1)
        # Escuadras remachadas de hierro viejo, comunes a todos los paneles.
        for x,y,sx,sy in ((r.x,r.y,1,1),(r.right,r.y,-1,1),
                           (r.x,r.bottom,1,-1),(r.right,r.bottom,-1,-1)):
            pygame.draw.lines(im,(106,92,67),False,
                [(x+sx*3,y+sy*14),(x+sx*3,y+sy*7),(x+sx*9,y+sy*3),(x+sx*18,y+sy*3)],2)
            pygame.draw.circle(im,(13,18,26),(x+sx*8,y+sy*8),3)
            pygame.draw.circle(im,(118,127,137),(x+sx*8,y+sy*8),1)
        if seleccionada:
            pygame.draw.polygon(im,(191,150,68),poligono(r.inflate(-2,-2),corte),1)
            # Dos marcas rúnicas, fuera de la zona de texto.
            for x,sx in ((r.x-3,1),(r.right+3,-1)):
                cy=r.centery
                pygame.draw.lines(im,(230,185,93),False,
                    [(x,cy-7),(x+sx*4,cy),(x,cy+7)],2)
        if len(self._cache)>=32:self._cache.clear()
        self._cache.append((clave,im))
        pantalla.blit(im,(rect.x-7,rect.y-5))
