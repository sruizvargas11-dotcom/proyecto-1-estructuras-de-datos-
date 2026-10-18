"""Regresiones de equipo, orden, trampas e interacción de cerraduras."""
from types import SimpleNamespace
import pygame
import pytest
from vista_pygame.controlador_pygame import ObjetoVisual, SalidaVisual, EventoTrampa
from vista_pygame.render.panel_inventario import PanelInventario
from vista_pygame.render.heroe_equipo import clave_equipo
from vista_pygame.render.iluminacion_sala import IluminacionSala
from vista_pygame.render.cinematica_trampa import EfectoTrampa, familia_trampa
from vista_pygame.render.interaccion_candado import InteraccionCandado,rect_candado
from vista_pygame.recursos.cargador_assets import CargadorAssets
from tests.vista.test_cinematica_cripta import app, esperar, terminar


def obj(id,clase,equipado=False,encendida=False,peso=1,valor=2):
    return ObjetoVisual(id,'itm_'+id,id,clase,equipado,encendida,peso,valor)


def mouse(tipo,pos,**datos):return pygame.event.Event(tipo,pos=pos,**datos)


def test_todos_los_objetos_tienen_su_accion_y_soltar_con_indice_real():
    p=PanelInventario()
    casos=[(obj('a','arma'),'EQ 1'),(obj('a','arma',True),'DEQ 1'),
           (obj('a','armadura',True),'DEQ 1'),(obj('a','antorcha',encendida=True),'AP 1'),
           (obj('a','pocion'),'U 1'),(obj('a','antidoto'),'U 1'),
           (obj('a','pergamino_retroceso'),'P'),(obj('a','llave'),None)]
    for objeto,comando in casos:
        estado=SimpleNamespace(inventario=[objeto])
        _,_,fila,boton=p.filas(estado)[0]
        assert p.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,boton.center,button=1),estado)==(True,comando)
        assert p.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,p.boton_soltar(fila).center,button=1),estado)==(True,'T 1')


@pytest.mark.parametrize('criterio',['nombre','peso','valor'])
def test_ordenar_no_altera_inventario_y_botones_siguen_las_instancias(criterio):
    p=PanelInventario();p.criterio=criterio
    inventario=[obj('z','arma',peso=3,valor=30),obj('a','armadura',peso=1,valor=1),obj('m','pocion',peso=2,valor=12)]
    estado=SimpleNamespace(inventario=inventario)
    assert [o.instancia_id for _,o,*_ in p.filas(estado)]==['a','m','z']
    for indice,o,fila,boton in p.filas(estado):
        comando=p.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,p.boton_soltar(fila).center,button=1),estado)[1]
        assert comando==f'T {indice}' and inventario[indice-1] is o
    assert [o.instancia_id for o in inventario]==['z','a','m']


def test_ocho_equipos_en_cinco_estados_y_la_muerte_no_cambia_equipo():
    assets=CargadorAssets();huellas=[]
    for k in range(8):
        estado=SimpleNamespace(arma_equipada='Espada' if k&1 else '',armadura_equipada='Coraza' if k&4 else '',
                              inventario=[obj('luz','antorcha',encendida=bool(k&2))])
        assert clave_equipo(estado)==k
        for nombre in ('reposo','caminar','ataque','muerte','recoger'):
            for cuadro in (0,12,24,31):
                im,offset=assets.fotograma_jugador_equipado(nombre,cuadro,k)
                r=im.get_bounding_rect(min_alpha=100)
                assert r.width>0 and r.height>0 and r.left>0 and r.top>0
                assert r.right<im.get_width() and r.bottom<=160
        im,_=assets.fotograma_jugador_equipado('reposo',0,k)
        huellas.append(pygame.image.tobytes(im,'RGBA'))
        assert assets.cuadros_muerte_equipo(k)[0][0] is assets.fotograma_jugador_equipado('muerte',0,k)[0]
        assert assets.sprite_espalda_equipo(k).get_width()>0
    assert len(set(huellas))==8


def test_luz_varia_suavemente_y_no_tapa_el_hud():
    luz=IluminacionSala();rect=pygame.Rect(40,40,760,470)
    oscuro=pygame.Surface((1280,720));oscuro.fill((150,150,150))
    luz.dibujar(oscuro,rect,(300,300))
    luz.actualizar(420,True)
    claro=pygame.Surface((1280,720));claro.fill((150,150,150))
    luz.dibujar(claro,rect,(300,300))
    assert claro.get_at((300,300)).r>oscuro.get_at((300,300)).r+40
    assert claro.get_at((1000,300))==oscuro.get_at((1000,300))==(150,150,150,255)
    luz.actualizar(210,False);assert luz.nivel==.5
    luz.actualizar(-100,False);assert luz.nivel==.5


@pytest.mark.parametrize('nombre,familia',[('Pinchos de suelo','pinchos'),('Dardos en la pared','dardos'),
    ('Gas venenoso','gas'),('Fuego','fuego'),('Escarcha','hielo'),('Techo de roca','rocas'),
    ('Descarga eléctrica','electricidad'),('Mecanismo secreto','mecanismo')])
def test_trampa_muestra_tipo_y_emite_un_solo_impacto_en_el_instante_correcto(nombre,familia):
    assert familia_trampa(nombre)==familia
    e=EfectoTrampa();evento=EventoTrampa(dano=4,vida_antes=100,vida_despues=96,nombre=nombre)
    e.iniciar(nombre,evento)
    e.actualizar(e.IMPACTO-1);assert not e.extraer_impactos()
    e.actualizar(1);assert e.extraer_impactos()==[evento]
    e.actualizar(20000);assert not e.extraer_impactos() and not e.activa
    e.iniciar(nombre,evento);e.actualizar(700)
    e.dibujar(pygame.Surface((1280,720)),CargadorAssets())


def test_candado_rechaza_llave_incorrecta_y_emite_solicitud_una_vez():
    e=InteraccionCandado(SalidaVisual('E',5,'Nicho',True,True,'itm_bronce'))
    estado=SimpleNamespace(inventario=[obj('negra','llave'),obj('bronce','llave')])
    for objeto,rect in e.tarjetas(estado):
        e.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,rect.center,button=1),estado)
        e.manejar_evento(mouse(pygame.MOUSEMOTION,e.ranura.center,rel=(0,0),buttons=(1,0,0)),estado)
        e.manejar_evento(mouse(pygame.MOUSEBUTTONUP,e.ranura.center,button=1),estado)
        if objeto.instancia_id=='negra':assert e.fase=='elegir' and not e.solicita_comando
    e.actualizar(e.INSERCION-1);assert not e.solicita_comando
    e.actualizar(1);assert e.solicita_comando
    e.enviado=True;e.fase='espera';assert not e.solicita_comando
    e.confirmar(True);e.actualizar(e.APERTURA);assert e.terminada


def test_arrastrar_llave_real_abre_una_vez_y_la_reja_termina_aun_con_ataques(app):
    from vista_pygame.config_vista import ESCENA_PARTIDA
    from vista_pygame.render.render_sala import SALA_RECT
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    for comando in ('R 1','R 1','R 1','R 1','N'):
        c.enviar_comando(comando);esperar(lambda:not c.esperando_red())
    c.eventos_nuevos()
    e=app._escenas[ESCENA_PARTIDA];e.al_entrar()
    antes=c.estado().acciones_jugador
    e.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,rect_candado('E',SALA_RECT).center,button=1))
    candado=e._candado;assert candado is not None
    objeto,tarjeta=candado.tarjetas(c.estado())[0]
    e.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,tarjeta.center,button=1))
    e.manejar_evento(mouse(pygame.MOUSEBUTTONUP,candado.ranura.center,button=1))
    e.actualizar(candado.INSERCION)
    esperar(lambda:not c.esperando_red())
    e.actualizar(0)
    assert candado.fase=='abriendo' and e._puerta_ms==700
    e.actualizar(candado.APERTURA)
    assert e._candado is None and e._puerta_ms==0
    terminar(e,c)
    assert e._puerta_ms==700 and c.estado().acciones_jugador==antes+1
    assert not next(s for s in c.estado().salidas if s.direccion=='E').cerrada
    assert any(o.instancia_id==objeto.instancia_id for o in c.estado().inventario)
    assert c.error_pendiente() is None


def test_reja_deja_de_forzar_abierta_y_refleja_el_cierre_automatico(app):
    from vista_pygame.config_vista import ESCENA_PARTIDA
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    for comando in ('R 1','R 1','R 1','R 1','N'):
        c.enviar_comando(comando);esperar(lambda:not c.esperando_red())
    c.eventos_nuevos()
    e=app._escenas[ESCENA_PARTIDA];e.al_entrar()
    c.enviar_comando('AB E');esperar(lambda:not c.esperando_red());e.actualizar(0)
    terminar(e,c)
    assert e._puerta_direccion is None
    for _ in range(5):
        c.enviar_comando('W');esperar(lambda:not c.esperando_red())
    e.actualizar(0)
    assert next(s for s in c.estado().salidas if s.direccion=='E').cerrada
    assert e._puerta_cerrando and e._puerta_ms==0
    terminar(e,c)
    assert e._puerta_direccion is None and e._puerta_ms==700


def test_pausa_botones_guardar_cargar_y_continuar_sin_dobles_acciones(app):
    from vista_pygame.config_vista import ESCENA_PARTIDA,ESCENA_PAUSA
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    app.cambiar_escena(ESCENA_PARTIDA)
    app.cambiar_escena(ESCENA_PAUSA)
    p=app._escenas[ESCENA_PAUSA]
    acciones=c.estado().acciones_jugador
    for indice,fragmento in ((1,'Partida guardada:'),(2,'Partida cargada:')):
        boton=p._botones[indice]
        p.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,boton.center,button=1))
        p.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,boton.center,button=1))
        esperar(lambda:not c.esperando_red());p.actualizar(0)
        assert not p._pendiente
        assert sum(fragmento in m for m in c.mensajes())==1
    p.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,p._botones[0].center,button=1))
    assert app._actual==ESCENA_PARTIDA and c.estado().acciones_jugador==acciones
    assert c.error_pendiente() is None


def test_pausa_teclado_y_cierre_tienen_las_mismas_acciones(app):
    from vista_pygame.config_vista import ESCENA_PARTIDA,ESCENA_PAUSA
    c=app._contexto.controlador
    c.iniciar_partida('cripta-prueba','Ada',999)
    esperar(lambda:c.estado() is not None and not c.esperando_red())
    app.cambiar_escena(ESCENA_PARTIDA);app.cambiar_escena(ESCENA_PAUSA)
    p=app._escenas[ESCENA_PAUSA]
    p.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_DOWN))
    assert p._seleccion==1
    p.manejar_evento(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    esperar(lambda:not c.esperando_red());p.actualizar(0)
    assert any('Partida guardada:' in m for m in c.mensajes())
    p.manejar_evento(mouse(pygame.MOUSEBUTTONDOWN,p._cerrar.center,button=1))
    assert app._actual==ESCENA_PARTIDA
