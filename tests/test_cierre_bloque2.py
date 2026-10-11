"""Regresiones del cierre: probar comportamiento observable y reintentos reales."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_red import ControladorRed, cargar_esqueleto_completo
from persistencia.contenido import PersistenciaContenido
from persistencia.catalogo import PersistenciaCatalogo
from tests.test_controlador_red import FuenteContada


@pytest.fixture
def entorno(tmp_path):
    fuente = FuenteContada(DatosOffline())
    cripta = cargar_esqueleto_completo(fuente, 'cripta-01')
    return fuente, cripta, ControladorRed(fuente, cripta, tmp_path)


@pytest.mark.parametrize('entrada', ['cola', 'garantizar', 'directo'])
@pytest.mark.parametrize('error', [RuntimeError('red'), ValueError('datos'), OSError('disco')])
def test_lote_fallido_se_puede_reintentar(entorno, entrada, error):
    fuente, cripta, red = entorno
    red.planificar_precarga(cripta.sala_por_id(1))
    with patch.object(fuente, 'contenido_salas', side_effect=error):
        if entrada == 'cola':
            assert red.procesar_cola() == 0
        else:
            with pytest.raises(type(error)):
                if entrada == 'garantizar':
                    red.garantizar_contenido(2)
                else:
                    red.solicitar_contenido_lote([2, 3, 5])
    assert red.pendientes() == 3
    assert red.procesar_cola() == 3
    assert red.pendientes() == 0
    assert all(red.contenido_cargado(i) for i in (2, 3, 5))


def test_nueva_partida_reutiliza_cache_sin_marcadores_auxiliares(entorno, tmp_path):
    fuente, cripta, red = entorno
    red.garantizar_contenido(2)
    antes = (len(fuente.contenido), len(fuente.lotes_catalogo))
    otra = cargar_esqueleto_completo(fuente, cripta.id)
    segundo = ControladorRed(fuente, otra, tmp_path)
    segundo.garantizar_contenido(2)
    assert (len(fuente.contenido), len(fuente.lotes_catalogo)) == antes


@pytest.mark.parametrize('clase', ['contenido', 'catalogo'])
def test_version_por_archivo_aunque_marcador_global_ya_se_actualizo(tmp_path, clase):
    if clase == 'contenido':
        p = PersistenciaContenido(tmp_path, 'v1')
        p.guardar('cripta-01', 2, {'sala': 2})
        (tmp_path / 'cripta-01' / 'version.json').write_text('{"version":"v2"}')
        assert PersistenciaContenido(tmp_path, 'v2').cargar('cripta-01', 2) is None
    else:
        p = PersistenciaCatalogo(tmp_path, 'v1')
        p.guardar_ficha('tipo', {'id': 'tipo'})
        (tmp_path / 'catalogo_version.json').write_text('"v2"')
        assert PersistenciaCatalogo(tmp_path, 'v2').cargar_ficha('tipo') is None


@pytest.mark.parametrize('clase', ['contenido', 'catalogo'])
def test_json_corrupto_con_marcador_vigente(tmp_path, clase):
    if clase == 'contenido':
        p = PersistenciaContenido(tmp_path, 'v1')
        p.guardar('cripta-01', 2, {'sala': 2})
        (tmp_path / 'cripta-01' / 'version.json').write_text('{"version":"v1"}')
        ruta = Path(p._ruta_sala('cripta-01', 2))
        cargar = lambda: p.cargar('cripta-01', 2)
    else:
        p = PersistenciaCatalogo(tmp_path, 'v1')
        p.guardar_ficha('tipo', {'id': 'tipo'})
        (tmp_path / 'catalogo_version.json').write_text('"v1"')
        ruta = Path(p.ruta_ficha('tipo'))
        cargar = lambda: p.cargar_ficha('tipo')
    ruta.write_bytes(b'{')
    assert cargar() is None


@pytest.mark.parametrize('nombre', ['NUL', 'con', 'AUX.txt', 'COM1', 'lpt9', '../otra', 'a/b', 'a\\b', 'a:b', '', '..', 'NUL.txt '])
def test_identificadores_invalidos_se_rechazan_antes_de_escribir(tmp_path, nombre):
    with pytest.raises(ValueError):
        PersistenciaContenido(tmp_path, 'v1').guardar(nombre, 1, {})
    with pytest.raises(ValueError):
        PersistenciaCatalogo(tmp_path, 'v1').guardar_ficha(nombre, {})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('clase', ['contenido', 'catalogo'])
def test_error_serializacion_conserva_copia_previa_y_limpia_temporal(tmp_path, clase):
    if clase == 'contenido':
        p = PersistenciaContenido(tmp_path, 'v1')
        guardar = lambda datos: p.guardar('cripta-01', 2, datos)
        cargar = lambda: p.cargar('cripta-01', 2)
    else:
        p = PersistenciaCatalogo(tmp_path, 'v1')
        guardar = lambda datos: p.guardar_ficha('tipo', datos)
        cargar = lambda: p.cargar_ficha('tipo')
    guardar({'valor': 'anterior'})
    with pytest.raises(TypeError):
        guardar({'valor': object()})
    assert cargar() == {'valor': 'anterior'}
    assert list(tmp_path.rglob('*.tmp')) == []


def test_fallo_en_ultima_entidad_no_publica_ninguna_sala_ni_gasta_ids(entorno):
    fuente, cripta, red = entorno
    original = fuente.contenido_salas
    def corrupta(cripta_id, ids):
        respuesta = original(cripta_id, ids)
        for datos in respuesta['contenido']:
            if datos['sala'] == 2:
                datos['enemigos'][-1]['vida'] = 99999
        return respuesta
    with patch.object(fuente, 'contenido_salas', side_effect=corrupta):
        with pytest.raises(ValueError):
            red.solicitar_contenido_lote([1, 2])
    assert not red.contenido_cargado(1)
    assert not red.contenido_cargado(2)
    assert len(cripta.sala_por_id(1).objetos_suelo) == 0
    assert len(cripta.sala_por_id(2).enemigos_dormidos) == 0
    assert red._fabrica.siguiente_id == 1
    assert red.solicitar_contenido_lote([1, 2]) == 2
    assert len(cripta.sala_por_id(2).enemigos_dormidos) == 2


def test_cache_parcial_no_cambia_asignacion_de_ids(entorno, tmp_path):
    fuente, cripta, red = entorno
    sala2 = DatosOffline().contenido_salas(cripta.id, [2])['contenido'][0]
    PersistenciaContenido(tmp_path, cripta.version).guardar(cripta.id, 2, sala2)
    red.solicitar_contenido_lote([1, 2])
    primero = next(cripta.sala_por_id(1).objetos_suelo.recorrer_valores())
    assert primero.instancia_id == 'objeto:1'


@pytest.mark.parametrize('sala_id', [True, 1.0, '1', -1])
def test_id_invalido_no_altera_cola(entorno, sala_id):
    fuente, cripta, red = entorno
    with pytest.raises(ValueError):
        red.solicitar_contenido_lote([sala_id])
    assert red.pendientes() == 0
    assert fuente.contenido == []


def test_reemplazo_fallido_conserva_original_y_limpia_temporal(tmp_path):
    p = PersistenciaCatalogo(tmp_path, 'v1')
    p.guardar_ficha('tipo', {'valor': 'anterior'})
    with patch('persistencia.cache_json.os.replace', side_effect=OSError('disco lleno')):
        with pytest.raises(OSError):
            p.guardar_ficha('tipo', {'valor': 'nuevo'})
    assert p.cargar_ficha('tipo') == {'valor': 'anterior'}
    assert list(tmp_path.rglob('*.tmp')) == []


def test_escritores_no_comparten_temporal(tmp_path):
    # Los hilos son solo una herramienta de prueba; el juego sigue síncrono.
    import os
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    barrera = Barrier(2)
    reemplazar = os.replace
    temporales = []
    p = PersistenciaCatalogo(tmp_path, 'v1')
    def sincronizar(origen, destino):
        temporales.append(origen)
        barrera.wait(timeout=5)
        reemplazar(origen, destino)
    with patch('persistencia.cache_json.os.replace', side_effect=sincronizar):
        with ThreadPoolExecutor(max_workers=2) as grupo:
            futuros = [grupo.submit(p.guardar_ficha, 'tipo', {'valor': valor}) for valor in (1, 2)]
            errores = [futuro.exception() for futuro in futuros]
    # Windows puede rechazar un reemplazo simultáneo: debe propagarse el error,
    # conservar un documento íntegro y limpiar ambos temporales.
    assert any(error is None for error in errores)
    assert all(error is None or isinstance(error, OSError) for error in errores)
    assert len(set(temporales)) == 2
    assert p.cargar_ficha('tipo') in ({'valor': 1}, {'valor': 2})
    assert list(tmp_path.rglob('*.tmp')) == []


@pytest.mark.parametrize('documento', [
    {}, [], {'id': 'tipo'},
    {'formato_cache': True, 'version': 'v1', 'identificador': 'tipo', 'datos': {}},
    {'formato_cache': 1, 'version': 'v1', 'identificador': 'otro', 'datos': {}},
    {'formato_cache': 1, 'version': 'v1', 'identificador': 'tipo', 'datos': []},
])
def test_sobre_invalido_o_antiguo_es_fallo_de_cache(tmp_path, documento):
    p = PersistenciaCatalogo(tmp_path, 'v1')
    p.guardar_ficha('tipo', {})
    Path(p.ruta_ficha('tipo')).write_text(json.dumps(documento), encoding='utf-8')
    assert p.cargar_ficha('tipo') is None


def test_cache_no_utf8_es_recuperable(tmp_path):
    p = PersistenciaCatalogo(tmp_path, 'v1')
    p.guardar_ficha('tipo', {})
    Path(p.ruta_ficha('tipo')).write_bytes(b'\xff\xfe')
    assert p.cargar_ficha('tipo') is None


def test_contenido_cache_incompleto_se_recarga(entorno, tmp_path):
    fuente, cripta, red = entorno
    PersistenciaContenido(tmp_path, cripta.version).guardar(cripta.id, 2, {'sala': 2})
    assert red.solicitar_contenido_lote([2]) == 1
    assert fuente.contenido == [[2]]
    assert len(cripta.sala_por_id(2).enemigos_dormidos) == 2


def test_cache_con_vida_imposible_no_bloquea_reintentos(entorno, tmp_path):
    fuente, cripta, red = entorno
    datos = DatosOffline().contenido_salas(cripta.id, [2])['contenido'][0]
    datos['enemigos'][0]['vida'] = 99999
    p = PersistenciaContenido(tmp_path, cripta.version)
    p.guardar(cripta.id, 2, datos)
    with pytest.raises(ValueError):
        red.solicitar_contenido_lote([2])
    assert p.cargar(cripta.id, 2) is None
    assert red.procesar_cola() == 1
    assert fuente.contenido == [[2]]


@pytest.mark.parametrize('fallo', ['ausente', 'duplicada', 'instancia', 'tipo', 'sala_bool'])
def test_contenido_invalido_no_publica_y_admite_recuperacion(entorno, fallo):
    fuente, cripta, red = entorno
    original = fuente.contenido_salas
    def corrupta(cripta_id, ids):
        respuesta = original(cripta_id, ids)
        datos = respuesta['contenido'][0]
        if fallo == 'ausente':
            respuesta['contenido'] = []
        elif fallo == 'duplicada':
            respuesta['contenido'].append(datos)
        elif fallo == 'instancia':
            datos['enemigos'][0]['instancia'] = ''
        elif fallo == 'tipo':
            datos['enemigos'][0]['tipo'] = '../tipo'
        else:
            datos['sala'] = True
        return respuesta
    with patch.object(fuente, 'contenido_salas', side_effect=corrupta):
        with pytest.raises(ValueError):
            red.solicitar_contenido_lote([2])
    assert len(cripta.sala_por_id(2).enemigos_dormidos) == 0
    assert not red.contenido_cargado(2)
    assert red.procesar_cola() == 1


@pytest.mark.parametrize('fallo', ['ausente', 'duplicada', 'incompleta'])
def test_catalogo_invalido_no_publica_salas(entorno, fallo):
    fuente, cripta, red = entorno
    original = fuente.catalogo
    def corrupta(ids):
        respuesta = original(ids)
        if fallo == 'ausente':
            respuesta['entidades'] = []
        elif fallo == 'duplicada':
            respuesta['entidades'].append(respuesta['entidades'][0])
        else:
            respuesta['entidades'][0].pop('nombre')
        return respuesta
    with patch.object(fuente, 'catalogo', side_effect=corrupta):
        with pytest.raises(ValueError):
            red.solicitar_contenido_lote([2])
    assert not red.contenido_cargado(2)
    assert red.procesar_cola() == 1


def test_error_segundo_guardado_no_publica_salas_y_preserva_ids(entorno):
    fuente, cripta, red = entorno
    guardar = red._pers_contenido.guardar
    def falla_segundo(cripta_id, sala_id, datos):
        if sala_id == 2:
            raise OSError('disco lleno')
        guardar(cripta_id, sala_id, datos)
    with patch.object(red._pers_contenido, 'guardar', side_effect=falla_segundo):
        with pytest.raises(OSError):
            red.solicitar_contenido_lote([1, 2])
    assert red._fabrica.siguiente_id == 1
    assert len(cripta.sala_por_id(1).objetos_suelo) == 0
    assert red.procesar_cola() == 2
    assert fuente.contenido == [[1, 2], [2]]
    assert next(cripta.sala_por_id(1).objetos_suelo.recorrer_valores()).instancia_id == 'objeto:1'


def test_lru_y_disco_permiten_recuperar_ficha_desalojada(tmp_path):
    from estructuras.listalru import ListaLRU
    p = PersistenciaCatalogo(tmp_path, 'v1')
    memoria = ListaLRU(capacidad=1)
    a, b = {'id': 'a'}, {'id': 'b'}
    p.guardar_ficha('a', a)
    assert memoria.insertar('a', a)
    memoria.marcar_en_uso('a')
    assert not memoria.insertar('b', b)
    assert memoria.buscar('a') is a
    memoria.desmarcar_en_uso('a')
    assert memoria.insertar('b', b)
    assert memoria.buscar('a') is None
    # Composición de componentes: el servicio Catálogo se integra en bloque 3.
    recuperada = p.cargar_ficha('a')
    assert recuperada == a
    assert memoria.insertar('a', recuperada)
    assert memoria.buscar('a') == a


def test_429_cuenta_y_presupuesto_impide_get_adicional():
    from adaptadores.datos_http import DatosHTTP
    from tests.test_datos_http import _mock_respuesta
    fuente = DatosHTTP()
    with patch('adaptadores.datos_http.requests.get', return_value=_mock_respuesta(200, {'presupuesto_solicitudes': 2})):
        fuente.datos_cripta('cripta-01')
    with patch('adaptadores.datos_http.requests.get', return_value=_mock_respuesta(429, {'reintentar_en': 0})) as get:
        with patch('adaptadores.datos_http.time.sleep'):
            with pytest.raises(RuntimeError, match='/criptas'):
                fuente.listar_criptas()
    assert get.call_count == 1
    assert fuente.requests_realizados == 2
