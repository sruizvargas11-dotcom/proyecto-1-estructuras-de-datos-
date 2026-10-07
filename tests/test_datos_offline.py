import json
import os
import tempfile
import unittest

from adaptadores.datos_offline import DatosOffline
from adaptadores.fuente_datos import FuenteDeDatos

CRIPTA = "cripta-01"
MAX_POR_LOTE = 10

# QUE CAMBIO:
# se dividieron los metodos de prueba en clases
# estas clases representan un tipo de test

# porfa eliminar los comentarios encima de cada metodo para confirmar lectura!! 

class TestContrato(unittest.TestCase):
    # DatosOffline cumple la interfaz y devuelve los datos reales de la cripta.

    def setUp(self):
        self.offline = DatosOffline()

    # NUEVO: comprueba que DatosOffline cumple la interfaz FuenteDeDatos 
    def test_es_una_fuente_de_datos(self):
        self.assertIsInstance(self.offline, FuenteDeDatos)

    def test_modo_es_offline(self):
        self.assertEqual(self.offline.modo(), "offline")

    # MODIFICADO (original: test_listar_criptas). Antes solo revisaba que la
    # respuesta tuviera las claves 'criptas', 'id' y 'nombre'. Ahora comprueba
    # que cripta-01 aparezca en la lista.
    def test_listar_criptas(self):
        criptas = self.offline.listar_criptas()["criptas"]
        ids = [c["id"] for c in criptas]
        self.assertIn(CRIPTA, ids)

    # MODIFICADO (original: test_datos_cripta). Antes solo revisaba que existieran
    # las claves; con datos inventados también pasaba. Ahora revisa los valores
    # reales (llave_salida, salas inicial/salida/total) y las stats del jugador.
    def test_datos_cripta_valores_reales(self):
        datos = self.offline.datos_cripta(CRIPTA)
        self.assertEqual(datos["id"], CRIPTA)
        self.assertEqual(datos["llave_salida"], "itm_llave_negra")
        self.assertEqual(datos["sala_inicial"], 1)
        self.assertEqual(datos["sala_salida"], 6)
        self.assertEqual(datos["salas_total"], 6)
        for clave in ("vida_max", "ataque", "defensa", "velocidad"):
            self.assertIn(clave, datos["jugador"])

    # MODIFICADO (original: test_esqueleto_cripta). Antes solo revisaba claves.
    # Ahora revisa la página, la cantidad de salas y la puerta real 2->5
    # (cerrada, con llave de bronce y cierre automático de 500).
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

    # MODIFICADO (une los originales test_version_cripta y test_version_catalogo).
    # Antes cada uno revisaba que hubiera una versión no vacía. Ahora además
    # comprueba que la versión de la cripta coincida con la de general.json.
    def test_versiones(self):
        self.assertEqual(self.offline.version_cripta(CRIPTA)["version"],
                         self.offline.datos_cripta(CRIPTA)["version"])
        self.assertTrue(self.offline.version_catalogo()["version"])


class TestContenido(unittest.TestCase):
    """contenido_salas responde cualquier combinación de salas, no solo lotes guardados."""

    def setUp(self):
        self.offline = DatosOffline()

    # MODIFICADO (original: test_contenido_salas). Pide las mismas 6 salas, pero
    # ahora se leen de un archivo por sala; además comprueba que vuelvan en orden.
    def test_todas_las_salas(self):
        contenido = self.offline.contenido_salas(CRIPTA, [1, 2, 3, 4, 5, 6])["contenido"]
        self.assertEqual([s["sala"] for s in contenido], [1, 2, 3, 4, 5, 6])
        for sala in contenido:
            for clave in ("enemigos", "objetos", "trampas"):
                self.assertIn(clave, sala)

    # NUEVO: pedir una sola sala funciona (antes solo servía el lote exacto guardado).
    def test_una_sola_sala(self):
        contenido = self.offline.contenido_salas(CRIPTA, [4])["contenido"]
        self.assertEqual(len(contenido), 1)
        sala_4 = contenido[0]
        self.assertEqual(sala_4["enemigos"][0]["instancia"], "e-401")
        self.assertEqual(sala_4["enemigos"][0]["tipo"], "ent_guardian_oseo")
        self.assertIn("itm_llave_negra", sala_4["objetos"])

    # NUEVO: las salas vuelven en el orden en que se pidieron.
    def test_respeta_el_orden_pedido(self):
        contenido = self.offline.contenido_salas(CRIPTA, [3, 1])["contenido"]
        self.assertEqual([s["sala"] for s in contenido], [3, 1])

    # NUEVO: documenta que el API puede omitir 'vida' de un enemigo (e-401).
    def test_enemigo_puede_venir_sin_vida(self):
        # El juego toma vida_max del catálogo en este caso.
        guardian = self.offline.contenido_salas(CRIPTA, [4])["contenido"][0]["enemigos"][0]
        self.assertNotIn("vida", guardian)

    # NUEVO: pedir una sala que no existe da FileNotFoundError con su número.
    def test_sala_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            self.offline.contenido_salas(CRIPTA, [999])
        self.assertIn("sala_999", str(ctx.exception))


class TestCatalogo(unittest.TestCase):
    """catalogo responde cualquier combinación de fichas y conserva tildes."""

    def setUp(self):
        self.offline = DatosOffline()

    # NUEVO: reemplaza al original test_catalogo, que solo funcionaba con el lote
    # exacto de 6 fichas guardado. Pide 2 fichas sueltas y revisa el orden.
    def test_subconjunto_en_el_orden_pedido(self):
        entidades = self.offline.catalogo(["trp_dardos", "ent_rata_gigante"])["entidades"]
        self.assertEqual([f["id"] for f in entidades], ["trp_dardos", "ent_rata_gigante"])

     # NUEVO: 'guardián' y 'daño' se leen bien (encoding UTF-8).
    def test_tildes_y_enie(self):
        guardian = self.offline.catalogo(["ent_guardian_oseo"])["entidades"][0]
        self.assertEqual(guardian["comportamiento"], "guardián")
        dardos = self.offline.catalogo(["trp_dardos"])["entidades"][0]
        self.assertEqual(dardos["daño"], 4)

    # NUEVO: pedir una ficha que no existe da FileNotFoundError.
    def test_id_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError):
            self.offline.catalogo(["itm_que_no_existe"])

    # NUEVO: toda ficha usada en la cripta (incluido lo que sueltan los enemigos) existe.
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

    # MODIFICADO (original: test_maximo_10_salas_lanza_error). Solo se renombró; misma lógica.
    def test_maximo_10_salas(self):
        with self.assertRaises(ValueError) as ctx:
            self.offline.contenido_salas(CRIPTA, list(range(1, 12)))
        self.assertIn("10", str(ctx.exception))

    # MODIFICADO (original: test_sala_ids_vacio_lanza_error). Solo se renombró; misma lógica.
    def test_sala_ids_vacio(self):
        with self.assertRaises(ValueError):
            self.offline.contenido_salas(CRIPTA, [])

    # MODIFICADO (original: test_maximo_10_catalogo_lanza_error). Solo se renombró; misma lógica.
    def test_maximo_10_catalogo(self):
        with self.assertRaises(ValueError) as ctx:
            self.offline.catalogo([f"ent_{i}" for i in range(11)])
        self.assertIn("10", str(ctx.exception))

    # NUEVO: lista de fichas vacía da ValueError (equivalente a test_sala_ids_vacio).
    def test_tipo_ids_vacio(self):
        with self.assertRaises(ValueError):
            self.offline.catalogo([])

    # NUEVO: página 0 da ValueError (la validación existía pero no tenía test).
    def test_pagina_invalida(self):
        with self.assertRaises(ValueError):
            self.offline.esqueleto_cripta(CRIPTA, 0)

    # NUEVO: una página fuera de rango da FileNotFoundError.
    def test_pagina_que_no_existe(self):
        with self.assertRaises(FileNotFoundError):
            self.offline.esqueleto_cripta(CRIPTA, 2)


class TestCarpeta(unittest.TestCase):
    """la carpeta de datos se puede elegir y no depende de dónde se ejecute Python."""

    # MODIFICADO (mismo nombre). Antes cambiaba el atributo de clase CARPETA con
    # patch.object, que ya no existe. Ahora pasa la carpeta directo al constructor:
    # DatosOffline('carpeta_que_no_existe_xyz'). Revisa el mismo mensaje de error. 
    def test_carpeta_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            DatosOffline("carpeta_que_no_existe_xyz")
        mensaje = str(ctx.exception)
        self.assertIn("carpeta_que_no_existe_xyz", mensaje)
        self.assertIn("Verifica", mensaje)

    # MODIFICADO (mismo nombre). Antes buscaba el nombre viejo
    # 'cripta-inexistente_general.json' en el mensaje. Ahora la ruta es
    # cripta-inexistente/general.json, así que busca las dos partes por separado.
    def test_archivo_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            DatosOffline().datos_cripta("cripta-inexistente")
        mensaje = str(ctx.exception)
        self.assertIn("cripta-inexistente", mensaje)
        self.assertIn("general.json", mensaje)

    # NUEVO: el constructor lee de la carpeta que se le pase (usa una carpeta temporal).
    def test_carpeta_personalizada(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with open(os.path.join(carpeta, "criptas.json"), "w", encoding="utf-8") as f:
                json.dump({"criptas": [{"id": "cripta-prueba"}]}, f)
            offline = DatosOffline(carpeta)
            self.assertEqual(offline.listar_criptas()["criptas"][0]["id"], "cripta-prueba")

    # NUEVO: funciona aunque Python se ejecute desde otra carpeta (ruta desde __file__).
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
