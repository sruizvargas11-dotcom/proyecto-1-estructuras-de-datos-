"""Pruebas unitarias de persistencia/contenido.py y persistencia/catalogo.py.

Todo corre sobre carpetas temporales (tempfile.mkdtemp) y se limpia en
tearDown. Los datos de datos_offline/ se leen tal cual están en disco,
nunca se modifican ni se copian hacia el repositorio.
"""

import json
import os
import shutil
import tempfile
import unittest

from persistencia.contenido import PersistenciaContenido
from persistencia.catalogo import PersistenciaCatalogo

CRIPTA = "cripta-01"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_OFFLINE = os.path.join(RAIZ, "datos_offline")

RUTA_VERSION_CRIPTA = os.path.join(CARPETA_OFFLINE, CRIPTA, "version.json")
RUTA_SALA_2 = os.path.join(CARPETA_OFFLINE, CRIPTA, "contenido", "sala_2.json")
RUTA_VERSION_CATALOGO = os.path.join(CARPETA_OFFLINE, "catalogo_version.json")
RUTA_FICHA_RATA = os.path.join(CARPETA_OFFLINE, "catalogo", "ent_rata_gigante.json")
RUTA_FICHA_DAGA = os.path.join(CARPETA_OFFLINE, "catalogo", "itm_daga_oxidada.json")


class TestPersistenciaContenido(unittest.TestCase):
    """Grupo 1 — guardar y recuperar contenido de salas."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _escribir_version_cripta(self, version):
        """Simula version.json de una cripta en la carpeta temporal."""
        ruta = os.path.join(self.carpeta, CRIPTA)
        os.makedirs(ruta, exist_ok=True)
        with open(os.path.join(ruta, "version.json"), "w", encoding="utf-8") as f:
            json.dump({"version": version}, f)

    def test_guardar_y_cargar_sala(self):
        """Copia el version.json real para simular la versión vigente."""
        destino = os.path.join(self.carpeta, CRIPTA, "version.json")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy(RUTA_VERSION_CRIPTA, destino)

        with open(destino, "r", encoding="utf-8") as f:
            version_vigente = json.load(f)["version"]

        persistencia = PersistenciaContenido(self.carpeta, version_vigente)

        datos = {"sala": 2, "enemigos": [], "objetos": [], "trampas": []}
        persistencia.guardar(CRIPTA, 2, datos)

        resultado = persistencia.cargar(CRIPTA, 2)
        self.assertEqual(resultado, datos)

    def test_version_vencida_retorna_none(self):
        self._escribir_version_cripta("version_vieja")
        persistencia_guarda = PersistenciaContenido(self.carpeta, "version_vieja")
        persistencia_guarda.guardar(CRIPTA, 2, {"sala": 2})

        persistencia_vieja = PersistenciaContenido(self.carpeta, "version_nueva")
        self.assertIsNone(persistencia_vieja.cargar(CRIPTA, 2))

    def test_sala_inexistente_retorna_none(self):
        """Carpeta vacía, sin version.json: no debe lanzar excepción."""
        persistencia = PersistenciaContenido(self.carpeta, "cualquier_version")
        self.assertIsNone(persistencia.cargar(CRIPTA, 99))

    def test_guardar_crea_carpetas_automaticamente(self):
        carpeta_nueva = os.path.join(self.carpeta, "no_existe_todavia")
        self.assertFalse(os.path.exists(carpeta_nueva))

        persistencia = PersistenciaContenido(carpeta_nueva, "version_cualquiera")
        persistencia.guardar(CRIPTA, 3, {"sala": 3})

        ruta_esperada = os.path.join(carpeta_nueva, CRIPTA, "contenido", "sala_3.json")
        self.assertTrue(os.path.exists(ruta_esperada))

    def test_contenido_guardado_es_identico_al_original(self):
        with open(RUTA_SALA_2, "r", encoding="utf-8") as f:
            datos_originales = json.load(f)

        destino = os.path.join(self.carpeta, CRIPTA, "version.json")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy(RUTA_VERSION_CRIPTA, destino)
        with open(destino, "r", encoding="utf-8") as f:
            version_vigente = json.load(f)["version"]

        persistencia = PersistenciaContenido(self.carpeta, version_vigente)
        persistencia.guardar(CRIPTA, 2, datos_originales)

        datos_cargados = persistencia.cargar(CRIPTA, 2)
        self.assertEqual(datos_cargados, datos_originales)


class TestPersistenciaCatalogo(unittest.TestCase):
    """Grupo 2 — guardar y recuperar fichas del catálogo."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _escribir_version_catalogo(self, version):
        """PersistenciaCatalogo.version_catalogo() devuelve el JSON tal
        cual está en disco, así que lo que se escriba aquí debe
        coincidir exactamente con lo que se pase al constructor."""
        ruta = os.path.join(self.carpeta, "catalogo_version.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(version, f)

    def test_guardar_y_cargar_ficha(self):
        """Copia el catalogo_version.json real para simular la versión vigente."""
        destino = os.path.join(self.carpeta, "catalogo_version.json")
        shutil.copy(RUTA_VERSION_CATALOGO, destino)

        with open(destino, "r", encoding="utf-8") as f:
            version_vigente = json.load(f)

        with open(RUTA_FICHA_RATA, "r", encoding="utf-8") as f:
            ficha = json.load(f)

        persistencia = PersistenciaCatalogo(self.carpeta, version_vigente)
        persistencia.guardar_ficha("ent_rata_gigante", ficha)

        resultado = persistencia.cargar_ficha("ent_rata_gigante")
        self.assertEqual(resultado, ficha)

    def test_version_catalogo_vencida_retorna_none(self):
        self._escribir_version_catalogo("v_vieja")
        persistencia_guarda = PersistenciaCatalogo(self.carpeta, "v_vieja")
        persistencia_guarda.guardar_ficha("ent_rata_gigante", {"id": "ent_rata_gigante"})

        persistencia_nueva = PersistenciaCatalogo(self.carpeta, "v_nueva")
        self.assertIsNone(persistencia_nueva.cargar_ficha("ent_rata_gigante"))

    def test_ficha_inexistente_retorna_none(self):
        """Versión vigente coincide, pero la ficha nunca se guardó."""
        self._escribir_version_catalogo("v1")
        persistencia = PersistenciaCatalogo(self.carpeta, "v1")

        self.assertIsNone(persistencia.cargar_ficha("tipo_que_no_existe"))

    def test_guardar_crea_carpetas_catalogo(self):
        carpeta_nueva = os.path.join(self.carpeta, "no_existe_aun")
        self.assertFalse(os.path.exists(carpeta_nueva))

        persistencia = PersistenciaCatalogo(carpeta_nueva, "v1")
        persistencia.guardar_ficha("ent_rata_gigante", {"id": "ent_rata_gigante"})

        ruta_esperada = os.path.join(carpeta_nueva, "catalogo", "ent_rata_gigante.json")
        self.assertTrue(os.path.exists(ruta_esperada))

    def test_ficha_guardada_es_identica_al_original(self):
        with open(RUTA_FICHA_RATA, "r", encoding="utf-8") as f:
            ficha_original = json.load(f)

        self._escribir_version_catalogo("v1")
        persistencia = PersistenciaCatalogo(self.carpeta, "v1")
        persistencia.guardar_ficha("ent_rata_gigante", ficha_original)

        ficha_cargada = persistencia.cargar_ficha("ent_rata_gigante")
        self.assertEqual(ficha_cargada, ficha_original)

    def test_multiples_fichas_independientes(self):
        with open(RUTA_FICHA_RATA, "r", encoding="utf-8") as f:
            ficha_rata = json.load(f)
        with open(RUTA_FICHA_DAGA, "r", encoding="utf-8") as f:
            ficha_daga = json.load(f)

        self._escribir_version_catalogo("v1")
        persistencia = PersistenciaCatalogo(self.carpeta, "v1")

        persistencia.guardar_ficha("ent_rata_gigante", ficha_rata)
        persistencia.guardar_ficha("itm_daga_oxidada", ficha_daga)

        rata_cargada = persistencia.cargar_ficha("ent_rata_gigante")
        daga_cargada = persistencia.cargar_ficha("itm_daga_oxidada")

        self.assertEqual(rata_cargada, ficha_rata)
        self.assertEqual(daga_cargada, ficha_daga)
        self.assertNotEqual(rata_cargada, daga_cargada)


class TestIntegracionContenidoCatalogo(unittest.TestCase):
    """Grupo 3 — PersistenciaContenido y PersistenciaCatalogo conviven
    en la misma carpeta base sin interferirse."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _escribir_version_cripta(self, version):
        ruta = os.path.join(self.carpeta, CRIPTA)
        os.makedirs(ruta, exist_ok=True)
        with open(os.path.join(ruta, "version.json"), "w", encoding="utf-8") as f:
            json.dump({"version": version}, f)

    def _escribir_version_catalogo(self, version):
        ruta = os.path.join(self.carpeta, "catalogo_version.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(version, f)

    def test_contenido_y_catalogo_en_misma_carpeta(self):
        self._escribir_version_cripta("v_cripta")
        self._escribir_version_catalogo("v_catalogo")

        contenido = PersistenciaContenido(self.carpeta, "v_cripta")
        catalogo = PersistenciaCatalogo(self.carpeta, "v_catalogo")

        datos_sala = {"sala": 2, "enemigos": [], "objetos": [], "trampas": []}
        ficha = {"id": "ent_rata_gigante", "nombre": "Rata gigante"}

        contenido.guardar(CRIPTA, 2, datos_sala)
        catalogo.guardar_ficha("ent_rata_gigante", ficha)

        self.assertEqual(contenido.cargar(CRIPTA, 2), datos_sala)
        self.assertEqual(catalogo.cargar_ficha("ent_rata_gigante"), ficha)

        # Cada uno vive en su propio árbol de carpetas, sin mezclarse.
        ruta_sala = os.path.join(self.carpeta, CRIPTA, "contenido", "sala_2.json")
        ruta_ficha = os.path.join(self.carpeta, "catalogo", "ent_rata_gigante.json")
        self.assertTrue(os.path.exists(ruta_sala))
        self.assertTrue(os.path.exists(ruta_ficha))

    def test_version_cripta_no_afecta_catalogo(self):
        self._escribir_version_cripta("v1")
        self._escribir_version_catalogo("v_catalogo")

        contenido = PersistenciaContenido(self.carpeta, "v1")
        catalogo = PersistenciaCatalogo(self.carpeta, "v_catalogo")

        contenido.guardar(CRIPTA, 2, {"sala": 2})
        ficha = {"id": "ent_rata_gigante", "nombre": "Rata gigante"}
        catalogo.guardar_ficha("ent_rata_gigante", ficha)

        # La versión de la cripta cambia (p. ej. el mapa se actualizó)...
        self._escribir_version_cripta("v2")

        # ...el contenido cacheado con la versión anterior queda invalidado...
        self.assertIsNone(contenido.cargar(CRIPTA, 2))

        # ...pero el catálogo es independiente y sigue sirviendo la ficha.
        self.assertEqual(catalogo.cargar_ficha("ent_rata_gigante"), ficha)


if __name__ == "__main__":
    unittest.main()
