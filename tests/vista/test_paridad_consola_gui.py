"""Misma cripta offline + semilla + acciones por consola y por GUI deben dar
el mismo estado final, y el .log que escribe la GUI debe reproducirse con
--replay exactamente igual que uno de consola (ambos usan el mismo
ControladorJuego/BitacoraPartida sin modificar, solo cambia la vista)."""
import time

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.controlador_replay import reproducir
from controlador.inicio_partida import nueva_partida
from herramientas.generar_cripta_prueba import generar
from controlador.controlador_pygame import ControladorPygame

TIMEOUT = 8.0
COMANDOS = ["N", "N", "R", "U", "N", "W", "EQ"]


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


def _firma(partida):
    j = partida.jugador
    return (partida.tiempo, j.vida, j.sala_actual.id, partida.acciones_jugador,
            partida.enemigos_derrotados, partida.estado,
            tuple((n.valor.instancia_id, n.valor.nombre)
                 for n in j.inventario.recorrer_desde_frente()))


def test_misma_semilla_y_acciones_mismo_estado_final(tmp_path):
    carpeta = generar(tmp_path / "datos")

    sesion = nueva_partida(DatosOffline(str(carpeta)), "cripta-prueba",
                           str(tmp_path / "cache-consola"), semilla=72,
                           nombre_jugador="Ada")
    ControladorJuego(sesion, VistaGuion(list(COMANDOS) + ["Q"])).jugar()
    firma_consola = _firma(sesion.partida)

    c = ControladorPygame(DatosOffline(str(carpeta)), carpeta_cache=str(tmp_path / "cache-gui"),
                          partidas_dir=str(tmp_path / "partidas-gui"))
    c.iniciar_partida("cripta-prueba", "Ada", semilla=72)
    assert _esperar(lambda: c.estado() is not None)
    for comando in COMANDOS:
        c.enviar_comando(comando)
    assert _esperar(lambda: c.estado().acciones_jugador == sesion.partida.acciones_jugador)
    ruta_log = c.sesion.bitacora.ruta
    c.salir()

    assert _firma(c.sesion.partida) == firma_consola


def test_log_de_la_gui_se_reproduce_con_replay(tmp_path):
    """El .log escrito al jugar desde la GUI se reproduce igual que uno de
    consola: mismo formato de bitácora, mismo ControladorJuego sin tocar."""
    carpeta = generar(tmp_path / "datos")
    c = ControladorPygame(DatosOffline(str(carpeta)), carpeta_cache=str(tmp_path / "cache-gui"),
                          partidas_dir=str(tmp_path / "partidas-gui"))
    c.iniciar_partida("cripta-prueba", "Ada", semilla=72)
    assert _esperar(lambda: c.estado() is not None)
    for comando in COMANDOS:
        c.enviar_comando(comando)
    assert _esperar(lambda: c.estado().acciones_jugador >= 5)
    ruta_log = c.sesion.bitacora.ruta
    firma_gui = None
    c.salir()
    firma_gui = _firma(c.sesion.partida)

    resultado = reproducir(ruta_log, DatosOffline(str(carpeta)), str(tmp_path / "cache-replay"))
    assert resultado.verificado
    assert _firma(resultado.partida) == firma_gui
