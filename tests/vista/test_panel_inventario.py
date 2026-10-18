"""Selección real del inventario y protección ante clics repetidos."""
from types import SimpleNamespace
import time
import pygame
import pytest

from controlador.controlador_pygame import ObjetoVisual
from vista_pygame.render.panel_inventario import PanelInventario


def objeto(id, clase='pocion', encendida=False):
    return ObjetoVisual(id, 'itm_'+id, id, clase, False, encendida)


def clic(rect, boton=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=boton, pos=rect.center)


def test_la_vista_ordenada_conserva_indices_reales_tras_consumir():
    panel = PanelInventario()
    estado = SimpleNamespace(inventario=[objeto('espada', 'arma'), objeto('cura'),
                                        objeto('llave', 'llave'), objeto('antidoto', 'antidoto')])
    panel.criterio='nombre'
    assert panel.manejar_evento(clic(panel.filas(estado)[0][3]), estado) == (True, 'U 4')
    estado.inventario.pop(1)
    assert panel.manejar_evento(clic(panel.filas(estado)[0][3]), estado) == (True, 'U 3')


def test_scroll_cierre_y_reapertura_no_devuelven_acciones():
    panel = PanelInventario()
    estado = SimpleNamespace(inventario=[objeto(str(i)) for i in range(8)])
    assert panel.manejar_evento(clic(panel.siguiente), estado) == (True, None)
    assert panel.filas(estado)[0][0] == 2
    for _ in range(15):panel.manejar_evento(clic(panel.siguiente), estado)
    assert [i for i, *_ in panel.filas(estado)] == [6, 7, 8]
    panel.manejar_evento(clic(panel.cerrar), estado)
    assert not panel.abierto
    assert panel.manejar_evento(clic(panel.filas(estado)[0][3]), estado) == (False, None)
    assert panel.manejar_evento(clic(pygame.Rect(984, 543, 100, 20)), estado) == (True, None)
    assert panel.abierto
    estado.inventario.clear()
    assert panel.filas(estado) == [] and panel.desplazamiento == 0


def test_antorcha_alterna_encender_apagar_y_pergamino_usa_su_comando():
    panel = PanelInventario()
    estado = SimpleNamespace(inventario=[objeto('luz', 'antorcha'),
                                        objeto('retorno', 'pergamino_retroceso')])
    filas = panel.filas(estado)
    assert panel.manejar_evento(clic(filas[0][3]), estado) == (True, 'U 1')
    estado.inventario[0].encendida = True
    assert panel.manejar_evento(clic(filas[0][3]), estado) == (True, 'AP 1')
    assert panel.manejar_evento(clic(filas[1][3]), estado) == (True, 'P')
    assert panel.manejar_evento(clic(filas[1][3], 3), estado) == (True, None)


def esperar(condicion):
    limite = time.monotonic()+10
    while not condicion() and time.monotonic() < limite:time.sleep(.002)
    assert condicion()


def test_clic_real_consumir_y_doble_clic_bloqueado(tmp_path):
    from adaptadores.datos_offline import DatosOffline
    from herramientas.generar_cripta_prueba import generar
    from vista_pygame.app import AppPygame
    from vista_pygame.config_vista import ESCENA_MENU, ESCENA_PARTIDA

    generar(tmp_path/'datos')
    app = AppPygame(DatosOffline(str(tmp_path/'datos')), carpeta_cache=str(tmp_path/'cache'),
                    partidas_dir=str(tmp_path/'partidas'))
    c = app._contexto.controlador
    try:
        esperar(lambda:not app._escenas[ESCENA_MENU]._cargando)
        c.iniciar_partida('cripta-prueba', 'Ada', 999)
        esperar(lambda:c.estado() is not None and not c.esperando_red())
        for _ in range(3):
            c.enviar_comando('R 1')
            esperar(lambda:not c.esperando_red())
        inventario = c.estado().inventario
        assert [o.clase for o in inventario] == ['antorcha', 'arma', 'pocion']
        escena = app._escenas[ESCENA_PARTIDA]
        escena.al_entrar()
        estado = c.estado()
        acciones = estado.acciones_jugador
        ids = [o.instancia_id for o in estado.inventario]
        pantalla = pygame.Surface((1280, 720))
        escena.dibujar(pantalla)
        pygame.image.save(pantalla, str(tmp_path/'panel-con-pocion.png'))
        boton = escena._inventario.filas(estado)[2][3]
        # Una transición descarta el clic sin consumir el objeto.
        escena._transicion.entrar(estado)
        escena.manejar_evento(clic(boton))
        assert c.estado().acciones_jugador == acciones
        escena._transicion.actualizar(1050)
        escena.manejar_evento(clic(boton))
        escena.manejar_evento(clic(boton))
        esperar(lambda:not c.esperando_red())
        assert c.estado().acciones_jugador == acciones+1
        assert [o.instancia_id for o in c.estado().inventario] == ids[:2]
        assert c.error_pendiente() is None
        escena.actualizar(0)
        pantalla = pygame.Surface((1280, 720))
        escena.dibujar(pantalla)
        pygame.image.save(pantalla, str(tmp_path/'panel-despues-de-consumir.png'))
    finally:
        c.salir()
