"""Pruebas del contrato de bloque 1: no usan el servidor real."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch
import json
import random

import pytest
import requests

from controlador.controlador_red import cargar_cripta, cargar_esqueleto_completo
from adaptadores.datos_offline import DatosOffline
from adaptadores.datos_http import DatosHTTP
from persistencia.esqueleto import PersistenciaEsqueleto
from persistencia.version import PersistenciaVersiones
from estructuras.vector_dinamico import Vector
from estructuras.lista_simple import ListaSimple
from estructuras.lista_doble import ListaDoble
from estructuras.pila import Pila
from estructuras.cola import Cola
from estructuras.array_circular import ArrayCircular
from estructuras.array_ordenado import ArrayOrdenado
from main import main


class FuentePrueba:
    def __init__(self):
        self.generales = {'id': 'prueba', 'version': 'v1', 'salas_total': 3,
            'paginas': 2, 'sala_inicial': 10, 'sala_salida': 30,
            'llave_salida': None, 'presupuesto_solicitudes': 20, 'inventario_max': 10}
        self.paginas = [
            {'pagina': 1, 'total_paginas': 2, 'salas': [
                {'id': 20, 'nombre': 'Pasillo', 'salidas': {'N': {'sala': 30}}},
                {'id': 10, 'nombre': 'Entrada', 'salidas': {'E': {'sala': 20}}}]},
            {'pagina': 2, 'total_paginas': 2, 'salas': [
                {'id': 30, 'nombre': 'Salida', 'salidas': {}}]}]
        self.llamadas = []
        self.fallo_pagina = None
        self.version_final = 'v1'

    def datos_cripta(self, id):
        self.llamadas.append('generales')
        return deepcopy(self.generales)

    def esqueleto_cripta(self, id, pagina):
        self.llamadas.append(pagina)
        if self.fallo_pagina == pagina:
            raise RuntimeError('Fallo de red simulado')
        return deepcopy(self.paginas[pagina - 1])

    def version_cripta(self, id):
        self.llamadas.append('version')
        return {'version': self.version_final}


def test_dos_paginas_y_segunda_carga(tmp_path):
    f = FuentePrueba()
    c, cache = cargar_cripta(f, 'prueba', tmp_path)
    assert not cache and f.llamadas == ['generales', 1, 2, 'version']
    assert [s.id for s in c.recorrer_salas()] == [10, 20, 30]
    assert c.sala_por_id(10).salida_hacia('E').cerrada is False
    f.llamadas.clear()
    copia, cache = cargar_cripta(f, 'prueba', tmp_path)
    assert cache and f.llamadas == ['generales']
    assert copia.sala_por_id(10) is not c.sala_por_id(10)
    assert PersistenciaVersiones(tmp_path).version_cripta_local('prueba') == 'v1'


def test_datos_reales(tmp_path):
    c, cache = cargar_cripta(DatosOffline(), 'cripta-01', tmp_path)
    assert len(c) == 6 and not cache
    puerta = c.sala_por_id(2).salida_hacia('E')
    assert (puerta.sala_destino_id, puerta.cerrada, puerta.llave, puerta.cierre_automatico) == (5, True, 'itm_llave_bronce', 500)
    assert cargar_cripta(DatosOffline(), 'cripta-01', tmp_path)[1]


def test_version_nueva(tmp_path):
    f = FuentePrueba()
    cargar_cripta(f, 'prueba', tmp_path)
    f.generales['version'] = f.version_final = 'v2'
    f.llamadas.clear()
    c, cache = cargar_cripta(f, 'prueba', tmp_path)
    assert c.version == 'v2' and not cache and 2 in f.llamadas


@pytest.mark.parametrize('fallo', ['pagina', 'version', 'escritura', 'reemplazo'])
def test_fallo_no_destruye_copia_anterior(tmp_path, fallo):
    f = FuentePrueba()
    cargar_cripta(f, 'prueba', tmp_path)
    ruta = tmp_path / 'prueba' / 'esqueleto.json'
    anterior = ruta.read_bytes()
    f.generales['version'] = f.version_final = 'v2'
    if fallo == 'pagina':
        f.fallo_pagina = 2
    if fallo == 'version':
        f.version_final = 'v3'
    if fallo in ('escritura', 'reemplazo'):
        metodo = 'write_text' if fallo == 'escritura' else 'replace'
        with patch.object(Path, metodo, side_effect=OSError('Disco simulado')):
            with pytest.raises(OSError): cargar_cripta(f, 'prueba', tmp_path)
    else:
        with pytest.raises((RuntimeError, ValueError)): cargar_cripta(f, 'prueba', tmp_path)
    assert ruta.read_bytes() == anterior
    assert PersistenciaVersiones(tmp_path).version_cripta_local('prueba') == 'v1'


@pytest.mark.parametrize('contenido', [b'{}', b'[]', b'null', b'{', b'\xff\xfe'])
def test_cache_corrupta_se_recarga(tmp_path, contenido):
    f = FuentePrueba()
    cargar_cripta(f, 'prueba', tmp_path)
    (tmp_path / 'prueba' / 'esqueleto.json').write_bytes(contenido)
    f.llamadas.clear()
    assert cargar_cripta(f, 'prueba', tmp_path)[1] is False
    assert 1 in f.llamadas


@pytest.mark.parametrize('campo,valor', [
    ('id','otra'), ('version',''), ('version',None), ('paginas',0), ('paginas',True),
    ('paginas',4), ('salas_total',0), ('salas_total','3'), ('sala_inicial',True),
    ('sala_salida',None), ('presupuesto_solicitudes',-1), ('inventario_max',False),
    ('llave_salida',[])])
def test_generales_invalidos(tmp_path, campo, valor):
    f=FuentePrueba(); f.generales[campo]=valor
    with pytest.raises(ValueError): cargar_cripta(f, 'prueba', tmp_path)
    assert not (tmp_path/'prueba'/'esqueleto.json').exists()


@pytest.mark.parametrize('caso', ['pagina', 'total', 'vacia', 'duplicado', 'destino', 'entrada',
                                  'direccion', 'booleano', 'cierre', 'tipo_sala', 'salidas', 'faltan'])
def test_mapa_invalido_no_se_publica(tmp_path, caso):
    f=FuentePrueba()
    sala=f.paginas[0]['salas'][0]
    if caso=='pagina': f.paginas[1]['pagina']=1
    elif caso=='total': f.paginas[1]['total_paginas']=3
    elif caso=='vacia': f.paginas[1]['salas']=[]
    elif caso=='duplicado': f.paginas[1]['salas'][0]['id']=20
    elif caso=='destino': sala['salidas']['N']['sala']=999
    elif caso=='entrada': f.generales['sala_inicial']=999
    elif caso=='direccion': sala['salidas']={'X': {'sala':30}}
    elif caso=='booleano': sala['salidas']['N']['cerrada']='false'
    elif caso=='cierre': sala['salidas']['N']['cierre_automatico']=-1
    elif caso=='tipo_sala': sala['id']='20'
    elif caso=='salidas': sala['salidas']=[]
    elif caso=='faltan': f.paginas[0]['salas'].pop()
    with pytest.raises(ValueError): cargar_cripta(f, 'prueba', tmp_path)
    assert not (tmp_path/'prueba'/'esqueleto.json').exists()


def test_disco_sin_permiso_no_se_oculta(tmp_path):
    with patch.object(Path, 'read_text', side_effect=PermissionError('sin permiso')):
        with pytest.raises(PermissionError): cargar_cripta(FuentePrueba(),'prueba',tmp_path)


def test_main_dos_arranques(tmp_path,capsys):
    args=['--offline','--cripta','cripta-01','--cache-dir',str(tmp_path)]
    assert main(args)==0
    assert 'fuente de datos' in capsys.readouterr().out
    assert main(args)==0
    assert 'caché' in capsys.readouterr().out


def test_main_error_controlado(tmp_path,capsys):
    assert main(['--offline','--cripta','no-existe','--cache-dir',str(tmp_path)])==1
    assert 'No se pudo cargar' in capsys.readouterr().out


def test_main_argumento_invalido():
    with pytest.raises(SystemExit) as e: main(['--ofline'])
    assert e.value.code==2


def respuesta(status, datos):
    r=Mock(status_code=status,text='error');r.json.return_value=datos
    return r


def test_http_timeout_cuenta_intento():
    h=DatosHTTP()
    with patch('adaptadores.datos_http.requests.get',side_effect=requests.Timeout('timeout')):
        with pytest.raises(RuntimeError):h.listar_criptas()
    assert h.requests_realizados==1


def test_http_429_limitado():
    h=DatosHTTP(max_reintentos=2)
    with patch('adaptadores.datos_http.requests.get',return_value=respuesta(429,{'reintentar_en':0})) as get:
        with patch('adaptadores.datos_http.time.sleep'):
            with pytest.raises(RuntimeError): h.listar_criptas()
    assert get.call_count==3 and h.requests_realizados==3


def test_http_presupuesto_impide_siguiente_solicitud():
    h=DatosHTTP()
    with patch('adaptadores.datos_http.requests.get',return_value=respuesta(200,{'presupuesto_solicitudes':1})) as get:
        h.datos_cripta('prueba')
        with pytest.raises(RuntimeError):h.version_cripta('prueba')
        assert get.call_count==1


@pytest.mark.parametrize('espera', [-1,'2',float('nan'),float('inf'),61,None])
def test_http_espera_invalida(espera):
    with patch('adaptadores.datos_http.requests.get',return_value=respuesta(429,{'reintentar_en':espera})):
        with pytest.raises(ValueError):DatosHTTP().listar_criptas()


@pytest.mark.parametrize('clase',[Pila,Cola,ArrayCircular])
@pytest.mark.parametrize('capacidad',[0,-1,True,1.5])
def test_capacidad_invalida(clase,capacidad):
    with pytest.raises(ValueError):clase(capacidad)


@pytest.mark.parametrize('semilla',range(5))
def test_vector_operaciones_aleatorias(semilla):
    rng=random.Random(semilla);v=Vector();referencia=[]
    for _ in range(500):
        if not referencia or rng.random()<0.6:
            n=rng.randrange(1000);v.agregarValor(n);referencia.append(n)
        else:
            i=rng.randrange(len(referencia));assert v.eliminar(i)==referencia.pop(i)
        assert list(v)==referencia and len(v)==len(referencia)


def test_vector_indices_invalidos():
    v=Vector();v.agregarValor(1)
    for indice in (-1,1,100):
        with pytest.raises(IndexError):v.eliminar(indice)
    for indice in (True,1.2,'0'):
        with pytest.raises(TypeError):v.obtenerValor(indice)


def test_lista_simple_ambos_extremos():
    s=ListaSimple();s.insertar_al_final(2);s.insertar_al_inicio(1);s.insertar_al_final(3)
    assert list(s)==[1,2,3] and s.a_lista_python()==[1,2,3]
    for valor in (2,1,3):assert s.eliminar_valor(valor)
    assert len(s)==0 and not s.eliminar_valor(9)
    s.insertar_al_final(4);assert list(s)==[4]


@pytest.mark.parametrize('semilla',range(5))
def test_lista_doble_enlaces(semilla):
    rng=random.Random(semilla);l=ListaDoble();nodos=[]
    for i in range(200):
        if not nodos or rng.random()<0.5:
            nodos.insert(0,l.insertar_al_frente(i))
        else:
            n=rng.choice(nodos)
            if rng.random()<0.5:l.eliminar_nodo(n);nodos.remove(n)
            else:l.mover_al_frente(n);nodos.remove(n);nodos.insert(0,n)
        assert list(l.recorrer_desde_frente())==nodos
        assert list(l.recorrer_desde_fondo())==nodos[::-1]
        assert len(l)==len(nodos)


@pytest.mark.parametrize('capacidad',[1,5,20])
def test_pila_cola_circular(capacidad):
    pila=Pila(capacidad);cola=Cola(capacidad);circular=ArrayCircular(capacidad)
    for i in range(100):
        pila.apilar_elemento(i);cola.encolar(i);circular.agregarValor(i)
    ultimos=list(range(100-capacidad,100))
    assert circular.listar_en_orden()==ultimos
    assert [cola.desencolar() for _ in ultimos]==ultimos
    assert [pila.desapilar_elemento() for _ in ultimos]==ultimos[::-1]
    assert cola.desencolar() is None and pila.desapilar_elemento() is None
    cola.encolar(999);assert cola.desencolar()==999


def test_array_ordenado_claves_y_actualizaciones():
    a=ArrayOrdenado()
    for i in range(99,-1,-1):a.insertar(i,str(i))
    for i in range(100):assert a.busqueda_binaria(i)==str(i)
    a.insertar(50,'nuevo');assert len(a)==100 and a.busqueda_binaria(50)=='nuevo'
    assert a.busqueda_binaria(999) is None


def test_fallo_registro_version_se_repara_en_proxima_carga(tmp_path):
    f=FuentePrueba()
    with patch.object(PersistenciaVersiones,'guardar_version_cripta',side_effect=OSError('fallo metadata')):
        with pytest.raises(OSError):cargar_cripta(f,'prueba',tmp_path)
    assert PersistenciaEsqueleto(tmp_path).cargar_esqueleto('prueba','v1') is not None
    f.llamadas.clear()
    assert cargar_cripta(f,'prueba',tmp_path)[1]
    assert f.llamadas==['generales']
    assert PersistenciaVersiones(tmp_path).version_cripta_local('prueba')=='v1'


@pytest.mark.parametrize('campo,valor',[('salas_total',4),('sala_inicial',20),('inventario_max',12)])
def test_cache_con_metadatos_distintos_no_se_acepta(tmp_path,campo,valor):
    f=FuentePrueba();cargar_cripta(f,'prueba',tmp_path)
    f.generales[campo]=valor;f.llamadas.clear()
    if campo=='salas_total':
        with pytest.raises(ValueError):cargar_cripta(f,'prueba',tmp_path)
    else:
        assert not cargar_cripta(f,'prueba',tmp_path)[1]
    assert 1 in f.llamadas


@pytest.mark.parametrize('id',[None,'',' ','..','../otra','a/b','a\\b'])
def test_identificador_invalido_no_consulta_fuente(tmp_path,id):
    f=FuentePrueba()
    with pytest.raises(ValueError):cargar_cripta(f,id,tmp_path)
    assert f.llamadas==[]


def test_guardado_modelo_invalido_no_reemplaza_archivo(tmp_path):
    f=FuentePrueba();c,_=cargar_cripta(f,'prueba',tmp_path)
    ruta=tmp_path/'prueba'/'esqueleto.json';original=ruta.read_bytes()
    c.sala_por_id(10).salida_hacia('E').sala_destino_id=999
    with pytest.raises(ValueError):PersistenciaEsqueleto(tmp_path).guardar_esqueleto(c)
    assert ruta.read_bytes()==original


def test_cargador_sin_cache():
    f=FuentePrueba();c=cargar_esqueleto_completo(f,'prueba')
    assert len(c)==3 and f.llamadas==['generales',1,2,'version']


def test_main_listado_vacio(capsys):
    f=Mock();f.listar_criptas.return_value={'criptas':[]}
    with patch('main.crear_fuente',return_value=f):assert main(['--offline'])==1
    assert 'No hay criptas' in capsys.readouterr().out


@pytest.mark.parametrize('datos',[[],None,{'criptas':[{}]}])
def test_main_listado_invalido(datos):
    f=Mock();f.listar_criptas.return_value=datos
    with patch('main.crear_fuente',return_value=f):assert main(['--offline'])==1


def test_http_reintentos_consumen_presupuesto():
    h=DatosHTTP()
    respuestas=[respuesta(200,{'presupuesto_solicitudes':3}),respuesta(429,{'reintentar_en':0}),respuesta(429,{'reintentar_en':0})]
    with patch('adaptadores.datos_http.requests.get',side_effect=respuestas) as get:
        h.datos_cripta('prueba')
        with patch('adaptadores.datos_http.time.sleep'):
            with pytest.raises(RuntimeError):h.version_cripta('prueba')
        assert get.call_count==3
    assert h.requests_realizados==3


@pytest.mark.parametrize('presupuesto',[None,True,-1,'9',0])
def test_http_presupuesto_invalido_o_insuficiente(presupuesto):
    with patch('adaptadores.datos_http.requests.get',return_value=respuesta(200,{'presupuesto_solicitudes':presupuesto})):
        with pytest.raises((ValueError,RuntimeError)):DatosHTTP().datos_cripta('prueba')


def test_http_respuesta_no_json():
    r=respuesta(200,{})
    r.json.side_effect=ValueError('JSON inválido')
    h=DatosHTTP()
    with patch('adaptadores.datos_http.requests.get',return_value=r):
        with pytest.raises(ValueError):h.listar_criptas()
    assert h.requests_realizados==1


def test_http_uuid_estable_entre_peticiones():
    h=DatosHTTP()
    with patch('adaptadores.datos_http.requests.get',return_value=respuesta(200,{})) as get:
        h.listar_criptas();h.version_catalogo()
    assert get.call_args_list[0].kwargs['headers']==get.call_args_list[1].kwargs['headers']
