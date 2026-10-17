"""Partida offline con semilla y acciones fijas: una termina en derrota y
otra en victoria. El ResumenPartida de la GUI debe coincidir exactamente con
lo que calcula/reporta la consola (resumen_puntaje + estadísticas de red),
sin que la vista recalcule nada.
"""
import time

import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import nueva_partida
from herramientas.generar_cripta_prueba import generar
from vista_pygame.controlador_pygame import ControladorPygame

TIMEOUT = 8.0


class VistaGuion:
    def __init__(self, comandos):
        self._comandos = iter(comandos)
    def mostrar_estado(self, partida): pass
    def mostrar_inventario(self, partida, objetos, criterio): pass
    def mostrar_ayuda(self): pass
    def mostrar_objeto(self, nodo): pass
    def mostrar_fin(self, partida): pass
    def agregar_mensaje(self, tiempo, texto): pass
    def leer_comando(self): return next(self._comandos, "Q")


def _esperar(condicion, timeout=TIMEOUT):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.01)
    return False


def _jugar_consola(fuente, cripta_id, carpeta_cache, semilla, comandos):
    sesion = nueva_partida(fuente, cripta_id, str(carpeta_cache), semilla=semilla,
                           nombre_jugador="Ada")
    ControladorJuego(sesion, VistaGuion(list(comandos) + ["Q"])).jugar()
    return sesion


def _jugar_gui(fuente, cripta_id, carpeta_cache, partidas_dir, semilla, nombre, comandos):
    c = ControladorPygame(fuente, carpeta_cache=str(carpeta_cache),
                          partidas_dir=str(partidas_dir))
    c.iniciar_partida(cripta_id, nombre, semilla=semilla)
    assert _esperar(lambda: c.estado() is not None)
    # Se encolan todas seguidas: la cola conserva el orden, así que no hace
    # falta esperar entre una y otra (la última termina la partida y
    # mostrar_estado ya no se vuelve a llamar para confirmarlo).
    for comando in comandos:
        c.enviar_comando(comando)
    assert _esperar(lambda: c.resumen_fin() is not None)
    c.salir()
    return c


# Camino real hasta la salida (ver datos_offline/cripta-01/salas_p1.json):
# 1 -N-> 2 -N-> 3 -N-> 4 (recoge itm_llave_negra, objeto 1) -AB E-> abre -E-> 6 = salida.
COMANDOS_VICTORIA = ["N", "N", "N", "R", "AB E", "E"]


def test_victoria_resumen_coincide_con_consola(tmp_path):
    carpeta = generar(tmp_path / "datos")

    sesion_consola = _jugar_consola(DatosOffline(str(carpeta)), "cripta-prueba",
                                    tmp_path / "cache-consola", 999, COMANDOS_VICTORIA)
    assert sesion_consola.partida.estado == "victoria"

    c = _jugar_gui(DatosOffline(str(carpeta)), "cripta-prueba", tmp_path / "cache-gui",
                   tmp_path / "partidas-gui", 999, "Ada", COMANDOS_VICTORIA)
    resumen = c.resumen_fin()

    assert resumen.resultado == "victoria"
    assert resumen.nombre_jugador == "Ada"
    puntaje_consola = dict(sesion_consola.partida.resumen_puntaje())
    assert resumen.id_cripta == puntaje_consola["cripta_id"]
    assert resumen.version_cripta == puntaje_consola["version_cripta"]
    assert resumen.acciones_jugador == puntaje_consola["acciones_jugador"]
    assert resumen.enemigos_derrotados == puntaje_consola["enemigos_derrotados"]
    assert resumen.tiempo_final == puntaje_consola["tiempo_final"]
    assert resumen.presupuesto_solicitudes == sesion_consola.partida.cripta.presupuesto_solicitudes
    cache_consola = dict(sesion_consola.red.estadisticas_cache())
    assert resumen.aciertos_cache == cache_consola["aciertos"]
    assert resumen.fallos_cache == cache_consola["fallos"]


def test_derrota_resumen_coincide_con_consola(tmp_path):
    # Dos ratas atacan sin tregua en la sala 2 (semilla 2026, ver
    # tests/test_partida.py::test_secuencia_213_y_determinismo_por_semilla);
    # el jugador de cripta-01 solo tiene 30 de vida: esperar alcanza para morir.
    comandos = ["N"] + ["W"] * 15

    sesion_consola = _jugar_consola(DatosOffline(), "cripta-01",
                                    tmp_path / "cache-consola", 2026, comandos)
    assert sesion_consola.partida.estado == "derrota"

    c = _jugar_gui(DatosOffline(), "cripta-01", tmp_path / "cache-gui",
                   tmp_path / "partidas-gui", 2026, "Ada", comandos)
    resumen = c.resumen_fin()

    assert resumen.resultado == "derrota"
    puntaje_consola = dict(sesion_consola.partida.resumen_puntaje())
    assert resumen.acciones_jugador == puntaje_consola["acciones_jugador"]
    assert resumen.tiempo_final == puntaje_consola["tiempo_final"]
