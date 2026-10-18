"""F2-03: errores al leer JSON deben identificar la operación HTTP."""
from unittest.mock import Mock, patch

import pytest
import requests

from adaptadores.datos_http import DatosHTTP


@pytest.mark.parametrize('estado', [200, 429])
def test_json_ilegible_informa_operacion_estado_y_cuenta_intento(estado):
    respuesta = Mock(status_code=estado)
    respuesta.json.side_effect = requests.exceptions.JSONDecodeError(
        'Expecting value', '<html>error</html>', 0)
    fuente = DatosHTTP()
    with patch('adaptadores.datos_http.requests.get', return_value=respuesta), \
            patch('adaptadores.datos_http.time.sleep') as esperar:
        with pytest.raises(ValueError) as error:
            fuente.listar_criptas()
    mensaje = str(error.value)
    assert 'GET /criptas' in mensaje
    assert str(estado) in mensaje and 'JSON' in mensaje
    assert fuente.requests_realizados == 1
    assert isinstance(error.value.__cause__, requests.exceptions.JSONDecodeError)
    esperar.assert_not_called()
