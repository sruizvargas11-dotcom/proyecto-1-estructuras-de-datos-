"""Temas por cripta, persistencia visual y aislamiento entre partidas HTTP."""
from pathlib import Path
from types import SimpleNamespace
import pygame
import pytest
from vista_pygame.recursos.temas_cripta import TEMAS,tema_por_cripta,tema_estado
from vista_pygame.recursos.cargador_assets import CargadorAssets
from vista_pygame.render.entrada_cripta import EntradaCripta
from vista_pygame.render.victoria_cripta import SalidaCripta
from vista_pygame.render.escenografia_sala import dibujar_escenario
from vista_pygame.render.cinematica_trampa import EfectoTrampa
from vista_pygame.controlador_pygame import SalidaVisual,ControladorPygame


@pytest.mark.parametrize('numero',range(1,5))
def test_tema_en_entrada_sala_trampa_y_victoria(numero):
    pygame.init();pygame.display.set_mode((1,1));assets=CargadorAssets()
    id=f'cripta-{numero:02}';tema=TEMAS[numero-1]
    assert tema_por_cripta(id)==tema
    estado=SimpleNamespace(cripta_id=id,cripta_nombre=tema.titulo,sala_id=1,es_sala_salida=False,
                           salidas=[SalidaVisual('N',2,'Sala 2',True,False,'llave')],
                           inventario=[],arma_equipada='',armadura_equipada='')
    imagen=pygame.Surface((760,470));pantalla=pygame.Surface((1280,720))
    for tipo in ('sala','final','entrada','exterior'):
        ruta=tema.recurso(assets.carpeta,tipo)
        assert ruta.is_file()
        if numero>1:assert tema.clave in str(ruta)
    assert dibujar_escenario(imagen,assets,estado,imagen.get_rect(),0,None)
    antes=pygame.image.tobytes(imagen,'RGB')
    estado.es_sala_salida=True;dibujar_escenario(imagen,assets,estado,imagen.get_rect(),0,None)
    assert antes!=pygame.image.tobytes(imagen,'RGB')
    entrada=EntradaCripta(None,id,tema.titulo);entrada.actualizar(2000);entrada.dibujar(pantalla,assets)
    assert entrada.tema==tema
    victoria=SalidaCripta(assets,0,pantalla,id,tema.titulo)
    victoria.actualizar(5200);victoria.dibujar(pantalla,assets)
    assert victoria.tema==tema and victoria.terminada
    trampa=EfectoTrampa();trampa.iniciar('Dardos',estado=estado)
    trampa.actualizar(700);trampa.dibujar(pantalla,assets)
    assert trampa.tema==tema


def test_cache_no_mezcla_los_fondos_al_cambiar_de_cripta():
    pygame.init();pygame.display.set_mode((1,1));assets=CargadorAssets();vistos=[]
    for n in (1,2,3,4,1):
        estado=SimpleNamespace(cripta_id=f'cripta-{n:02}',sala_id=1,salidas=[],es_sala_salida=False)
        im=pygame.Surface((760,470));dibujar_escenario(im,assets,estado,im.get_rect(),0,None)
        vistos.append(pygame.image.tobytes(im,'RGB'))
    assert vistos[0]==vistos[-1] and len(set(vistos[:4]))==4


def test_criptas_futuras_tienen_tema_estable_y_se_reconoce_el_nombre():
    assert tema_por_cripta('nueva','Osario de los Reyes')==TEMAS[0]
    assert tema_por_cripta('nueva','CATACUMBAS PROFUNDAS')==TEMAS[3]
    assert tema_por_cripta('nueva','Catacumbas medias')==TEMAS[2]
    assert tema_estado(SimpleNamespace(cripta_id='futura-sin-descripcion'))==tema_por_cripta('futura-sin-descripcion')
    assert tema_estado(None)==TEMAS[0]


def test_cliente_http_nuevo_conserva_metricas_del_anterior(tmp_path):
    from adaptadores.datos_http import DatosHTTP
    fuente=DatosHTTP(max_reintentos=2);fuente._contador=9;fuente._presupuesto=9
    c=ControladorPygame(fuente,partidas_dir=str(tmp_path))
    c._fuente_usada=True
    c._hilo=object();c._preparar_fuente_nueva_partida()
    assert c._fuente is fuente  # Nunca reiniciar un presupuesto en una partida activa.
    c._hilo=None;c._preparar_fuente_nueva_partida()
    assert c._fuente is not fuente and c._fuente.requests_realizados==0
    assert fuente.requests_realizados==9 and fuente.presupuesto==9
    assert c._fuente._client_id==fuente._client_id and c._fuente._max_reintentos==2
    nuevo=c._fuente;c._preparar_fuente_nueva_partida();assert c._fuente is nuevo
