import pytest
from estructuras.vector_dinamico import Vector
from estructuras.lista_simple import ListaSimple
from estructuras.lista_doble import ListaDoble
from estructuras.pila import Pila
from estructuras.cola import Cola
from estructuras.array_circular import ArrayCircular
from estructuras.array_ordenado import ArrayOrdenado
from estructuras.heap_minimo import HeapMinimo
from estructuras.listalru import ListaLRU

@pytest.mark.parametrize('crear',[Vector,ListaSimple,ListaDoble,Pila,Cola,lambda:ArrayCircular(3),ArrayOrdenado,HeapMinimo])
def test_contadores_cero_y_consulta_pura(crear):
    t=crear();antes=t.contadores()
    assert all(v==0 for _,v in antes)
    assert t.contadores()==antes and len(t)==0

def test_vector_trabajo_y_sin_doble_conteo():
    v=Vector()
    for x in range(5):v.agregarValor(x)
    v.asignarValor(1,9);assert v.obtenerValor(1)==9
    assert v.eliminar(0)==0 and v.eliminarUltimo()==4
    assert v.contador_eliminaciones==2 and v.contador_desplazamientos==4
    assert v.contador_redimensiones==1 and v.contador_asignaciones==1
    it=iter(v);assert next(it)==9;it.close()
    assert list(v)==[9,2,3]
    assert v.contador_recorridos==2 and v.contador_elementos_recorridos==4
    antes=v.contadores()
    with pytest.raises(IndexError):v.eliminar(99)
    assert antes==v.contadores()

def test_simple_busquedas_comparaciones_y_fallos():
    l=ListaSimple()
    for x in (10,20,30):l.insertar_al_final(x)
    assert l.contiene_valor(20) and not l.contiene_valor(99)
    assert l.contador_busquedas==2 and l.contador_comparaciones==5
    assert l.eliminar_valor(20) and not l.eliminar_valor(99)
    assert l.contador_intentos_eliminacion==2 and l.contador_eliminaciones==1
    assert l.contador_comparaciones==9
    assert list(l)==[10,30] and l.contador_elementos_recorridos==7

def test_doble_recorridos_y_nodos_invalidos():
    l=ListaDoble();a=l.insertar_al_final(1);b=l.insertar_al_final(2)
    assert [n.valor for n in l.recorrer_desde_frente()]==[1,2]
    assert [n.valor for n in l.recorrer_desde_fondo()]==[2,1]
    assert l.contador_nodos_recorridos==4
    l.mover_al_frente(b);l.mover_al_frente(b)
    assert l.contador_movimientos_al_frente==2 and l.contador_nodos_recorridos==4
    l.eliminar_nodo(a);antes=l.contadores()
    with pytest.raises(ValueError):l.eliminar_nodo(a)
    assert antes==l.contadores()

@pytest.mark.parametrize('clase,insertar,extraer,consultar,intentos,retiros,consultas',[
 (Pila,'apilar_elemento','desapilar_elemento','ver_tope','contador_intentos_desapilar','contador_desapilados','contador_consultas_tope'),
 (Cola,'encolar','desencolar','ver_frente','contador_intentos_desencolar','contador_desencolados','contador_consultas_frente')])
def test_pila_cola_distinguen_vacio_descarte_y_extraccion(clase,insertar,extraer,consultar,intentos,retiros,consultas):
    t=clase(2);assert getattr(t,extraer)() is None
    assert getattr(t,consultar)() is None
    for x in (1,2,3):getattr(t,insertar)(x)
    assert t.contador_descartes_por_limite==1 and getattr(t,retiros)==0
    resultado=[getattr(t,extraer)(),getattr(t,extraer)()]
    assert resultado==([3,2] if clase is Pila else [2,3])
    assert getattr(t,intentos)==3 and getattr(t,retiros)==2 and getattr(t,consultas)==1

def test_circular_listados_y_sobrescritura():
    a=ArrayCircular(2);assert a.listar_en_orden()==[]
    for i in range(4):a.agregarValor(i)
    assert a.listar_en_orden()==[2,3]
    assert a.contador_listados==2 and a.contador_elementos_listados==2
    assert a.contador_sobrescrituras==2

def test_ordenado_comparaciones_reales_y_actualizaciones():
    a=ArrayOrdenado();a.insertar(2,'a');a.insertar(1,'b')
    assert a.contador_inserciones==2 and a.contador_desplazamientos==1
    assert a.contador_comparaciones==2
    a.insertar(2,'actualizada')
    assert len(a)==2 and a.contador_actualizaciones==1 and a.contador_comparaciones==5
    assert a.busqueda_binaria(2)=='actualizada'
    assert a.contador_comparaciones==8
    assert a.busqueda_binaria(9) is None and a.contador_comparaciones==12

def test_heap_cancelacion_reprogramacion_y_descartes():
    h=HeapMinimo();a=h.insertarEntrada(1,'a');b=h.insertarEntrada(2,'b')
    h.invalidarEntrada(a);h.invalidarEntrada(a)
    assert h.contador_cancelaciones==1
    antes=h.contadores()
    with pytest.raises(ValueError):h.reprogramarEntrada(b,-1)
    assert h.contadores()==antes and b.valido
    nueva=h.reprogramarEntrada(b,3)
    assert nueva.valido and h.contador_reprogramaciones==1
    assert h.extraer_minimo()=='b' and h.contador_descartes_cancelados==2
    assert h.extraer_minimo() is None and h.contador_intentos_extraccion==2
    assert h._contador_extracciones==1

def test_lru_metrica_detallada_compatible_y_sin_cambiar_orden():
    l=ListaLRU(1);a=object()
    assert l.insertar('a',a);assert l.insertar('a',a)
    l.marcar_en_uso('a');assert not l.insertar('b',object())
    for k in ('a','a','a','b','c'):l.buscar(k)
    antes=l.contadores_operaciones();nodo=l._lista.head()
    assert l.contadores()==(3,2,0) and l.contadores_operaciones()==antes
    assert l._lista.head() is nodo
    assert l.contador_inserciones==1 and l.contador_actualizaciones==1
    assert l.contador_rechazos_capacidad==1 and l.contador_referencias_adquiridas==1
    l.desmarcar_en_uso('a');assert l.contador_referencias_liberadas==1
    assert l.insertar('b',object()) and l.contador_desalojos==1
