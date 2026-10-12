"""Pruebas de integración del bloque 2: persistencia de contenido, lectura
offline con la estructura real de datos_offline/, carga del esqueleto
completo de una cripta y el Actor base.

No se hacen requests reales: todo se apoya en DatosOffline (lectura de
disco) y en carpetas temporales para la persistencia.
"""

import json
import os
import shutil
import tempfile
import unittest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_red import cargar_esqueleto_completo
from modelo.entidades.actor import Actor
from modelo.mundo.cripta_modelo import CriptaModelo
from persistencia.contenido import PersistenciaContenido

CRIPTA = "cripta-01"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_OFFLINE = os.path.join(RAIZ, "datos_offline")


class TestPersistenciaContenido(unittest.TestCase):
    """Grupo 1 — PersistenciaContenido guarda y recupera contenido de salas."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.version = "v1"

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _escribir_version(self, carpeta, cripta_id, version):
        ruta = os.path.join(carpeta, cripta_id)
        os.makedirs(ruta, exist_ok=True)
        with open(os.path.join(ruta, "version.json"), "w", encoding="utf-8") as f:
            json.dump({"version": version}, f)

    def test_guardar_y_cargar_sala(self):
        self._escribir_version(self.carpeta, CRIPTA, self.version)
        persistencia = PersistenciaContenido(self.carpeta, self.version)

        datos = {"sala": 2, "enemigos": [], "objetos": [], "trampas": []}
        persistencia.guardar(CRIPTA, 2, datos)

        resultado = persistencia.cargar(CRIPTA, 2)
        self.assertEqual(resultado, datos)

    def test_cargar_version_vencida_retorna_none(self):
        self._escribir_version(self.carpeta, CRIPTA, "v1")
        persistencia_guarda = PersistenciaContenido(self.carpeta, "v1")
        persistencia_guarda.guardar(CRIPTA, 2, {"sala": 2})

        persistencia_vieja = PersistenciaContenido(self.carpeta, "v2")
        self.assertIsNone(persistencia_vieja.cargar(CRIPTA, 2))

    def test_cargar_sala_inexistente_retorna_none(self):
        self._escribir_version(self.carpeta, CRIPTA, self.version)
        persistencia = PersistenciaContenido(self.carpeta, self.version)

        self.assertIsNone(persistencia.cargar(CRIPTA, 99))

    def test_guardar_crea_carpetas_automaticamente(self):
        carpeta_nueva = os.path.join(self.carpeta, "no_existe_todavia")
        self.assertFalse(os.path.exists(carpeta_nueva))

        persistencia = PersistenciaContenido(carpeta_nueva, self.version)
        persistencia.guardar(CRIPTA, 3, {"sala": 3})

        ruta_esperada = os.path.join(
            carpeta_nueva, CRIPTA, "contenido", "sala_3.json"
        )
        self.assertTrue(os.path.exists(ruta_esperada))


class TestDatosOfflineEstructuraReal(unittest.TestCase):
    """Grupo 2 — DatosOffline lee la estructura real de datos_offline/."""

    def setUp(self):
        self.offline = DatosOffline()

    def test_offline_lee_sala_correctamente(self):
        contenido = self.offline.contenido_salas(CRIPTA, [2])["contenido"]
        sala_2 = contenido[0]
        self.assertEqual(sala_2["sala"], 2)
        self.assertTrue(len(sala_2["enemigos"]) > 0)

    def test_offline_lee_ficha_catalogo(self):
        ficha = self.offline.catalogo(["ent_rata_gigante"])["entidades"][0]
        self.assertEqual(ficha["clase"], "enemigo")
        self.assertIn(ficha["comportamiento"], ("rastreador", "guardián"))

    def test_offline_version_cripta_coincide_con_general(self):
        version_archivo = self.offline.version_cripta(CRIPTA)["version"]
        version_general = self.offline.datos_cripta(CRIPTA)["version"]
        self.assertEqual(version_archivo, version_general)


class TestEsqueletoCompleto(unittest.TestCase):
    """Grupo 3 — carga del esqueleto completo de una cripta desde la fuente."""

    def setUp(self):
        self.offline = DatosOffline()
        self.cripta = cargar_esqueleto_completo(self.offline, CRIPTA)

    def test_cargar_esqueleto_desde_offline(self):
        self.assertIsInstance(self.cripta, CriptaModelo)
        self.assertEqual(len(self.cripta), 6)
        self.assertEqual(self.cripta.sala_inicial_id, 1)
        self.assertEqual(self.cripta.sala_salida_id, 6)

    def test_cripta_modelo_salas_tienen_salidas(self):
        sala_2 = self.cripta.sala_por_id(2)
        for direccion in ("N", "S", "E"):
            self.assertIsNotNone(sala_2.salida_hacia(direccion))

        sala_1 = self.cripta.sala_por_id(1)
        self.assertIsNotNone(sala_1.salida_hacia("N"))

    def test_cripta_modelo_sala_por_id(self):
        sala_3 = self.cripta.sala_por_id(3)
        self.assertIsNotNone(sala_3)
        self.assertEqual(sala_3.nombre, "Cripta baja")


class TestActorBase(unittest.TestCase):
    """Grupo 4 — comportamiento básico compartido por jugador y enemigos."""

    def _actor(self, vida_max=30, vida=None, ataque=5, defensa=2, velocidad=100):
        return Actor(
            instancia_id="a-1",
            vida_max=vida_max,
            ataque=ataque,
            defensa=defensa,
            velocidad=velocidad,
            vida=vida,
        )

    def test_actor_recibir_dano(self):
        actor = self._actor(vida_max=30, vida=30)
        actor.recibir_dano(10)
        self.assertEqual(actor.vida, 20)

    def test_actor_dano_no_baja_de_cero(self):
        actor = self._actor(vida_max=30, vida=5)
        actor.recibir_dano(100)
        self.assertEqual(actor.vida, 0)
        self.assertFalse(actor.vivo)

    def test_actor_curar_no_supera_vida_max(self):
        actor = self._actor(vida_max=30, vida=20)
        actor.curar(100)
        self.assertEqual(actor.vida, 30)

    def test_actor_morir_cancela_evento(self):
        actor = self._actor()

        class EventoMock:
            valido = True

        evento = EventoMock()
        actor.evento_actual = evento
        actor.morir()

        self.assertFalse(actor.vivo)
        self.assertFalse(evento.valido)


class TestFlujoIntegracion(unittest.TestCase):
    """Grupo 5 — el flujo offline completo funciona de punta a punta."""

    def setUp(self):
        self.carpeta_temporal = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.carpeta_temporal, ignore_errors=True)

    def test_flujo_offline_completo(self):
        offline = DatosOffline()

        cripta = cargar_esqueleto_completo(offline, CRIPTA)
        self.assertIsInstance(cripta, CriptaModelo)

        sala_2 = offline.contenido_salas(CRIPTA, [2])["contenido"][0]
        self.assertTrue(len(sala_2["enemigos"]) > 0)

        ficha_rata = offline.catalogo(["ent_rata_gigante"])["entidades"][0]
        self.assertGreater(ficha_rata["vida_max"], 0)
        if ficha_rata["comportamiento"] == "guardián":
            self.assertIn("á", ficha_rata["comportamiento"])

    def test_persistencia_contenido_con_datos_reales(self):
        ruta_sala_2 = os.path.join(
            CARPETA_OFFLINE, CRIPTA, "contenido", "sala_2.json"
        )
        with open(ruta_sala_2, "r", encoding="utf-8") as f:
            datos_originales = json.load(f)

        version = "v-real"
        ruta_version = os.path.join(self.carpeta_temporal, CRIPTA)
        os.makedirs(ruta_version, exist_ok=True)
        with open(
            os.path.join(ruta_version, "version.json"), "w", encoding="utf-8"
        ) as f:
            json.dump({"version": version}, f)

        persistencia = PersistenciaContenido(self.carpeta_temporal, version)
        persistencia.guardar(CRIPTA, 2, datos_originales)

        datos_cargados = persistencia.cargar(CRIPTA, 2)
        self.assertEqual(datos_cargados, datos_originales)


if __name__ == "__main__":
    unittest.main()
