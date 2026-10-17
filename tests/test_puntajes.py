"""Tabla de puntajes: registro al cerrar la partida, orden con InsertionSort y JSON."""
import json

import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import nueva_partida
from estructuras.vector_dinamico import Vector
from herramientas.generar_cripta_prueba import generar
from persistencia import puntajes
from persistencia.puntajes import (ErrorTablaPuntajes, RegistroPuntaje, TablaPuntajes,
                                   comparar_puntajes)
from tests.test_controlador_juego import RUTA_VICTORIA, VistaGuion

# Camino corto a la salida de cripta-prueba (igual que tests/vista/test_fin_partida.py).
VICTORIA_PRUEBA = ["N", "N", "N", "R", "AB E", "E"]


def registro(nombre="Ana", resultado="victoria", derrotados=3, tiempo=1000, acciones=20,
             cripta="cripta-01", version="v1"):
    return RegistroPuntaje(nombre, cripta, version, acciones, derrotados, tiempo, resultado)


def nombres(tabla):
    return [r.nombre_jugador for r in tabla]


# --- Registro ----------------------------------------------------------------

@pytest.mark.parametrize("campo, valor", [
    ("acciones", -1), ("acciones", True), ("tiempo", 1.5), ("derrotados", "3"),
    ("resultado", "en_curso"), ("cripta", ""), ("version", None), ("nombre", "  "),
])
def test_registro_valida_sus_campos(campo, valor):
    with pytest.raises(ValueError):
        registro(**{campo: valor})


def test_registro_ida_y_vuelta_json():
    original = registro(nombre="Sebastián", version="fd58f7743b9e")
    copia = RegistroPuntaje.desde_json(json.loads(json.dumps(original.a_json())))
    assert copia.a_json() == original.a_json()
    assert set(original.a_json()) == {"nombre_jugador", "cripta_id", "version_cripta",
                                      "acciones_jugador", "enemigos_derrotados",
                                      "tiempo_final", "resultado"}


# --- Criterio de orden -------------------------------------------------------

def test_victoria_antes_que_derrota():
    assert comparar_puntajes(registro(resultado="victoria", derrotados=0),
                             registro(resultado="derrota", derrotados=9)) < 0


def test_mas_enemigos_derrotados_va_antes():
    assert comparar_puntajes(registro(derrotados=3), registro(derrotados=2)) < 0


def test_entre_victorias_gana_el_menor_tiempo():
    assert comparar_puntajes(registro(tiempo=900), registro(tiempo=1000)) < 0


def test_entre_derrotas_gana_el_que_sobrevivio_mas():
    assert comparar_puntajes(registro(resultado="derrota", tiempo=1000),
                             registro(resultado="derrota", tiempo=900)) < 0


def test_con_el_mismo_tiempo_gana_el_de_menos_acciones():
    assert comparar_puntajes(registro(acciones=10), registro(acciones=11)) < 0
    assert comparar_puntajes(registro(), registro(nombre="Otro")) == 0


# --- Tabla -------------------------------------------------------------------

def test_sin_archivo_la_tabla_empieza_vacia(tmp_path):
    tabla = TablaPuntajes(str(tmp_path / "puntajes.json")).cargar()
    assert len(tabla) == 0 and isinstance(tabla.registros, Vector)


def test_agregar_ordena_y_devuelve_la_posicion(tmp_path):
    tabla = TablaPuntajes(str(tmp_path / "puntajes.json"))
    assert tabla.agregar(registro("Lenta", tiempo=2000)) == 1
    assert tabla.agregar(registro("Muerta", resultado="derrota")) == 2
    assert tabla.agregar(registro("Rapida", tiempo=500)) == 1
    assert tabla.agregar(registro("Media", tiempo=1000)) == 2
    assert nombres(tabla) == ["Rapida", "Media", "Lenta", "Muerta"]


def test_los_empates_conservan_el_orden_de_llegada(tmp_path):
    tabla = TablaPuntajes(str(tmp_path / "puntajes.json"))
    for nombre in ("Primero", "Segundo", "Tercero"):
        tabla.agregar(registro(nombre))
    assert nombres(tabla) == ["Primero", "Segundo", "Tercero"]


def test_agregar_a_una_tabla_ordenada_es_lineal(tmp_path, monkeypatch):
    """Con la tabla ya ordenada solo el registro nuevo está fuera de lugar:
    InsertionSort hace como máximo 2(n - 1) comparaciones, no O(n log n) ni O(n²)."""
    tabla = TablaPuntajes(str(tmp_path / "puntajes.json"))
    for i in range(200):
        tabla.agregar(registro(f"J{i}", tiempo=1000 + i))
    llamadas = []
    original = puntajes.comparar_puntajes

    def contar(a, b):
        llamadas.append(1)
        return original(a, b)

    monkeypatch.setattr(puntajes, "comparar_puntajes", contar)
    assert tabla.agregar(registro("Mejor", tiempo=1)) == 1
    assert len(llamadas) <= 2 * (len(tabla) - 1)


def test_el_archivo_queda_ordenado_y_se_puede_releer(tmp_path):
    ruta = tmp_path / "partidas" / "puntajes.json"   # la carpeta se crea sola
    tabla = TablaPuntajes(str(ruta))
    tabla.agregar(registro("B", tiempo=2000))
    tabla.agregar(registro("A", tiempo=1000))
    tabla.guardar()
    documento = json.loads(ruta.read_text(encoding="utf-8"))
    assert documento["formato_puntajes"] == 1
    assert [r["nombre_jugador"] for r in documento["registros"]] == ["A", "B"]
    assert nombres(TablaPuntajes(str(ruta)).cargar()) == ["A", "B"]
    assert not list(ruta.parent.glob(".puntajes-*.tmp"))


def test_cargar_reordena_un_archivo_editado_a_mano(tmp_path):
    ruta = tmp_path / "puntajes.json"
    ruta.write_text(json.dumps({"formato_puntajes": 1, "registros": [
        registro("Derrota", resultado="derrota").a_json(),
        registro("Lenta", tiempo=3000).a_json(),
        registro("Rapida", tiempo=100).a_json(),
    ]}), encoding="utf-8")
    assert nombres(TablaPuntajes(str(ruta)).cargar()) == ["Rapida", "Lenta", "Derrota"]


@pytest.mark.parametrize("contenido", [
    "{no es json", "[]", '{"formato_puntajes": 2, "registros": []}',
    '{"formato_puntajes": 1, "registros": [{"nombre_jugador": "Ana"}]}',
])
def test_un_archivo_danado_se_rechaza_sin_sobrescribirlo(tmp_path, contenido):
    ruta = tmp_path / "puntajes.json"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(ErrorTablaPuntajes):
        TablaPuntajes(str(ruta)).cargar()
    assert ruta.read_text(encoding="utf-8") == contenido


# --- Integración con ControladorJuego._cerrar --------------------------------

def _juego(tmp_path, comandos, nombre="Daniel", tabla=True, vida=300):
    sesion = nueva_partida(DatosOffline(), "cripta-01", str(tmp_path / "cache"),
                           semilla=3, nombre_jugador=nombre)
    sesion.partida.jugador.vida_max = sesion.partida.jugador.vida = vida
    vista = VistaGuion(comandos)
    tabla_puntajes = TablaPuntajes(str(tmp_path / "puntajes.json")) if tabla else None
    return ControladorJuego(sesion, vista, tabla_puntajes=tabla_puntajes), vista, sesion


def test_una_victoria_queda_registrada_con_todos_los_campos(tmp_path):
    controlador, vista, sesion = _juego(tmp_path, RUTA_VICTORIA)
    assert controlador.jugar() == "victoria"
    partida = sesion.partida
    datos = json.loads((tmp_path / "puntajes.json").read_text(encoding="utf-8"))
    assert datos["registros"] == [{
        "nombre_jugador": "Daniel", "cripta_id": "cripta-01",
        "version_cripta": partida.version_cripta,
        "acciones_jugador": partida.acciones_jugador,
        "enemigos_derrotados": 3, "tiempo_final": partida.tiempo,
        "resultado": "victoria"}]
    assert controlador.registro_puntaje is not None
    assert vista.textos("Puntaje registrado: posición 1 de 1")


def test_se_registra_antes_de_mostrar_fin(tmp_path):
    """La vista encuentra la tabla ya actualizada cuando se le avisa del fin."""
    controlador, vista, _ = _juego(tmp_path, RUTA_VICTORIA)
    vistos = []
    vista.mostrar_fin = lambda partida: vistos.append(len(controlador.tabla_puntajes))
    controlador.jugar()
    assert vistos == [1]


def test_una_derrota_tambien_se_registra(tmp_path):
    controlador, _, _ = _juego(tmp_path, ["N", "W", "W"], vida=5)
    assert controlador.jugar() == "derrota"
    tabla = TablaPuntajes(str(tmp_path / "puntajes.json")).cargar()
    assert [(r.nombre_jugador, r.resultado) for r in tabla] == [("Daniel", "derrota")]


def test_sin_nombre_se_registra_el_nombre_por_defecto(tmp_path):
    controlador, _, _ = _juego(tmp_path, RUTA_VICTORIA, nombre=None)
    controlador.jugar()
    assert nombres(TablaPuntajes(str(tmp_path / "puntajes.json")).cargar()) == ["Jugador"]


def test_varias_partidas_se_acumulan_en_orden(tmp_path):
    for nombre, comandos, vida in (("Pierde", ["N", "W", "W"], 5),
                                   ("Gana", RUTA_VICTORIA, 300)):
        controlador, _, _ = _juego(tmp_path, comandos, nombre=nombre, vida=vida)
        controlador.jugar()
    assert nombres(TablaPuntajes(str(tmp_path / "puntajes.json")).cargar()) == ["Gana", "Pierde"]


def test_salir_con_q_no_registra_puntaje(tmp_path):
    controlador, _, _ = _juego(tmp_path, ["W", "Q"])
    assert controlador.jugar() == "en_curso"
    assert not (tmp_path / "puntajes.json").exists()
    assert controlador.registro_puntaje is None


def test_sin_tabla_no_se_escribe_nada(tmp_path):
    controlador, _, _ = _juego(tmp_path, RUTA_VICTORIA, tabla=False)
    assert controlador.jugar() == "victoria"
    assert not (tmp_path / "puntajes.json").exists()


def test_un_archivo_danado_no_interrumpe_el_cierre(tmp_path):
    ruta = tmp_path / "puntajes.json"
    ruta.write_text("{roto", encoding="utf-8")
    controlador, vista, _ = _juego(tmp_path, RUTA_VICTORIA)
    assert controlador.jugar() == "victoria" and vista.fin == "victoria"
    assert vista.textos("No se pudo registrar el puntaje")
    assert ruta.read_text(encoding="utf-8") == "{roto"


def test_despues_de_cargar_se_registra_el_nombre_del_guardado(tmp_path):
    """Con L la sesión pasa a ser la del archivo, que trae su propio nombre."""
    carpeta = generar(tmp_path / "datos")
    guardado = str(tmp_path / "partida.sav")
    tabla = str(tmp_path / "puntajes.json")

    def jugar(nombre, comandos):
        sesion = nueva_partida(DatosOffline(str(carpeta)), "cripta-prueba",
                               str(tmp_path / "cache"), semilla=999, nombre_jugador=nombre)
        controlador = ControladorJuego(sesion, VistaGuion(comandos),
                                       tabla_puntajes=TablaPuntajes(tabla))
        return controlador.jugar()

    assert jugar("Ada", ["N", f"G {guardado}", "Q"]) == "en_curso"
    assert jugar("Otro", [f"L {guardado}"] + VICTORIA_PRUEBA[1:]) == "victoria"
    assert nombres(TablaPuntajes(tabla).cargar()) == ["Ada"]


def test_main_usa_la_tabla_de_partidas_dir(tmp_path, monkeypatch):
    """La consola registra en <--partidas-dir>/puntajes.json."""
    import io
    import main
    generar(tmp_path / "datos")
    guion = "Daniel\n" + "\n".join(VICTORIA_PRUEBA) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(guion))
    assert main.main(["--offline", "--offline-dir", str(tmp_path / "datos"),
                      "--cripta", "cripta-prueba", "--partidas-dir", str(tmp_path / "p"),
                      "--cache-dir", str(tmp_path / "cache"),
                      "--reportes", str(tmp_path / "r.txt")]) == 0
    tabla = TablaPuntajes(str(tmp_path / "p" / "puntajes.json")).cargar()
    assert [(r.nombre_jugador, r.resultado) for r in tabla] == [("Daniel", "victoria")]
