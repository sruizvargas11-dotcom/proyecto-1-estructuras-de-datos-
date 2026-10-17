import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

import utilidades.puntajes as m

def p(nombre='José', resultado='victoria', enemigos=3, acciones=20, tiempo=100):
    return m.Puntaje(nombre,'cripta-01','v1',acciones,enemigos,tiempo,resultado)

def test_prioridades_y_empate_estable():
    t=m.TablaPuntajes()
    for x in [p('Q','en_curso',99,0,0),p('Derrota','derrota',99),p('Mucho tiempo',tiempo=200),p('Más acciones',acciones=21),p('Uno'),p('Dos'),p('Más enemigos',enemigos=4)]:
        t.agregar(x)
    assert [x['nombre'] for x in t.a_datos()]==['Más enemigos','Uno','Dos','Mucho tiempo','Más acciones','Derrota','Q']

def test_grupos_criptas_versiones():
    t=m.TablaPuntajes()
    for c,v in [('b','v1'),('a','v2'),('a','v1')]:
        t.agregar(m.Puntaje('X',c,v,1,0,1,'victoria'))
    assert [(x['cripta_id'],x['version_cripta']) for x in t.a_datos()]==[('a','v1'),('a','v2'),('b','v1')]

def test_json_roundtrip_y_agregar(tmp_path):
    ruta=tmp_path/'carpeta/puntajes.json'
    assert len(m.TablaPuntajes.cargar(ruta))==0
    t=m.registrar_puntaje(ruta,p())
    assert m.TablaPuntajes.cargar(ruta).a_datos()==t.a_datos()
    assert 'José' in ruta.read_text(encoding='utf-8')
    assert len(m.registrar_puntaje(ruta,p('Ana')))==2

@pytest.mark.parametrize('campo,valor',[('nombre',' '),('cripta_id',None),('version_cripta',1),('acciones_jugador',True),('acciones_jugador',-1),('enemigos_derrotados',1.5),('tiempo_final',-1),('resultado','otro')])
def test_rechaza_datos_invalidos(campo,valor):
    d=p().a_datos();d[campo]=valor
    with pytest.raises(ValueError):m.Puntaje.desde_datos(d)

@pytest.mark.parametrize('contenido',['{','[]','{"formato":2,"puntajes":[]}','{"formato":1,"puntajes":[{}]}'])
def test_archivo_malo_no_sobrescrito(tmp_path,contenido):
    ruta=tmp_path/'p.json';ruta.write_text(contenido,encoding='utf-8')
    with pytest.raises(ValueError):m.registrar_puntaje(ruta,p())
    assert ruta.read_text(encoding='utf-8')==contenido

def test_fallo_reemplazo_preserva_anterior(tmp_path):
    ruta=tmp_path/'p.json';m.registrar_puntaje(ruta,p());antes=ruta.read_bytes()
    with patch.object(m.os,'replace',side_effect=OSError('fallo simulado')):
        with pytest.raises(OSError):m.registrar_puntaje(ruta,p('Ana'))
    assert ruta.read_bytes()==antes
    assert list(tmp_path.glob('.puntajes-*'))==[]

def test_carga_desordenada_y_crecimiento(tmp_path):
    ruta=tmp_path/'p.json'
    registros=[p(str(i),enemigos=i).a_datos() for i in range(100)]
    ruta.write_text(json.dumps({'formato':1,'puntajes':registros}),encoding='utf-8')
    t=m.TablaPuntajes.cargar(ruta)
    assert len(t)==100 and t.obtener(0).enemigos_derrotados==99

def test_no_comparte_registro_original():
    t=m.TablaPuntajes();x=p();t.agregar(x);x.nombre='Otro'
    assert t.obtener(0).nombre=='José'
