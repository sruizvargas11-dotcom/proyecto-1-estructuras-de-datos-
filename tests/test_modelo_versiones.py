from pathlib import Path
from unittest.mock import patch
import pytest

from modelo.mundo.cripta_modelo import CriptaModelo
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from modelo.entidades.actor import Actor
from persistencia.version import PersistenciaVersiones


def cripta():
    return CriptaModelo('prueba','v1',10,20,None,9,10)


def test_modelo_busqueda_y_duplicados():
    c=cripta()
    with pytest.raises(RuntimeError):c.sala_por_id(10)
    c.agregar_sala(Sala(20,'Salida'));c.agregar_sala(Sala(10,'Entrada'))
    c.finalizar_carga()
    assert c.sala_por_id(10).nombre=='Entrada' and c.sala_por_id(999) is None
    c.agregar_sala(Sala(10,'Repetida'))
    with pytest.raises(RuntimeError):c.sala_por_id(10)
    with pytest.raises(ValueError):c.finalizar_carga()
    with pytest.raises(RuntimeError):c.sala_por_id(10)


def test_salas_no_comparten_listas():
    a=Sala(1,'A');b=Sala(2,'B')
    for nombre in ('salidas','enemigos_activos','enemigos_dormidos','objetos_suelo','trampas'):
        assert getattr(a,nombre) is not getattr(b,nombre)
    a.salidas.insertar_al_inicio(Salida('N',2))
    a.salidas.insertar_al_inicio(Salida('E',2,True))
    assert [s.direccion for s in a.salidas_abiertas()]==['N']
    assert a.salida_hacia('O') is None and a.tiempo_rastro==-1


def test_versiones_lectura_y_comparacion(tmp_path):
    p=PersistenciaVersiones(tmp_path)
    assert p.version_cripta_local('prueba') is None and p.version_catalogo_local() is None
    p.guardar_version_cripta('prueba','v1');p.guardar_version_catalogo('c1')
    q=PersistenciaVersiones(tmp_path)
    assert q.version_cripta_local('prueba')=='v1'
    assert q.version_cripta_local('prueba','v1')=='v1'
    assert q.version_cripta_local('prueba','v2') is None
    assert q.version_catalogo_local('c1')=='c1'
    assert q.version_catalogo_local('c2') is None


@pytest.mark.parametrize('version',[None,True,7,'','   '])
def test_version_invalida_conserva_anterior(tmp_path,version):
    p=PersistenciaVersiones(tmp_path);p.guardar_version_cripta('prueba','v1')
    with pytest.raises(ValueError):p.guardar_version_cripta('prueba',version)
    assert p.version_cripta_local('prueba')=='v1'


@pytest.mark.parametrize('operacion',['write_text','replace'])
def test_version_fallo_disco(tmp_path,operacion):
    p=PersistenciaVersiones(tmp_path);p.guardar_version_cripta('prueba','v1')
    with patch.object(Path,operacion,side_effect=OSError('simulado')):
        with pytest.raises(OSError):p.guardar_version_cripta('prueba','v2')
    assert p.version_cripta_local('prueba')=='v1'


def test_actor_limites_vida_y_muerte():
    a=Actor('a',10,2,1,100,vida=7)
    assert a.curar(10)==3 and a.vida==10
    assert a.recibir_dano(3)==3 and a.vida==7
    assert a.recibir_dano(100)==7 and a.vida==0 and not a.vivo
    assert a.curar(100)==0 and a.recibir_dano(3)==0
    with pytest.raises(ValueError):a.curar(-1)
    with pytest.raises(ValueError):a.recibir_dano(-1)


@pytest.mark.parametrize('vida_max,velocidad,vida',[(0,100,None),(10,0,None),(10,100,-1),(10,100,11)])
def test_actor_invalido(vida_max,velocidad,vida):
    with pytest.raises(ValueError):Actor('a',vida_max,2,1,velocidad,vida=vida)
