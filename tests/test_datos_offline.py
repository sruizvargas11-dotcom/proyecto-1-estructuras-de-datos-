"""Tests de DatosOffline — sin requests reales, todo se lee desde disco."""

import unittest
from unittest.mock import patch

from adaptadores.datos_offline import DatosOffline


class TestDatosOffline(unittest.TestCase):

    def test_listar_criptas(self):
        offline = DatosOffline()
        resultado = offline.listar_criptas()

        self.assertIsInstance(resultado, dict)
        self.assertIn("criptas", resultado)
        self.assertGreaterEqual(len(resultado["criptas"]), 1)

        primera = resultado["criptas"][0]
        self.assertIn("id", primera)
        self.assertIn("nombre", primera)

    def test_datos_cripta(self):
        offline = DatosOffline()
        datos = offline.datos_cripta("cripta-01")

        for clave in (
            "version",
            "sala_inicial",
            "sala_salida",
            "presupuesto_solicitudes",
            "inventario_max",
            "jugador",
        ):
            self.assertIn(clave, datos)

        jugador = datos["jugador"]
        for clave in ("vida_max", "ataque", "defensa", "velocidad"):
            self.assertIn(clave, jugador)

    def test_esqueleto_cripta(self):
        offline = DatosOffline()
        esqueleto = offline.esqueleto_cripta("cripta-01", 1)

        self.assertIn("pagina", esqueleto)
        self.assertIn("total_paginas", esqueleto)
        self.assertIsInstance(esqueleto["salas"], list)

        for sala in esqueleto["salas"]:
            self.assertIn("id", sala)
            self.assertIn("nombre", sala)
            self.assertIn("salidas", sala)

    def test_contenido_salas(self):
        offline = DatosOffline()
        contenido = offline.contenido_salas("cripta-01", [1, 2, 3, 4, 5, 6])

        self.assertIn("contenido", contenido)
        for elemento in contenido["contenido"]:
            self.assertIn("sala", elemento)
            self.assertIn("enemigos", elemento)
            self.assertIn("objetos", elemento)
            self.assertIn("trampas", elemento)

    def test_catalogo(self):
        offline = DatosOffline()
        tipo_ids = [
            "ent_rata_gigante",
            "itm_antorcha",
            "itm_coraza_cuero",
            "itm_daga_oxidada",
            "itm_llave_bronce",
            "trp_dardos",
        ]
        fichas = offline.catalogo(tipo_ids)

        self.assertIn("entidades", fichas)
        for entidad in fichas["entidades"]:
            self.assertIn("id", entidad)
            self.assertIn("clase", entidad)

    def test_version_cripta(self):
        offline = DatosOffline()
        version = offline.version_cripta("cripta-01")

        self.assertIn("version", version)
        self.assertTrue(version["version"])

    def test_version_catalogo(self):
        offline = DatosOffline()
        version = offline.version_catalogo()

        self.assertIn("version", version)
        self.assertTrue(version["version"])

    def test_carpeta_inexistente_lanza_error(self):
        with patch.object(DatosOffline, "CARPETA", "carpeta_que_no_existe_xyz"):
            with self.assertRaises(FileNotFoundError) as ctx:
                DatosOffline()

        mensaje = str(ctx.exception)
        self.assertIn("carpeta_que_no_existe_xyz", mensaje)
        self.assertIn("Verifica", mensaje)

    def test_archivo_inexistente_lanza_error(self):
        offline = DatosOffline()

        with self.assertRaises(FileNotFoundError) as ctx:
            offline.datos_cripta("cripta-inexistente")

        mensaje = str(ctx.exception)
        self.assertIn("cripta-inexistente_general.json", mensaje)

    def test_maximo_10_salas_lanza_error(self):
        offline = DatosOffline()

        with self.assertRaises(ValueError) as ctx:
            offline.contenido_salas("cripta-01", list(range(1, 12)))

        self.assertIn("10", str(ctx.exception))

    def test_sala_ids_vacio_lanza_error(self):
        offline = DatosOffline()

        with self.assertRaises(ValueError):
            offline.contenido_salas("cripta-01", [])

    def test_maximo_10_catalogo_lanza_error(self):
        offline = DatosOffline()
        tipo_ids = [f"ent_{i}" for i in range(11)]

        with self.assertRaises(ValueError) as ctx:
            offline.catalogo(tipo_ids)

        self.assertIn("10", str(ctx.exception))

    def test_modo_es_offline(self):
        offline = DatosOffline()

        self.assertEqual(offline.modo(), "offline")


if __name__ == "__main__":
    unittest.main()
