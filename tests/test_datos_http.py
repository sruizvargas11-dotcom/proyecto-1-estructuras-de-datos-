"""Tests de DatosHTTP usando unittest.mock — sin requests reales."""

import unittest
from unittest.mock import MagicMock, patch

from adaptadores.datos_http import DatosHTTP


def _mock_respuesta(status_code: int, json_data: dict, text: str = ""):
    respuesta = MagicMock()
    respuesta.status_code = status_code
    respuesta.json.return_value = json_data
    respuesta.text = text
    return respuesta


class TestDatosHTTP(unittest.TestCase):

    @patch("adaptadores.datos_http.requests.get")
    def test_get_exitoso(self, mock_get):
        mock_get.return_value = _mock_respuesta(200, {"criptas": []})

        http = DatosHTTP()
        resultado = http.listar_criptas()

        self.assertEqual(resultado, {"criptas": []})
        self.assertEqual(http.requests_realizados, 1)

    @patch("adaptadores.datos_http.time.sleep")
    @patch("adaptadores.datos_http.requests.get")
    def test_maneja_429_y_reintenta(self, mock_get, mock_sleep):
        respuesta_429 = _mock_respuesta(429, {"reintentar_en": 2})
        respuesta_200 = _mock_respuesta(200, {"criptas": []})
        mock_get.side_effect = [respuesta_429, respuesta_200]

        http = DatosHTTP()
        resultado = http.listar_criptas()

        self.assertEqual(resultado, {"criptas": []})
        self.assertEqual(http.requests_realizados, 2)
        mock_sleep.assert_called_once_with(2)

    @patch("adaptadores.datos_http.requests.get")
    def test_error_500_lanza_excepcion_con_contexto(self, mock_get):
        mock_get.return_value = _mock_respuesta(500, {}, text="error interno")

        http = DatosHTTP()
        with self.assertRaises(RuntimeError) as ctx:
            http.listar_criptas()

        mensaje = str(ctx.exception)
        self.assertIn("/criptas", mensaje)
        self.assertIn("500", mensaje)
        self.assertIn("error interno", mensaje)

    @patch("adaptadores.datos_http.requests.get")
    def test_maximo_10_salas_lanza_error(self, mock_get):
        http = DatosHTTP()
        sala_ids = list(range(1, 12))

        with self.assertRaises(ValueError):
            http.contenido_salas("cripta-01", sala_ids)

        mock_get.assert_not_called()
        self.assertEqual(http.requests_realizados, 0)

    @patch("adaptadores.datos_http.requests.get")
    def test_maximo_10_catalogo_lanza_error(self, mock_get):
        http = DatosHTTP()
        tipo_ids = [f"ent_{i}" for i in range(11)]

        with self.assertRaises(ValueError):
            http.catalogo(tipo_ids)

        mock_get.assert_not_called()

    @patch("adaptadores.datos_http.requests.get")
    def test_presupuesto_se_fija_en_datos_cripta(self, mock_get):
        mock_get.return_value = _mock_respuesta(
            200, {"id": "cripta-01", "presupuesto_solicitudes": 9}
        )

        http = DatosHTTP()
        http.datos_cripta("cripta-01")

        self.assertEqual(http.presupuesto, 9)

    def test_uuid_se_genera_una_sola_vez(self):
        http1 = DatosHTTP()
        http2 = DatosHTTP()

        self.assertIsNotNone(http1.reporte()["client_id"])
        self.assertIsNotNone(http2.reporte()["client_id"])
        self.assertNotEqual(http1.reporte()["client_id"], http2.reporte()["client_id"])


if __name__ == "__main__":
    unittest.main()
