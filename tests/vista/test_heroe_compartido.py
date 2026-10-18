import pygame
import pytest
from vista_pygame.render.heroe_compartido import HeroeCompartido, heroe_compartido
from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.render.portada_animada import PortadaAnimada
from vista_pygame.render.animaciones import ColaAnimaciones, DURACION_ATAQUE_MS
from vista_pygame.render.ojo_torre import cargar_ojo, cuadro_ojo
from vista_pygame.controlador_pygame import EventoAtaque


def test_partida_y_muerte_usan_las_imagenes_cargadas_del_atlas():
    h=heroe_compartido();a=CargadorAssets()
    for i,im in enumerate(h.cuadros('reposo')):
        assert a.fotograma_jugador('reposo',i)[0] is im
    for i,(im,_) in enumerate(a.cuadros_muerte()):
        assert im is h.cuadros('muerte')[i]


@pytest.mark.parametrize('estado,fila,cantidad',[('reposo',0,48),('ataque',1,32),('muerte',2,48)])
def test_se_reproducen_ocho_dibujos_completos_sin_articular_ni_recortar(estado,fila,cantidad):
    h=heroe_compartido();frames=h.cuadros(estado)
    assert len(frames)==cantidad
    assert len({id(im) for im in frames})==8
    for im in frames:
        assert any(im is fuente for fuente in h._dibujados[fila])
        rect=im.get_bounding_rect()
        assert rect.left>0 and rect.right<im.get_width()
        assert rect.bottom==160
        areas=[c.count() for c in pygame.mask.from_surface(im).connected_components()]
        assert max(areas)/sum(areas)>.94


def test_correciones_de_equipo_son_archivos_de_poses_completas():
    a=CargadorAssets();h=heroe_compartido()
    for fila,columna,nombre in ((1,1,'ataque_anticipacion.png'),(2,3,'muerte_transicion.png')):
        im=pygame.image.load(str(a.carpeta/'sprites/jugador'/nombre))
        assert im.get_bounding_rect().w>100
        assert h._poses[fila][columna].get_bounding_rect().w>100


def test_reproducir_no_rota_ni_reconstruye_el_cuerpo(monkeypatch):
    h=HeroeCompartido()
    def prohibido(*args,**kwargs):pytest.fail('Reconstruyó un personaje ya dibujado')
    monkeypatch.setattr(pygame.image,'load',prohibido)
    monkeypatch.setattr(pygame.transform,'rotate',prohibido)
    monkeypatch.setattr(pygame.transform,'scale',prohibido)
    for estado in ('reposo','ataque','muerte'):
        for im in h.cuadros(estado):assert isinstance(im,pygame.Surface)


def test_caida_termina_horizontal_y_quieta():
    c=heroe_compartido().cuadros('muerte')
    assert c[-1].get_bounding_rect().width>c[-1].get_bounding_rect().height*2
    assert c[-1] is c[-2]


def test_heroe_de_portada_respira_como_los_bichos_con_equipo_y_pies_fijos():
    p=PortadaAnimada();p.ajustar((1280,720))
    frames=p._capas[0][0]
    assert len(frames)==48
    assert len(set(p._capas[0][1]))==1
    assert pygame.image.tobytes(frames[0],'RGBA')!=pygame.image.tobytes(frames[12],'RGBA')
    # Cabeza, espada, mango y apoyo al suelo permanecen en su sitio.
    for rect in ((34,16,28,18),(47,33,11,4),(0,54,94,40),(72,0,22,54)):
        equipo=pygame.image.tobytes(frames[0].subsurface(rect),'RGBA')
        assert all(pygame.image.tobytes(im.subsurface(rect),'RGBA')==equipo for im in frames)
    for hombro in ((17,32,12,18),(52,40,16,12)):
        antes=pygame.image.tobytes(frames[0].subsurface(hombro),'RGBA')
        assert pygame.image.tobytes(frames[12].subsurface(hombro),'RGBA')!=antes
        assert pygame.image.tobytes(frames[36].subsurface(hombro),'RGBA')!=antes
    for frames,_ in p._capas[1:]:
        assert len(frames)==48
        for im in frames:
            rect=im.get_bounding_rect()
            assert rect.left>=4 and rect.right<im.get_width()-3 and rect.bottom==92


def test_identificador_del_jugador_puede_ser_personalizado():
    c=ColaAnimaciones();c.preparar([('heroe-17',(100,100)),('rata',(300,100))])
    c.agregar_desde_eventos([EventoAtaque(atacante_id='heroe-17',objetivo_id='rata',dano=1)])
    c.actualizar(round(DURACION_ATAQUE_MS*.6))
    estado,cuadro=c.estado_actor('heroe-17')
    assert estado=='ataque' and 0<=cuadro<32


def test_ojo_parpadea_y_vuelve_a_abrirse_sin_aplastar_las_imagenes():
    frames=cargar_ojo()
    assert len(frames)==8 and len({f.get_size() for f in frames})==1
    assert cuadro_ojo(0)==0 and cuadro_ojo(5400+160)==4
    assert cuadro_ojo(5720)==0
    assert cuadro_ojo(12300+160)==4 and cuadro_ojo(12620)==0
    assert pygame.image.tobytes(frames[0],'RGBA')!=pygame.image.tobytes(frames[4],'RGBA')


def test_craneo_del_esqueleto_queda_nitido_y_quieto_al_respirar():
    p=PortadaAnimada();frames=p._capas[1][0]
    w=frames[0].get_width()
    cabeza=pygame.image.tobytes(frames[0].subsurface((0,0,w,35)),'RGBA')
    assert all(pygame.image.tobytes(im.subsurface((0,0,w,35)),'RGBA')==cabeza for im in frames)
    assert pygame.image.tobytes(frames[0],'RGBA')!=pygame.image.tobytes(frames[12],'RGBA')
