import importlib
import json
import random
from unittest.mock import patch

import pytest

from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar, insertion_sort, merge_sort
from estructuras.heap_minimo import HeapMinimo
from modelo.entidades.actor import Actor
from modelo.mundo.cripta_modelo import CriptaModelo
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from persistencia.esqueleto import PersistenciaEsqueleto


def vector(datos):
    v = Vector()
    for dato in datos:
        v.agregarValor(dato)
    return v


@pytest.mark.parametrize('nombre', ['heap_minimo', 'array_ordenado', 'ordenamientos', 'listalru'])
def test_importaciones(nombre):
    importlib.import_module('estructuras.' + nombre)


@pytest.mark.parametrize('algoritmo', [insertion_sort, merge_sort, ordenar])
@pytest.mark.parametrize('datos', [[], [1], [3, 1, 2, 1], list(range(40)), list(range(40, -1, -1))])
def test_orden_correcto(algoritmo, datos):
    v = vector(datos)
    algoritmo(v, lambda a, b: (a > b) - (a < b))
    assert [v.obtenerValor(i) for i in range(len(v))] == sorted(datos)


@pytest.mark.parametrize('algoritmo', [insertion_sort, merge_sort, ordenar])
def test_estabilidad(algoritmo):
    datos = [(i % 3, i) for i in range(60)]
    v = vector(datos)
    algoritmo(v, lambda a, b: (a[0] > b[0]) - (a[0] < b[0]))
    assert [v.obtenerValor(i) for i in range(len(v))] == sorted(datos, key=lambda x: x[0])


def test_selector_dos_bloques_invertidos():
    v = vector(list(range(50, 100)) + list(range(50)))
    assert ordenar(v, lambda a, b: a - b) == 'merge_sort'
    assert [v.obtenerValor(i) for i in range(100)] == list(range(100))


def test_heap_orden_cancelacion_y_empates():
    rng = random.Random(7)
    h = HeapMinimo()
    esperado = []
    for seq in range(100):
        tiempo = rng.randrange(20)
        entrada = h.insertarEntrada(tiempo, seq)
        if seq % 5 == 0:
            h.invalidarEntrada(entrada)
        else:
            esperado.append((tiempo, seq))
    assert [h.extraer_minimo() for _ in esperado] == [seq for _, seq in sorted(esperado)]
    assert h.extraer_minimo() is None


def test_reprogramacion_recibe_secuencia_nueva():
    h = HeapMinimo()
    primero = h.insertarEntrada(10, 'primero')
    h.insertarEntrada(10, 'segundo')
    nuevo = h.reprogramarEntrada(primero, 10)
    assert nuevo.secuencia > primero.secuencia
    assert [h.extraer_minimo(), h.extraer_minimo(), h.extraer_minimo()] == ['segundo', 'primero', None]


def test_muerte_cancela_entrada_real():
    h = HeapMinimo()
    actor = Actor('actor', 10, 2, 1, 100)
    actor.evento_actual = h.insertarEntrada(10, actor)
    actor.recibir_dano(10)
    assert h.extraer_minimo() is None


def modelo():
    c = CriptaModelo('prueba', 'v1', 1, 2, None, 9, 10)
    a = Sala(1, 'Entrada')
    a.salidas.insertar_al_inicio(Salida('N', 2, True, 'llave', 500))
    c.agregar_sala(Sala(2, 'Salida'))
    c.agregar_sala(a)
    c.finalizar_carga()
    return c


def test_modelo_usa_ordenador_compartido():
    from estructuras.ordenamientos import ordenar as real
    with patch('modelo.mundo.cripta_modelo.ordenar', wraps=real) as espia:
        c = modelo()
    espia.assert_called_once()
    assert c.ultimo_algoritmo == 'insertion_sort'
    assert c.sala_por_id(1).nombre == 'Entrada'


@pytest.mark.parametrize('contenido', ['{', '{}', '[]', 'null'])
def test_cache_invalida(tmp_path, contenido):
    ruta = tmp_path / 'prueba' / 'esqueleto.json'
    ruta.parent.mkdir()
    ruta.write_text(contenido, encoding='utf-8')
    assert PersistenciaEsqueleto(tmp_path).cargar_esqueleto('prueba', 'v1') is None


@pytest.mark.parametrize('caso', ['duplicado', 'destino', 'tipo', 'direccion'])
def test_cache_estructura_inconsistente(tmp_path, caso):
    p = PersistenciaEsqueleto(tmp_path)
    p.guardar_esqueleto(modelo())
    ruta = tmp_path / 'prueba' / 'esqueleto.json'
    datos = json.loads(ruta.read_text(encoding='utf-8'))
    if caso == 'duplicado':
        datos['salas'][1]['id'] = 1
    elif caso == 'destino':
        datos['salas'][0]['salidas'][0]['sala_destino_id'] = 999
    elif caso == 'tipo':
        datos['salas'][0]['salidas'][0]['cerrada'] = 'false'
    else:
        datos['salas'][0]['salidas'].append(datos['salas'][0]['salidas'][0])
    ruta.write_text(json.dumps(datos), encoding='utf-8')
    assert p.cargar_esqueleto('prueba', 'v1') is None


def test_cache_independencia_y_version(tmp_path):
    p = PersistenciaEsqueleto(tmp_path)
    c = modelo()
    p.guardar_esqueleto(c)
    c.sala_por_id(1).salida_hacia('N').cerrada = False
    recuperada = p.cargar_esqueleto('prueba', 'v1')
    assert recuperada.sala_por_id(1) is not c.sala_por_id(1)
    assert recuperada.sala_por_id(1).salida_hacia('N').cerrada
    assert p.cargar_esqueleto('prueba', 'v2') is None


@pytest.mark.parametrize('tiempo', [-1, True, 1.5, '10', None])
def test_heap_rechaza_tiempo_invalido_sin_perder_evento(tiempo):
    h = HeapMinimo()
    entrada = h.insertarEntrada(10, 'accion')
    with pytest.raises(ValueError):
        h.reprogramarEntrada(entrada, tiempo)
    assert h.extraer_minimo() == 'accion'
    assert h.extraer_minimo() is None
