import json
import os
import tempfile
import unittest

from adaptadores.datos_offline import DatosOffline
from adaptadores.fuente_datos import FuenteDeDatos

CRIPTA = "cripta-01"
MAX_POR_LOTE = 10

class TestContrato(unittest.TestCase):
    # DatosOffline cumple la interfaz y devuelve los datos reales de la cripta.

    def setUp(self):
        self.offline = DatosOffline()

    # DatosOffline implementa todos los métodos de FuenteDeDatos.
    def test_es_una_fuente_de_datos(self):
        self.assertIsInstance(self.offline, FuenteDeDatos)

    def test_modo_es_offline(self):
        self.assertEqual(self.offline.modo(), "offline")

    # El listado debe incluir cripta-01, que está descargada en el repositorio.
    def test_listar_criptas(self):
        criptas = self.offline.listar_criptas()["criptas"]
        ids = [c["id"] for c in criptas]
        self.assertIn(CRIPTA, ids)

    # Comprueba los valores de la cripta y las estadísticas iniciales del jugador.
    def test_datos_cripta_valores_reales(self):
        datos = self.offline.datos_cripta(CRIPTA)
        self.assertEqual(datos["id"], CRIPTA)
        self.assertEqual(datos["llave_salida"], "itm_llave_negra")
        self.assertEqual(datos["sala_inicial"], 1)
        self.assertEqual(datos["sala_salida"], 6)
        self.assertEqual(datos["salas_total"], 6)
        for clave in ("vida_max", "ataque", "defensa", "velocidad"):
            self.assertIn(clave, datos["jugador"])

    # La salida de la sala 2 a la 5 requiere la llave de bronce
    # y se cierra automáticamente tras 500 unidades de tiempo.
    def test_esqueleto_valores_reales(self):
        esqueleto = self.offline.esqueleto_cripta(CRIPTA, 1)
        self.assertEqual(esqueleto["pagina"], 1)
        self.assertEqual(esqueleto["total_paginas"], 1)
        self.assertEqual(len(esqueleto["salas"]), 6)

        sala_2 = esqueleto["salas"][1]
        self.assertEqual(sala_2["id"], 2)
        salida_este = sala_2["salidas"]["E"]
        self.assertEqual(salida_este["sala"], 5)
        self.assertTrue(salida_este["cerrada"])
        self.assertEqual(salida_este["llave"], "itm_llave_bronce")
        self.assertEqual(salida_este["cierre_automatico"], 500)

    # La versión de la cripta debe coincidir con la de sus datos generales.
    def test_versiones(self):
        self.assertEqual(self.offline.version_cripta(CRIPTA)["version"],
                         self.offline.datos_cripta(CRIPTA)["version"])
        self.assertTrue(self.offline.version_catalogo()["version"])


class TestContenido(unittest.TestCase):
    """contenido_salas responde cualquier combinación de salas, no solo lotes guardados."""

    def setUp(self):
        self.offline = DatosOffline()

    # Lee el archivo de cada sala y devuelve el lote en el orden solicitado.
    def test_todas_las_salas(self):
        contenido = self.offline.contenido_salas(CRIPTA, [1, 2, 3, 4, 5, 6])["contenido"]
        self.assertEqual([s["sala"] for s in contenido], [1, 2, 3, 4, 5, 6])
        for sala in contenido:
            for clave in ("enemigos", "objetos", "trampas"):
                self.assertIn(clave, sala)

    # También admite consultas de una sola sala.
    def test_una_sola_sala(self):
        contenido = self.offline.contenido_salas(CRIPTA, [4])["contenido"]
        self.assertEqual(len(contenido), 1)
        sala_4 = contenido[0]
        self.assertEqual(sala_4["enemigos"][0]["instancia"], "e-401")
        self.assertEqual(sala_4["enemigos"][0]["tipo"], "ent_guardian_oseo")
        self.assertIn("itm_llave_negra", sala_4["objetos"])

    # Respeta el orden de los identificadores recibidos.
    def test_respeta_el_orden_pedido(self):
        contenido = self.offline.contenido_salas(CRIPTA, [3, 1])["contenido"]
        self.assertEqual([s["sala"] for s in contenido], [3, 1])

    # El API puede omitir la vida actual de un enemigo, como en e-401.
    def test_enemigo_puede_venir_sin_vida(self):
        # El juego toma vida_max del catálogo en este caso.
        guardian = self.offline.contenido_salas(CRIPTA, [4])["contenido"][0]["enemigos"][0]
        self.assertNotIn("vida", guardian)

    # Una sala inexistente debe producir FileNotFoundError e indicar su número.
    def test_sala_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            self.offline.contenido_salas(CRIPTA, [999])
        self.assertIn("sala_999", str(ctx.exception))


class TestCatalogo(unittest.TestCase):
    """catalogo responde cualquier combinación de fichas y conserva tildes."""

    def setUp(self):
        self.offline = DatosOffline()

    # Se pueden consultar fichas sueltas sin depender de un lote predefinido.
    def test_subconjunto_en_el_orden_pedido(self):
        entidades = self.offline.catalogo(["trp_dardos", "ent_rata_gigante"])["entidades"]
        self.assertEqual([f["id"] for f in entidades], ["trp_dardos", "ent_rata_gigante"])

     # Las tildes de guardián y daño deben conservarse al leer UTF-8.
    def test_tildes_y_enie(self):
        guardian = self.offline.catalogo(["ent_guardian_oseo"])["entidades"][0]
        self.assertEqual(guardian["comportamiento"], "guardián")
        dardos = self.offline.catalogo(["trp_dardos"])["entidades"][0]
        self.assertEqual(dardos["daño"], 4)

    # Una ficha inexistente debe producir FileNotFoundError.
    def test_id_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError):
            self.offline.catalogo(["itm_que_no_existe"])

    # También deben existir las fichas de los objetos que sueltan los enemigos.
    def test_cubre_todo_lo_que_aparece_en_la_cripta(self):
        # Todo tipo usado en el contenido (y lo que sueltan los enemigos) debe tener ficha
        contenido = self.offline.contenido_salas(CRIPTA, [1, 2, 3, 4, 5, 6])["contenido"]
        tipos = []
        for sala in contenido:
            for enemigo in sala["enemigos"]:
                if enemigo["tipo"] not in tipos:
                    tipos.append(enemigo["tipo"])
            for objeto in sala["objetos"]:
                if objeto not in tipos:
                    tipos.append(objeto)
            for trampa in sala["trampas"]:
                if trampa["tipo"] not in tipos:
                    tipos.append(trampa["tipo"])

        i = 0
        while i < len(tipos):
            lote = tipos[i:i + MAX_POR_LOTE]
            for ficha in self.offline.catalogo(lote)["entidades"]:
                for suelto in ficha.get("suelta", []):
                    if suelto not in tipos:
                        tipos.append(suelto)
            i += len(lote)


class TestValidaciones(unittest.TestCase):
    """Mismas reglas que el API: listas no vacías, máximo 10, página válida."""

    def setUp(self):
        self.offline = DatosOffline()

    def test_maximo_10_salas(self):
        with self.assertRaises(ValueError) as ctx:
            self.offline.contenido_salas(CRIPTA, list(range(1, 12)))
        self.assertIn("10", str(ctx.exception))

    def test_sala_ids_vacio(self):
        with self.assertRaises(ValueError):
            self.offline.contenido_salas(CRIPTA, [])

    def test_maximo_10_catalogo(self):
        with self.assertRaises(ValueError) as ctx:
            self.offline.catalogo([f"ent_{i}" for i in range(11)])
        self.assertIn("10", str(ctx.exception))

    # Un lote de fichas vacío no es una consulta válida.
    def test_tipo_ids_vacio(self):
        with self.assertRaises(ValueError):
            self.offline.catalogo([])

    # La numeración de páginas empieza en 1.
    def test_pagina_invalida(self):
        with self.assertRaises(ValueError):
            self.offline.esqueleto_cripta(CRIPTA, 0)

    # Una página sin archivo local debe producir FileNotFoundError.
    def test_pagina_que_no_existe(self):
        with self.assertRaises(FileNotFoundError):
            self.offline.esqueleto_cripta(CRIPTA, 2)


class TestCarpeta(unittest.TestCase):
    """la carpeta de datos se puede elegir y no depende de dónde se ejecute Python."""

    # El constructor debe informar si la carpeta indicada no existe.
    def test_carpeta_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            DatosOffline("carpeta_que_no_existe_xyz")
        mensaje = str(ctx.exception)
        self.assertIn("carpeta_que_no_existe_xyz", mensaje)
        self.assertIn("Verifica", mensaje)

    # El error debe identificar tanto la cripta como el archivo que falta.
    def test_archivo_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            DatosOffline().datos_cripta("cripta-inexistente")
        mensaje = str(ctx.exception)
        self.assertIn("cripta-inexistente", mensaje)
        self.assertIn("general.json", mensaje)

    # el constructor lee de la carpeta que se le pase (usa una carpeta temporal).
    def test_carpeta_personalizada(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with open(os.path.join(carpeta, "criptas.json"), "w", encoding="utf-8") as f:
                json.dump({"criptas": [{"id": "cripta-prueba"}]}, f)
            # listar_criptas solo ofrece criptas descargadas (con su general.json).
            os.makedirs(os.path.join(carpeta, "cripta-prueba"))
            with open(os.path.join(carpeta, "cripta-prueba", "general.json"), "w",
                      encoding="utf-8") as f:
                json.dump({"id": "cripta-prueba"}, f)
            offline = DatosOffline(carpeta)
            self.assertEqual(offline.listar_criptas()["criptas"][0]["id"], "cripta-prueba")

    # el menú offline no ofrece criptas listadas pero no descargadas.
    def test_listar_criptas_omite_las_no_descargadas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with open(os.path.join(carpeta, "criptas.json"), "w", encoding="utf-8") as f:
                json.dump({"criptas": [{"id": "c-bajada", "nombre": "A"},
                                       {"id": "c-falta", "nombre": "B"}]}, f)
            os.makedirs(os.path.join(carpeta, "c-bajada"))
            with open(os.path.join(carpeta, "c-bajada", "general.json"), "w",
                      encoding="utf-8") as f:
                json.dump({"id": "c-bajada"}, f)
            offline = DatosOffline(carpeta)
            ids = [c["id"] for c in offline.listar_criptas()["criptas"]]
            self.assertEqual(ids, ["c-bajada"])
            # El archivo original no se modifica.
            with open(os.path.join(carpeta, "criptas.json"), encoding="utf-8") as f:
                self.assertEqual(len(json.load(f)["criptas"]), 2)

    # si ninguna está descargada, el error dice cómo descargar una.
    def test_listar_criptas_sin_ninguna_descargada_explica_que_hacer(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with open(os.path.join(carpeta, "criptas.json"), "w", encoding="utf-8") as f:
                json.dump({"criptas": [{"id": "c-falta", "nombre": "B"}]}, f)
            with self.assertRaises(FileNotFoundError) as ctx:
                DatosOffline(carpeta).listar_criptas()
            self.assertIn("descargar_offline", str(ctx.exception))

    # funciona aunque Python se ejecute desde otra carpeta (ruta desde __file__).
    def test_no_depende_del_directorio_actual(self):
        directorio_original = os.getcwd()
        with tempfile.TemporaryDirectory() as otro_directorio:
            try:
                os.chdir(otro_directorio)
                datos = DatosOffline().datos_cripta(CRIPTA)
                self.assertEqual(datos["id"], CRIPTA)
            finally:
                os.chdir(directorio_original)


if __name__ == "__main__":
    unittest.main()
