import json
import random
from pathlib import Path

import pytest
import adaptadores.datos_offline as modulo_offline

from estructuras.lista_doble import ListaDoble
from estructuras.listalru import ListaLRU
from estructuras.pila import Pila
from estructuras.heap_minimo import HeapMinimo
from modelo.entidades.actor import Actor
from modelo.entidades.objetos.arma import Arma
from modelo.entidades.objetos.armadura import Armadura
from modelo.entidades.objetos.objeto import Objeto
from modelo.entidades.objetos.fabrica_objetos import FabricaObjetos
from modelo.entidades.objetos.pocion import Pocion
from modelo.entidades.objetos.antidoto import Antidoto
from modelo.entidades.objetos.llave import Llave
from modelo.entidades.objetos.antorcha import Antorcha
from modelo.entidades.objetos.pergamino_retroceso import PergaminoRetroceso
from modelo.entidades.jugador import Jugador
from modelo.entidades.enemigo import Enemigo
from modelo.entidades.trampa import Trampa
from modelo.mundo.cripta_modelo import CriptaModelo
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from controlador.controlador_red import cargar_cripta
from adaptadores.datos_offline import DatosOffline


def jugador(capacidad=5):
    return Jugador('j', 30, 6, 2, 100, capacidad, Sala(1, 'Inicio'))

def objeto(i, peso=1, valor=10, nombre='A'):
    return Objeto(str(i), 'tipo', nombre, peso, valor)

def al_inventario(j, o):
    j.sala_actual.objetos_suelo.insertar_al_inicio(o)
    assert j.recoger(o)
    return j.buscar_nodo(o.instancia_id)

def orden(j):
    return [n.valor.instancia_id for n in j.inventario.recorrer_desde_frente()]


def test_doble_extremos_recorridos_y_nodo_ajeno():
    l=ListaDoble();a=l.insertar_al_final('a');b=l.insertar_al_final('b')
    c=l.insertar_al_frente('c')
    assert [n.valor for n in l.recorrer_desde_frente()]==['c','a','b']
    assert [n.valor for n in l.recorrer_desde_fondo()]==['b','a','c']
    l.mover_al_frente(b)
    assert len(l)==3 and l.cola() is a
    otro=ListaDoble().insertar_al_frente('otro')
    for n in (otro,None):
        with pytest.raises(ValueError):l.eliminar_nodo(n)
        with pytest.raises(ValueError):l.mover_al_frente(n)
    l.eliminar_nodo(c)
    with pytest.raises(ValueError):l.eliminar_nodo(c)
    assert len(l)==2
    l.eliminar_nodo(b);l.eliminar_nodo(a)
    assert l.head() is None and l.cola() is None and len(l)==0


def test_pila_default_cinco_y_opcion_sin_limite():
    p=Pila()
    for i in range(6):p.apilar_elemento(i)
    assert len(p)==5
    assert [p.desapilar_elemento() for _ in range(6)]==[5,4,3,2,1,None]
    p=Pila(None)
    for i in range(6):p.apilar_elemento(i)
    assert len(p)==6


@pytest.mark.parametrize('capacidad',[0,-1,True,1.5,None])
def test_lru_capacidad_invalida(capacidad):
    with pytest.raises(ValueError):ListaLRU(capacidad)


def test_lru_pins_duplicados_contadores_y_tope():
    l=ListaLRU(2);a=object();b=object()
    assert l.insertar('a',a) and l.insertar('b',b)
    l.marcar_en_uso('a');l.marcar_en_uso('a');l.marcar_en_uso('b')
    assert l.insertar('a',a) and len(l)==2
    assert not l.insertar('c',object()) and len(l)==2
    with pytest.raises(ValueError):l.insertar('a',object())
    l.desmarcar_en_uso('a')
    assert not l.insertar('c',object())
    l.desmarcar_en_uso('a')
    assert l.insertar('c',object())
    for key in ('b','b','c','a','falta'):l.buscar(key)
    antes=[n.valor.id_ficha for n in l._lista.recorrer_desde_frente()]
    assert l.contadores()==(3,2,1)
    assert l.contadores()==(3,2,1)
    assert antes==[n.valor.id_ficha for n in l._lista.recorrer_desde_frente()]


def test_lru_actualizar_libre_no_cambia_tamano():
    l=ListaLRU(1);l.insertar('a',1);l.insertar('a',2)
    assert len(l)==1 and l.buscar('a')==2 and l.contador_desalojos==0
    with pytest.raises(ValueError):l.desmarcar_en_uso('a')
    with pytest.raises(KeyError):l.marcar_en_uso('x')


@pytest.mark.parametrize('campo',['vida_max','vida','ataque','defensa','velocidad'])
@pytest.mark.parametrize('valor',[float('nan'),float('inf'),True,'5'])
def test_actor_rechaza_estadisticas_no_finitas(campo,valor):
    datos=dict(instancia_id='a',vida_max=30,vida=30,ataque=3,defensa=2,velocidad=100)
    datos[campo]=valor
    with pytest.raises(ValueError):Actor(**datos)


def test_actor_cancelacion_real_del_heap():
    a=Actor('a',10,1,1,100);h=HeapMinimo()
    a.evento_actual=h.insertarEntrada(20,a)
    a.recibir_dano(100)
    assert not a.vivo and h.extraer_minimo() is None
    assert a.curar(100)==0


def test_fabrica_todas_subclases_y_ids_unicos():
    carpeta=Path(modulo_offline.__file__).resolve().parents[1]/'datos_offline/catalogo'
    f=FabricaObjetos();creados=[]
    for p in carpeta.glob('itm_*.json'):
        ficha=json.loads(p.read_text(encoding='utf-8'))
        creados.extend([f.crear(ficha),f.crear(ficha)])
    assert len(set(o.instancia_id for o in creados))==len(creados)
    assert {type(o) for o in creados}=={Arma,Armadura,Pocion,Antidoto,Llave,Antorcha,PergaminoRetroceso}
    for o in creados:
        if not isinstance(o,Arma):assert not hasattr(o,'ataque_bonus')
    siguiente=f.siguiente_id
    with pytest.raises(ValueError):f.crear(dict(id='x',nombre='x',peso=1,valor=1,clase='error'))
    assert f.siguiente_id==siguiente


@pytest.mark.parametrize('rearme,esperado',[(None,300),(10,10)])
def test_trampa_desarmada_no_repite_y_rearma(rearme,esperado):
    a=Actor('a',20,1,1,100)
    t=Trampa('t','tipo','Dardos',4,rearme)
    assert t.rearme==esperado
    assert t.activar(a)==4 and a.vida==16 and not t.armada
    assert t.activar(a)==0 and a.vida==16
    t.rearmar();assert t.activar(a)==4 and a.vida==12


@pytest.mark.parametrize('rearme',[0,-1,True,3.5])
def test_trampa_intervalo_invalido(rearme):
    with pytest.raises(ValueError):Trampa('t','tipo','T',3,rearme)


def test_recoger_lleno_no_cambia_suelo_evento_o_tiempo():
    j=jugador(1);a=objeto(1);b=objeto(2)
    al_inventario(j,a);j.sala_actual.objetos_suelo.insertar_al_inicio(b)
    h=HeapMinimo();entrada=h.insertarEntrada(120,j);j.evento_actual=entrada;j.tiempo_siguiente=120
    assert not j.recoger(b) and list(j.sala_actual.objetos_suelo)==[b]
    assert j.evento_actual is entrada and entrada.valido and j.tiempo_siguiente==120
    assert orden(j)==['1']


def test_cursor_soltar_centro_sin_busqueda_y_sin_duplicar(monkeypatch):
    j=jugador()
    for i in range(3):al_inventario(j,objeto(i))
    assert j.siguiente().instancia_id=='1'
    def no_buscar(*args):raise AssertionError('Soltar por cursor no debe buscar por ID')
    monkeypatch.setattr(j,'buscar_nodo',no_buscar)
    retirado=j.cursor
    assert j.soltar_actual().instancia_id=='1'
    assert orden(j)==['0','2'] and j.cursor.valor.instancia_id=='2'
    assert j.anterior().instancia_id=='0'
    with pytest.raises(ValueError):j.soltar_nodo(retirado)
    assert [o.instancia_id for o in j.sala_actual.objetos_suelo]==['1']


def test_equipar_sustituye_bonus_sin_acumular_y_soltar_quita_bonus():
    j=jugador();a=Arma('a','a','A',1,1,3);b=Arma('b','b','B',1,1,5)
    c=Armadura('c','c','C',1,1,4)
    for o in (a,b,c):al_inventario(j,o)
    assert j.equipar('a') and j.ataque==9
    assert j.equipar('a') and j.ataque==9
    assert j.equipar('b') and j.ataque==11 and orden(j)[0]=='b'
    assert j.equipar('c') and j.defensa==6 and len(j.inventario)==3
    j.soltar('b');assert j.ataque==6
    j.soltar('c');assert j.defensa==2


@pytest.mark.parametrize('criterio',['peso','valor','nombre'])
def test_vista_ordenada_estable_conserva_nodos_cursor_y_orden(criterio):
    j=jugador()
    for o in (objeto(0,3,30,'C'),objeto(1,1,10,'A'),objeto(2,1,10,'A')):al_inventario(j,o)
    antes=list(j.inventario.recorrer_desde_frente());cursor=j.cursor
    vista=j.inventario_ordenado(criterio)
    assert [o.instancia_id for o in vista]==['1','2','0']
    assert list(j.inventario.recorrer_desde_frente())==antes and j.cursor is cursor


def escenario(comportamiento='rastreador',cerrada=False):
    c=CriptaModelo('c','v',1,3,None,10,5)
    salas=[Sala(i,str(i)) for i in range(1,5)]
    salas[0].salidas.insertar_al_inicio(Salida('N',3,cerrada))
    salas[0].salidas.insertar_al_inicio(Salida('S',2))
    for s in salas:c.agregar_sala(s)
    c.finalizar_carga()
    j=jugador();j.sala_actual=salas[3]
    e=Enemigo('e','tipo','Enemigo',10,1,1,100,comportamiento,salas[0])
    return c,salas,j,e


@pytest.mark.parametrize('edad,accion',[(0,'mover'),(399,'mover'),(400,'esperar'),(401,'esperar')])
def test_rastreador_frontera_400(edad,accion):
    c,s,j,e=escenario();s[1].tiempo_rastro=100
    assert e.decidir_accion(j,100+edad,random.Random(0))[0]==accion


def test_rastreador_empate_puertas_y_no_busca_mapa(monkeypatch):
    c,s,j,e=escenario();s[1].tiempo_rastro=s[2].tiempo_rastro=10
    def prohibido(*a):raise AssertionError('No buscar en el mapa en cada decisión')
    monkeypatch.setattr(c,'sala_por_id',prohibido)
    assert e.decidir_accion(j,20,random.Random(1))==('mover',s[1])
    s[2].tiempo_rastro=19
    assert e.decidir_accion(j,20,random.Random(1))==('mover',s[2])
    s[0].salida_hacia('N').cerrada=True
    assert e.decidir_accion(j,20,random.Random(1))==('mover',s[1])


@pytest.mark.parametrize('comportamiento',['guardián','errante','rastreador'])
def test_ataque_prioritario_sin_consumir_azar(comportamiento):
    c,s,j,e=escenario(comportamiento);j.sala_actual=s[0]
    azar=random.Random(0);antes=azar.getstate()
    assert e.decidir_accion(j,0,azar)==('atacar',j)
    assert azar.getstate()==antes


def test_errante_reproducible_guardian_y_sin_salidas():
    c,s,j,e=escenario('errante');a=random.Random(123);b=random.Random(123)
    assert [e.decidir_accion(j,0,a)[1].id for _ in range(30)]==[e.decidir_accion(j,0,b)[1].id for _ in range(30)]
    for salida in s[0].salidas:salida.cerrada=True
    antes=a.getstate();assert e.decidir_accion(j,0,a)==('esperar',None) and a.getstate()==antes
    e.comportamiento='guardián'
    assert e.decidir_accion(j,0,a)==('esperar',None)


def test_carga_real_offline_enlaza_destinos_tambien_desde_cache(tmp_path):
    for _ in range(2):
        c,cache=cargar_cripta(DatosOffline(),'cripta-01',tmp_path)
        for sala in c.recorrer_salas():
            for salida in sala.salidas:
                assert salida.sala_destino is c.sala_por_id(salida.sala_destino_id)


def test_jugador_usa_estadisticas_de_generales():
    p=Path(modulo_offline.__file__).resolve().parents[1]/'datos_offline/cripta-01/general.json'
    generales=json.loads(p.read_text(encoding='utf-8'))
    generales['jugador']['vida_max']=47
    generales['inventario_max']=0
    j=Jugador.desde_generales(generales,Sala(1,'A'))
    assert j.vida==47 and j.inventario_max==0
    o=objeto(1);j.sala_actual.objetos_suelo.insertar_al_inicio(o)
    assert not j.recoger(o)


def test_enemigos_comparten_tipo_pero_no_vida_ni_instancia():
    p=Path(modulo_offline.__file__).resolve().parents[1]/'datos_offline/catalogo/ent_rata_gigante.json'
    ficha=json.loads(p.read_text(encoding='utf-8'))
    a=Enemigo.desde_ficha('rata:1',ficha,vida=4)
    b=Enemigo.desde_ficha('rata:2',ficha)
    a.recibir_dano(2)
    assert a.vida==2 and b.vida==ficha['vida_max']
    assert a.instancia_id!=b.instancia_id and a.tipo_id==b.tipo_id
    assert list(a.suelta)==ficha['suelta']


def test_rastro_futuro_o_no_visitado_no_se_sigue():
    c,s,j,e=escenario()
    s[1].tiempo_rastro=21
    s[2].tiempo_rastro=-1
    assert e.decidir_accion(j,20,random.Random(0))==('esperar',None)


def test_inventario_no_equipable_y_id_duplicado():
    j=jugador();o=objeto(1);al_inventario(j,o)
    duplicado=objeto(1)
    j.sala_actual.objetos_suelo.insertar_al_inicio(duplicado)
    assert not j.recoger(duplicado)
    assert not j.equipar('1') and j.ataque==6 and j.defensa==2
    assert j.soltar('no_existe') is None
