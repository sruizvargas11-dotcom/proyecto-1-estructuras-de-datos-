"""ControladorPygame.tabla_puntajes(): filas planas de persistencia/puntajes.py.

El registro ocurre en el hilo de modelo (ControladorJuego._cerrar) y la
escena lee desde el hilo de pygame; aquí se comprueba que la copia publicada
ya está lista cuando aparece resumen_fin().
"""
import dataclasses
import json
import time

from adaptadores.datos_offline import DatosOffline
from herramientas.generar_cripta_prueba import generar
from persistencia.puntajes import RegistroPuntaje, TablaPuntajes
from vista_pygame.contratos import FilaPuntaje
from controlador.controlador_pygame import ControladorPygame

TIMEOUT = 15
COMANDOS_VICTORIA = ["N", "N", "N", "R", "AB E", "E"]


def _esperar(condicion, timeout=TIMEOUT):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.01)
    return False


def _controlador(tmp_path):
    carpeta = tmp_path / "datos"
    if not carpeta.exists():
        generar(carpeta)
    return ControladorPygame(DatosOffline(str(carpeta)), carpeta_cache=str(tmp_path / "cache"),
                             partidas_dir=str(tmp_path / "partidas"))


def _ganar(tmp_path, nombre):
    c = _controlador(tmp_path)
    c.iniciar_partida("cripta-prueba", nombre, semilla=999)
    assert _esperar(lambda: c.estado() is not None)
    for comando in COMANDOS_VICTORIA:
        c.enviar_comando(comando)
    assert _esperar(lambda: c.resumen_fin() is not None)
    filas = c.tabla_puntajes()   # leída apenas aparece el resumen, como haría la escena
    c.salir()
    return c, filas


def test_fila_puntaje_tiene_los_campos_documentados():
    assert {f.name for f in dataclasses.fields(FilaPuntaje)} == {
        "posicion", "nombre_jugador", "id_cripta", "version_cripta", "acciones_jugador",
        "enemigos_derrotados", "tiempo_final", "resultado", "es_actual"}


def test_sin_archivo_la_tabla_esta_vacia(tmp_path):
    assert _controlador(tmp_path).tabla_puntajes() == []


def test_antes_de_jugar_se_lee_el_archivo(tmp_path):
    ruta = tmp_path / "partidas" / "puntajes.json"
    tabla = TablaPuntajes(str(ruta))
    tabla.agregar(RegistroPuntaje("Ana", "cripta-prueba", "laboratorio-consola-v1", 5, 0, 300, "victoria"))
    tabla.guardar()
    filas = _controlador(tmp_path).tabla_puntajes()
    assert [(f.posicion, f.nombre_jugador, f.es_actual) for f in filas] == [(1, "Ana", False)]


def test_un_archivo_danado_da_una_tabla_vacia(tmp_path):
    ruta = tmp_path / "partidas" / "puntajes.json"
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{roto", encoding="utf-8")
    assert _controlador(tmp_path).tabla_puntajes() == []


def test_al_ganar_la_tabla_ya_esta_lista_con_el_resumen(tmp_path):
    c, filas = _ganar(tmp_path, "Ada")
    resumen = c.resumen_fin()
    assert len(filas) == 1
    fila = filas[0]
    assert (fila.posicion, fila.nombre_jugador, fila.resultado, fila.es_actual) == \
        (1, "Ada", "victoria", True)
    assert (fila.id_cripta, fila.version_cripta, fila.acciones_jugador,
            fila.enemigos_derrotados, fila.tiempo_final) == \
        (resumen.id_cripta, resumen.version_cripta, resumen.acciones_jugador,
         resumen.enemigos_derrotados, resumen.tiempo_final)
    datos = json.loads((tmp_path / "partidas" / "puntajes.json").read_text(encoding="utf-8"))
    assert [r["nombre"] for r in datos["puntajes"]] == ["Ada"]


def test_la_partida_actual_queda_marcada_entre_las_anteriores(tmp_path):
    ruta = tmp_path / "partidas" / "puntajes.json"
    tabla = TablaPuntajes(str(ruta))
    tabla.agregar(RegistroPuntaje("Rapida", "cripta-prueba", "laboratorio-consola-v1", 1, 9, 1, "victoria"))
    tabla.agregar(RegistroPuntaje("Muerta", "cripta-prueba", "laboratorio-consola-v1", 1, 0, 50, "derrota"))
    tabla.guardar()
    _, filas = _ganar(tmp_path, "Ada")
    assert [(f.posicion, f.nombre_jugador, f.es_actual) for f in filas] == [
        (1, "Rapida", False), (2, "Ada", True), (3, "Muerta", False)]


def test_salir_sin_terminar_registra_interrumpida(tmp_path):
    c = _controlador(tmp_path)
    c.iniciar_partida("cripta-prueba", "Ada", semilla=999)
    assert _esperar(lambda: c.estado() is not None)
    c.enviar_comando("N")
    c.salir()
    assert [(f.nombre_jugador, f.resultado) for f in c.tabla_puntajes()] == [("Ada", "en_curso")]
    assert (tmp_path / "partidas" / "puntajes.json").exists()


def test_tabla_puntajes_devuelve_una_copia(tmp_path):
    _, filas = _ganar(tmp_path, "Ada")
    c = _controlador(tmp_path)
    copia = c.tabla_puntajes()
    copia.clear()
    assert len(c.tabla_puntajes()) == 1
