"""Contrato de 429: duración del servidor, presupuesto y cierre cancelable."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest

from adaptadores.datos_http import DatosHTTP


def respuesta(estado, datos):
    return Mock(status_code=estado, json=Mock(return_value=datos))


@pytest.mark.parametrize('segundos', [61, 120, 3600, 10**100])
def test_espera_del_servidor_no_tiene_un_tope_arbitrario(segundos):
    fuente = DatosHTTP()
    with patch('adaptadores.datos_http.requests.get', side_effect=[
            respuesta(429, {'reintentar_en': segundos}), respuesta(200, {'criptas': []})]), \
            patch.object(fuente, '_esperar_reintento') as esperar:
        assert fuente.listar_criptas() == {'criptas': []}
    esperar.assert_called_once_with(segundos)
    assert fuente.requests_realizados == 2


def test_429_repetidos_pueden_recuperarse_sin_limite_arbitrario_por_defecto():
    fuente = DatosHTTP()
    respuestas = [respuesta(429, {'reintentar_en': 0}) for _ in range(5)]
    respuestas.append(respuesta(200, {'criptas': []}))
    with patch('adaptadores.datos_http.requests.get', side_effect=respuestas):
        assert fuente.listar_criptas() == {'criptas': []}
    assert fuente.requests_realizados == 6


def test_espera_larga_se_divide_sin_acortar_su_duracion():
    fuente = DatosHTTP()
    with patch.object(fuente._cancelacion, 'wait', return_value=False) as esperar:
        fuente._esperar_reintento(75)
    assert [llamada.args[0] for llamada in esperar.call_args_list] == [30, 30, 15]


def test_cancelar_no_hace_solicitudes_y_una_nueva_partida_no_hereda_cancelacion():
    fuente = DatosHTTP()
    fuente.cancelar_pendientes()
    with patch('adaptadores.datos_http.requests.get') as get:
        with pytest.raises(RuntimeError, match='/criptas.*cancelada'):
            fuente.listar_criptas()
    get.assert_not_called()
    assert fuente.requests_realizados == 0
    nueva = fuente.para_nueva_partida()
    assert not nueva._cancelacion.is_set()
    assert nueva._client_id == fuente._client_id


@pytest.mark.parametrize('espera', [True, -1, float('nan'), float('inf'), '120', None])
def test_espera_invalida_informa_la_operacion(espera):
    fuente = DatosHTTP()
    with patch('adaptadores.datos_http.requests.get', return_value=respuesta(429, {'reintentar_en': espera})):
        with pytest.raises(ValueError, match='GET /criptas.*reintentar_en'):
            fuente.listar_criptas()
    assert fuente.requests_realizados == 1


def test_solicitudes_concurrentes_no_exceden_el_presupuesto():
    fuente = DatosHTTP()
    with patch('adaptadores.datos_http.requests.get', return_value=respuesta(200, {'presupuesto_solicitudes': 2})):
        fuente.datos_cripta('prueba')
    def consultar(_):
        try:
            fuente.version_cripta('prueba')
            return True
        except RuntimeError:
            return False
    with patch('adaptadores.datos_http.requests.get', return_value=respuesta(200, {'version': 'v1'})) as get:
        with ThreadPoolExecutor(max_workers=12) as hilos:
            resultados = list(hilos.map(consultar, range(24)))
    assert sum(resultados) == 1 and get.call_count == 1
    assert fuente.requests_realizados == 2 and fuente.dentro_del_presupuesto
