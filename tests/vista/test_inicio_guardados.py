"""Menú real: restauración binaria, archivos separados y errores recuperables."""
import time
from pathlib import Path
import pygame
import pytest
from dataclasses import replace
from tests.vista.test_cinematica_cripta import app, esperar
from vista_pygame.config_vista import ESCENA_MENU, ESCENA_PARTIDA
from controlador.estado_final import lineas_estado


def clic(escena,rect):
    escena.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center))


def guardar_actual(c,nombre='Ada',comandos=('R 1','U 1','R 1','EQ 2')):
    c.iniciar_partida('cripta-prueba',nombre,999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    for comando in comandos:
        c.enviar_comando(comando);esperar(lambda:not c.esperando_red())
    c.guardar();esperar(lambda:not c.esperando_red())
    assert any('Partida guardada:' in m for m in c.mensajes())
    ruta=Path(c._controlador.ruta_guardado)
    estado=list(lineas_estado(c.sesion.partida))
    log=Path(c.sesion.bitacora.ruta)
    c.salir()
    return ruta,estado,log


def actualizar_hasta(app,condicion):
    limite=time.monotonic()+10
    while not condicion() and time.monotonic()<limite:
        app._escenas[ESCENA_MENU].actualizar(20);time.sleep(.002)
    assert condicion()


def test_inicio_nueva_y_volver_preservan_formulario(app):
    m=app._escenas[ESCENA_MENU]
    assert m._pagina=='inicio'
    clic(m,m._rect_inicio(0));assert m._pagina=='nueva'
    for ch in 'Ada':m.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_a,mod=0,unicode=ch))
    assert m._nombre=='Ada'
    m.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    assert m._pagina=='inicio' and app._contexto.controlador.sesion is None
    clic(m,m._rect_inicio(0));assert m._nombre=='Ada'


def test_lista_vacia_y_archivo_danado_no_arrancan_partida(app):
    m=app._escenas[ESCENA_MENU];c=app._contexto.controlador
    clic(m,m._rect_inicio(1));esperar(lambda:not m._leyendo_guardados)
    assert m._pagina=='cargar' and not m._guardados
    clic(m,m._rect_volver());assert m._pagina=='inicio'
    carpeta=Path(c._partidas_dir);carpeta.mkdir(exist_ok=True)
    (carpeta/'roto.sav').write_bytes(b'No es una partida')
    clic(m,m._rect_inicio(1));esperar(lambda:not m._leyendo_guardados)
    assert len(m._guardados)==1 and m._guardados[0].error
    clic(m,m._rect_guardado(0))
    assert m._aviso_guardados and c.sesion is None
    m.dibujar(pygame.Surface((1280,720)))


def test_carga_desde_inicio_conserva_estado_log_y_ruta(app):
    c=app._contexto.controlador
    ruta,estado,log=guardar_actual(c)
    log_original=log.read_bytes();guardado_original=ruta.read_bytes()
    app.cambiar_escena(ESCENA_MENU)
    m=app._escenas[ESCENA_MENU]
    clic(m,m._rect_inicio(1));esperar(lambda:not m._leyendo_guardados)
    assert m._guardados[0].nombre_jugador=='Ada'
    clic(m,m._rect_guardado(0))
    clic(m,m._rect_guardado(0))  # El doble clic no inicia dos hilos de modelo.
    actualizar_hasta(app,lambda:app._actual==ESCENA_PARTIDA)
    assert list(lineas_estado(c.sesion.partida))==estado
    assert c.nombre_jugador=='Ada' and c.sesion.partida.semilla==999
    assert Path(c._controlador.ruta_guardado)==ruta
    assert log.read_bytes()==log_original and ruta.read_bytes()==guardado_original
    assert Path(c.sesion.bitacora.ruta)!=log
    c.enviar_comando('W');esperar(lambda:not c.esperando_red())
    c.guardar();esperar(lambda:not c.esperando_red())
    assert len(list(ruta.parent.glob('*.sav')))==1
    assert ruta.read_bytes()!=guardado_original


def test_partidas_nuevas_no_sobrescriben_otros_guardados(app):
    c=app._contexto.controlador
    primera,_,_=guardar_actual(c,'Ada',('W',))
    original=primera.read_bytes()
    segunda,_,_=guardar_actual(c,'Luis',('R 1',))
    assert segunda!=primera and primera.read_bytes()==original
    filas=c.listar_partidas_guardadas()
    assert len(filas)==2 and {f.nombre_jugador for f in filas}=={'Ada','Luis'}


def test_archivo_eliminado_despues_de_listarlo_muestra_error(app):
    c=app._contexto.controlador
    ruta,_,_=guardar_actual(c)
    app.cambiar_escena(ESCENA_MENU);m=app._escenas[ESCENA_MENU]
    clic(m,m._rect_inicio(1));esperar(lambda:not m._leyendo_guardados)
    ruta.unlink();clic(m,m._rect_guardado(0))
    actualizar_hasta(app,lambda:not m._cargando_partida)
    assert app._actual==ESCENA_MENU and m._aviso_guardados.startswith('No se pudo cargar:')
    clic(m,m._rect_volver());assert m._pagina=='inicio'


def test_version_incompatible_no_inicia_modelo(app):
    from persistencia.PartidaBinaria import PartidaBinaria
    c=app._contexto.controlador
    ruta,_,_=guardar_actual(c)
    archivo=PartidaBinaria(str(ruta))
    datos=archivo.cargar_global()
    salas=[(id,archivo.cargar_sala_binaria(id)) for id in datos['salas']]
    datos['version_cripta']='otra-version-incompatible'
    archivo.guardar(datos,salas)
    with pytest.raises(ValueError,match='version_cripta'):
        c.cargar_partida_guardada(str(ruta))
    assert c._hilo is None and c.sesion is None


def test_scroll_guardados_y_resoluciones(app):
    c=app._contexto.controlador;ruta,_,_=guardar_actual(c)
    m=app._escenas[ESCENA_MENU];m._abrir_guardados();esperar(lambda:not m._leyendo_guardados)
    fila=m._guardados[0]
    m._guardados=[replace(fila,archivo=f'partida-{n}.sav',nombre_jugador=f'Jugador {n}') for n in range(8)]
    m.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_PAGEDOWN))
    assert m._indice_guardado==4 and m._primero_guardado==1
    m.manejar_evento(pygame.event.Event(pygame.MOUSEWHEEL,y=-10,x=0))
    assert m._indice_guardado==7 and m._primero_guardado==4
    for tamano in ((1280,720),(1008,690),(1920,1080),(640,400)):
        m.dibujar(pygame.Surface(tamano))
        assert m._rect_guardado(3).bottom<tamano[1]
