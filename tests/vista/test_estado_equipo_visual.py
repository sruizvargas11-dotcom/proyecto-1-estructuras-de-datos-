"""Los datos del panel proceden de los objetos y del reloj virtual."""
import pytest
from tests.test_equipo_interactivo import jugar
from tests.vista.test_cinematica_cripta import app
from controlador.controlador_pygame import construir_estado
from vista_pygame.render.panel_equipo import PanelEquipo


@pytest.mark.parametrize('comandos,encendida,agotada',[
    (['R 1'],False,False),
    (['R 1','U 1'],True,False),
    (['R 1','U 1','AP 1'],False,False),
    (['R 1','U 1']+['W']*40,False,True),
])
def test_combustible_nuevo_encendido_apagado_y_agotado(tmp_path,comandos,encendida,agotada):
    c,_,_=jugar(tmp_path,comandos)
    foto=construir_estado(c.partida)
    objeto=foto.inventario[0]
    real=c.partida.jugador.inventario.head().valor
    assert objeto.encendida==encendida and objeto.agotada==agotada
    assert objeto.duracion==real.duracion
    if len(comandos)==1:assert objeto.tiempo_restante==real.duracion
    elif agotada:assert objeto.tiempo_restante==0
    else:assert objeto.tiempo_restante==real.evento_apagado.tiempo-foto.tiempo
    # Consultar y seleccionar ranuras no gasta combustible ni modifica el modelo.
    antes=(real.encendida,real.usos_restantes,c.partida.tiempo)
    assert PanelEquipo.ranuras(foto)[2][1] is objeto
    construir_estado(c.partida)
    assert antes==(real.encendida,real.usos_restantes,c.partida.tiempo)


def test_panel_muestra_bonus_reales_y_equipo_actual(tmp_path):
    c,_,_=jugar(tmp_path,['R 1','U 1','R 1','EQ 2','R 1','EQ 3'])
    foto=construir_estado(c.partida)
    arma,armadura,luz=[o for _,o in PanelEquipo.ranuras(foto)]
    assert arma.ataque_bonus==c.partida.jugador.arma_equipada.ataque_bonus
    assert armadura.defensa_bonus==c.partida.jugador.armadura_equipada.defensa_bonus
    assert arma.peso==c.partida.jugador.arma_equipada.peso
    assert armadura.valor==c.partida.jugador.armadura_equipada.valor
    assert luz.encendida and luz.tiempo_restante<luz.duracion
    assert arma.tiempo_restante is None and armadura.tiempo_restante is None


def test_scroll_de_estado_no_envia_comandos_ni_tapa_el_inventario(app):
    import pygame
    from dataclasses import replace
    from vista_pygame.config_vista import ESCENA_PARTIDA
    from tests.vista.test_cinematica_cripta import esperar
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    e=app._escenas[ESCENA_PARTIDA];e.al_entrar()
    pantalla=pygame.Surface((1280,720))
    estado=replace(c.estado(),efectos=['Efecto de prueba '+str(i) for i in range(10)])
    e._dibujar_hud(pantalla,app._contexto.assets,estado)
    assert e._max_scroll_info>0 and e._rect_info.bottom<e._inventario.RECT.top
    antes=(c.estado().tiempo,c.estado().acciones_jugador)
    e.manejar_evento(pygame.event.Event(pygame.MOUSEWHEEL,pos=e._rect_info.center,y=-100,x=0))
    assert e._scroll_info==e._max_scroll_info
    e._dibujar_hud(pantalla,app._contexto.assets,estado)
    assert antes==(c.estado().tiempo,c.estado().acciones_jugador)
    assert pantalla.get_clip()==pantalla.get_rect()
