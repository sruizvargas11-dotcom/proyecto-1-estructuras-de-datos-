"""Pruebas funcionales del Bloque 3 — bitácora de partida y persistencia binaria.

Corre con pytest sobre carpetas temporales; no toca archivos del repositorio.
"""

import ast
import os
import random

import pytest

from bitacora_partida import BitacoraPartida, ErrorVersionIncompatible, MARCA
from persistencia.PartidaBinaria import PartidaBinaria, ErrorFormatoBinario, MAGIC, VERSION_FORMATO


CRIPTA_ID = "cripta-01"
VERSION_CRIPTA = "v1.0.0"
VERSION_CATALOGO = "cat-v1.0.0"
SEMILLA = 12345


# ─────────────────────────── BitacoraPartida ────────────────────────────


@pytest.fixture
def ruta_bitacora(tmp_path):
    return str(tmp_path / "partida.log")


class TestBitacoraPartidaNueva:

    def test_partida_nueva_crea_archivo_con_encabezado_correcto(self, ruta_bitacora):
        BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )

        assert os.path.exists(ruta_bitacora)

        with open(ruta_bitacora, "r", encoding="utf-8") as f:
            lineas = [linea.rstrip("\n") for linea in f]

        assert lineas[0] == MARCA
        assert lineas[1] == f"cripta_id: {CRIPTA_ID}"
        assert lineas[2] == f"version_cripta: {VERSION_CRIPTA}"
        assert lineas[3] == f"version_catalogo: {VERSION_CATALOGO}"
        assert lineas[4] == f"semilla: {SEMILLA}"
        assert lineas[5] == "----------"


class TestAbrir:

    def test_abrir_recupera_todos_los_campos(self, ruta_bitacora):
        BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )

        bitacora = BitacoraPartida.abrir(ruta_bitacora)

        assert bitacora.cripta_id == CRIPTA_ID
        assert bitacora.version_cripta == VERSION_CRIPTA
        assert bitacora.version_catalogo == VERSION_CATALOGO
        assert bitacora.semilla == SEMILLA

    def test_abrir_lanza_valueerror_si_marca_incorrecta(self, tmp_path):
        ruta = tmp_path / "no_es_bitacora.log"
        ruta.write_text("ESTO NO ES UNA BITACORA\notros datos\n", encoding="utf-8")

        with pytest.raises(ValueError):
            BitacoraPartida.abrir(str(ruta))


class TestRegistrarYLeer:

    def test_registrar_escribe_lineas_con_formato_correcto(self, ruta_bitacora):
        bitacora = BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )
        bitacora.registrar(0, "inicio_partida")
        bitacora.registrar(5, "mover_norte")
        bitacora.cerrar()

        with open(ruta_bitacora, "r", encoding="utf-8") as f:
            lineas = [linea.rstrip("\n") for linea in f]

        assert lineas[-2] == "t=0 inicio_partida"
        assert lineas[-1] == "t=5 mover_norte"

    def test_leer_acciones_produce_exactamente_lo_registrado(self, ruta_bitacora):
        bitacora = BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )
        esperado = [
            (0, "inicio_partida"),
            (3, "mover_norte"),
            (7, "atacar_rata_gigante"),
            (10, "recoger_daga_oxidada"),
        ]
        for tiempo, accion in esperado:
            bitacora.registrar(tiempo, accion)
        bitacora.cerrar()

        leida = BitacoraPartida.abrir(ruta_bitacora)
        assert leida.leer_acciones() == esperado


class TestVerificarCompatibilidad:

    def test_lanza_si_version_cripta_difiere(self, ruta_bitacora):
        bitacora = BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )
        with pytest.raises(ErrorVersionIncompatible):
            bitacora.verificar_compatibilidad("version_distinta", VERSION_CATALOGO)

    def test_lanza_si_version_catalogo_difiere(self, ruta_bitacora):
        bitacora = BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )
        with pytest.raises(ErrorVersionIncompatible):
            bitacora.verificar_compatibilidad(VERSION_CRIPTA, "catalogo_distinto")

    def test_no_lanza_si_ambas_versiones_coinciden(self, ruta_bitacora):
        bitacora = BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )
        bitacora.verificar_compatibilidad(VERSION_CRIPTA, VERSION_CATALOGO)


class TestContextManager:

    def test_uso_como_context_manager_cierra_sin_error(self, ruta_bitacora):
        BitacoraPartida.partida_nueva(
            ruta_bitacora, CRIPTA_ID, VERSION_CRIPTA, VERSION_CATALOGO, SEMILLA
        )

        with BitacoraPartida.abrir(ruta_bitacora) as bitacora:
            bitacora.registrar(0, "inicio_partida")

        assert bitacora._archivo is None


# ─────────────────────────── PartidaBinaria ────────────────────────────


@pytest.fixture
def ruta_binaria(tmp_path):
    return str(tmp_path / "partida.bin")


def _estado_global_ejemplo():
    return {"reloj": 42, "jugador": {"vida": 80, "inventario": ["daga_oxidada"]}, "semilla": SEMILLA}


def _estado_salas_ejemplo():
    """Pares (sala_id, datos) ya en orden, para las pruebas que no
    necesitan ejercitar el ordenamiento."""
    return [
        (1, {"sala": 1, "enemigos": [], "objetos": ["daga_oxidada"], "trampas": []}),
        (2, {"sala": 2, "enemigos": ["rata_gigante"], "objetos": [], "trampas": ["pozo"]}),
        (5, {"sala": 5, "enemigos": [], "objetos": [], "trampas": []}),
    ]


def _datos_por_id(salas, sala_id):
    for sid, datos in salas:
        if sid == sala_id:
            return datos
    raise KeyError(sala_id)


class TestGuardarYCargarTodo:

    def test_guardar_y_cargar_todo_recupera_estado_identico(self, ruta_binaria):
        global_esperado = _estado_global_ejemplo()
        salas_esperado = _estado_salas_ejemplo()

        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(global_esperado, salas_esperado)

        global_cargado, salas_cargado = partida.cargar_todo()

        assert global_cargado == global_esperado
        assert salas_cargado == salas_esperado

    def test_guardar_con_cero_salas_no_lanza_excepcion(self, ruta_binaria):
        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(_estado_global_ejemplo(), [])

        global_cargado, salas_cargado = partida.cargar_todo()
        assert global_cargado == _estado_global_ejemplo()
        assert salas_cargado == []

    def test_guardar_con_pares_desordenados_cargar_todo_los_devuelve_ordenados(self, ruta_binaria):
        salas_desordenadas = [
            (5, {"sala": 5}),
            (1, {"sala": 1}),
            (2, {"sala": 2}),
        ]

        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(_estado_global_ejemplo(), salas_desordenadas)

        _, salas_cargado = partida.cargar_todo()

        assert salas_cargado == [(1, {"sala": 1}), (2, {"sala": 2}), (5, {"sala": 5})]

    def test_guardar_con_sala_id_repetido_lanza_valueerror(self, ruta_binaria):
        salas_repetidas = [
            (1, {"sala": 1}),
            (2, {"sala": 2}),
            (1, {"sala": 1, "otra_version": True}),
        ]

        partida = PartidaBinaria(ruta_binaria)
        with pytest.raises(ValueError):
            partida.guardar(_estado_global_ejemplo(), salas_repetidas)


class TestCargarGlobal:

    def test_cargar_global_devuelve_solo_estado_global(self, ruta_binaria):
        global_esperado = _estado_global_ejemplo()
        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(global_esperado, _estado_salas_ejemplo())

        assert partida.cargar_global() == global_esperado


class TestCargarSalaBinaria:

    def test_sala_existente_devuelve_dict_correcto(self, ruta_binaria):
        salas = _estado_salas_ejemplo()
        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(_estado_global_ejemplo(), salas)

        assert partida.cargar_sala_binaria(2) == _datos_por_id(salas, 2)

    def test_sala_intermedia_desordenada_al_guardar_devuelve_la_correcta(self, ruta_binaria):
        salas_desordenadas = [
            (40, {"sala": 40}),
            (10, {"sala": 10}),
            (30, {"sala": 30}),
            (20, {"sala": 20}),
        ]

        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(_estado_global_ejemplo(), salas_desordenadas)

        assert partida.cargar_sala_binaria(30) == {"sala": 30}
        assert partida.cargar_sala_binaria(10) == {"sala": 10}

    def test_sala_inexistente_devuelve_none(self, ruta_binaria):
        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(_estado_global_ejemplo(), _estado_salas_ejemplo())

        assert partida.cargar_sala_binaria(999) is None

    def test_busqueda_binaria_en_disco_con_200_salas_desordenadas(self, ruta_binaria):
        """La búsqueda binaria ahora se hace directamente sobre el índice en
        disco (sin cargarlo completo): se verifica que sigue encontrando la
        sala correcta en los extremos y en el medio, con un índice grande y
        guardado fuera de orden."""
        rnd = random.Random(7)
        ids = list(range(200))
        rnd.shuffle(ids)
        salas_desordenadas = [(sid, {"sala": sid}) for sid in ids]

        partida = PartidaBinaria(ruta_binaria)
        partida.guardar(_estado_global_ejemplo(), salas_desordenadas)

        assert partida.cargar_sala_binaria(0) == {"sala": 0}
        assert partida.cargar_sala_binaria(100) == {"sala": 100}
        assert partida.cargar_sala_binaria(199) == {"sala": 199}
        assert partida.cargar_sala_binaria(999) is None


class TestSinOrdenamientosProhibidos:

    def test_persistencia_partida_binaria_no_usa_sorted_ni_sort(self):
        """§4.9: sorted()/list.sort() no se permiten en los ordenamientos
        evaluados; el índice del archivo de guardado es uno de esos
        contextos. Se verifica estáticamente con ast, no por inspección
        manual, para que no se reintroduzca por accidente."""
        ruta_modulo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "persistencia", "PartidaBinaria.py",
        )
        with open(ruta_modulo, "r", encoding="utf-8") as f:
            arbol = ast.parse(f.read(), filename=ruta_modulo)

        llamadas_prohibidas = []
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call):
                funcion = nodo.func
                if isinstance(funcion, ast.Name) and funcion.id == "sorted":
                    llamadas_prohibidas.append("sorted()")
                elif isinstance(funcion, ast.Attribute) and funcion.attr == "sort":
                    llamadas_prohibidas.append(".sort()")

        assert llamadas_prohibidas == []


class TestEncabezadoInvalido:

    def test_magic_incorrecto_lanza_errorformatobinario(self, ruta_binaria):
        with open(ruta_binaria, "wb") as f:
            f.write((0xDEADBEEF).to_bytes(4, byteorder="big"))
            f.write(VERSION_FORMATO.to_bytes(2, byteorder="big"))
            f.write((0).to_bytes(2, byteorder="big"))
            f.write((12).to_bytes(4, byteorder="big"))

        partida = PartidaBinaria(ruta_binaria)
        with pytest.raises(ErrorFormatoBinario):
            partida.cargar_global()

    def test_version_incorrecta_lanza_errorformatobinario(self, ruta_binaria):
        with open(ruta_binaria, "wb") as f:
            f.write(MAGIC.to_bytes(4, byteorder="big"))
            f.write((VERSION_FORMATO + 1).to_bytes(2, byteorder="big"))
            f.write((0).to_bytes(2, byteorder="big"))
            f.write((12).to_bytes(4, byteorder="big"))

        partida = PartidaBinaria(ruta_binaria)
        with pytest.raises(ErrorFormatoBinario):
            partida.cargar_global()
