import pytest

from adaptadores.datos_offline import DatosOffline
from bitacora_partida import BitacoraPartida
from controlador.controlador_juego import (COSTO_ABRIR, COSTO_ATACAR, COSTO_EQUIPAR,
                                           COSTO_ESPERAR, COSTO_MOVER, COSTO_RECOGER,
                                           COSTO_SOLTAR, COSTO_USAR, ControladorJuego,
                                           interpretar)
from controlador.inicio_partida import nueva_partida
from modelo.entidades.objetos.fabrica_objetos import FabricaObjetos
from tests.test_controlador_red import FuenteContada

# Recorrido completo de cripta-01 hasta la victoria (ver datos_offline).
RUTA_VICTORIA = ("N,A,A,A,A,A,A,R,EQ,N,R 1,R,S,AB E,E,R 1,W,P,O,N,N,"
                 "A,A,A,A,A,A,A,A,R,AB E,E").split(",")
COSTOS = {"mover": COSTO_MOVER, "atacar": COSTO_ATACAR, "esperar": COSTO_ESPERAR,
          "usar": COSTO_USAR, "equipar": COSTO_EQUIPAR, "abrir": COSTO_ABRIR,
          "recoger": COSTO_RECOGER, "soltar": COSTO_SOLTAR}


class VistaGuion:
    """Vista de prueba: entrega comandos de una lista y registra lo mostrado."""

    def __init__(self, comandos):
        self._comandos = list(comandos)
        self.tiempos_decision = []   # t en cada mostrar_estado
        self.mensajes = []           # (t, texto)
        self.inventarios = []
        self.fin = None

    def agregar_mensaje(self, tiempo, texto):
        self.mensajes.append((tiempo, texto))

    def mostrar_estado(self, partida):
        self.tiempos_decision.append(partida.tiempo)

    def mostrar_inventario(self, partida, objetos, criterio):
        self.inventarios.append((criterio, [o.nombre for o in objetos]))

    def mostrar_ayuda(self):
        pass

    def leer_comando(self):
        return self._comandos.pop(0) if self._comandos else "Q"

    def mostrar_fin(self, partida):
        self.fin = partida.estado

    def textos(self, fragmento):
        return [(t, m) for t, m in self.mensajes if fragmento in m]


def _juego(tmp_path, comandos, semilla=3, vida=300, fuente=None, bitacora=True):
    fuente = fuente or DatosOffline()
    ruta = str(tmp_path / "partida.log") if bitacora else None
    sesion = nueva_partida(fuente, "cripta-01", str(tmp_path / "cache"),
                           semilla=semilla, ruta_bitacora=ruta)
    if vida is not None:
        sesion.partida.jugador.vida_max = sesion.partida.jugador.vida = vida
    vista = VistaGuion(comandos)
    return ControladorJuego(sesion, vista), vista, sesion, ruta


def _acciones(ruta):
    return BitacoraPartida.abrir(ruta).leer_acciones()


def _dar_objeto(sesion, tipo_id):
    """Pone en el inventario una instancia nueva del tipo (solo para pruebas)."""
    sesion.red.resolver_catalogo([tipo_id])
    objeto = FabricaObjetos(prefijo="prueba").crear(sesion.red.ficha(tipo_id))
    sesion.partida.jugador.inventario.insertar_al_final(objeto)
    return objeto


def _dar_pergamino(sesion):
    return _dar_objeto(sesion, "itm_pergamino_retroceso")



@pytest.mark.parametrize("texto, nombre, argumento", [
    ("n", "mover", "N"), ("O", "mover", "O"), ("mover e", "mover", "E"),
    ("A", "atacar", 1), ("a 2", "atacar", 2), ("R 3", "recoger", 3),
    ("eq", "equipar", 1), ("T 2", "soltar", 2), ("u", "usar", 1),
    ("AB s", "abrir", "S"), ("W", "esperar", None), ("P", "pergamino", None),
    ("I valor", "inventario", "valor"), ("q", "salir", None),
])
def test_interpretar_comandos_validos(texto, nombre, argumento):
    comando, error = interpretar(texto)
    assert error is None and comando.nombre == nombre and comando.argumento == argumento


@pytest.mark.parametrize("texto", ["", "xyz", "AB", "AB X", "A 0", "R dos", "I color",
                                   "mover"])
def test_interpretar_rechaza_entradas_invalidas(texto):
    comando, error = interpretar(texto)
    assert comando is None and error


def test_la_bitacora_usa_formas_que_el_interprete_acepta():
    for texto in ("mover N", "atacar 2", "abrir E", "esperar", "pergamino"):
        comando, error = interpretar(texto)
        assert error is None and comando.texto() == texto



def test_un_ciclo_extrae_ejecuta_y_programa(tmp_path):
    controlador, vista, sesion, _ = _juego(tmp_path, ["W"])
    jugador = sesion.partida.jugador
    entrada = controlador.ciclo()
    # 1. se extrajo el turno del jugador en t=0
    assert entrada.dato.dueno is jugador and entrada.tiempo == 0
    # 2. se pidió el comando con el reloj en 0
    assert vista.tiempos_decision == [0]
    # 4. su siguiente acción quedó programada con el costo de esperar
    assert jugador.evento_actual.tiempo == COSTO_ESPERAR
    assert dict(controlador.contadores())["turnos_jugador"] == 1


def test_ejemplo_213_tiempos_exactos(tmp_path):
    """0 mover; 66 rata; 100 recoger (25); 125 equipar (50); 132 rata; 175."""
    controlador, vista, sesion, ruta = _juego(tmp_path, ["N", "R", "EQ"])
    assert controlador.jugar() == "en_curso"
    assert vista.tiempos_decision == [0, 100, 125, 175]
    ataques = sorted({t for t, _ in vista.textos("te ataca")})
    assert ataques == [66, 132]
    assert [(t, a) for t, a in _acciones(ruta)] == [
        (0, "mover N"), (100, "recoger 1"), (125, "equipar 1")]
    contadores = dict(controlador.contadores())
    assert contadores["turnos_enemigo"] == 4      # 2 ratas x (66 y 132)


def test_efectos_del_entorno_pasan_por_el_bucle(tmp_path):
    """La trampa de la sala 2 se rearma en t=300 dentro del ciclo (paso 3b)."""
    controlador, vista, sesion, _ = _juego(tmp_path, ["N", "S", "W", "W", "W"])
    controlador.jugar()
    trampa = next(iter(sesion.partida.cripta.sala_por_id(2).trampas))
    assert trampa.armada
    assert dict(controlador.contadores())["efectos"] >= 1



def test_costos_de_cada_accion(tmp_path):
    controlador, vista, sesion, ruta = _juego(tmp_path, RUTA_VICTORIA)
    assert controlador.jugar() == "victoria"
    acciones = _acciones(ruta)
    usados = set()
    for (t, accion), (t_sig, siguiente) in zip(acciones, acciones[1:]):
        nombre = accion.split()[0]
        if nombre == "pergamino" or siguiente == "pergamino":
            continue   # el pergamino no tiene costo y mueve el reloj hacia atrás
        assert t_sig - t == COSTOS[nombre], (t, accion)
        usados.add(nombre)
    # 'esperar' se verifica en test_rechazos (su único uso aquí va antes del pergamino).
    assert {"mover", "atacar", "recoger", "equipar", "abrir"} <= usados


def test_soltar_y_usar_cuestan_25_y_50(tmp_path):
    controlador, vista, sesion, _ = _juego(tmp_path, ["N", "N", "R", "T", "R", "Q"])
    # sala 3: llave de bronce y coraza; recoger, soltar y recoger de nuevo
    controlador.jugar()
    t = vista.tiempos_decision
    assert t[3] - t[2] == COSTO_RECOGER and t[4] - t[3] == COSTO_SOLTAR

    controlador, vista, sesion, _ = _juego(tmp_path / "b", ["U", "Q"])
    _dar_objeto(sesion, "itm_pocion_menor")
    sesion.partida.jugador.vida = 100
    controlador.jugar()
    assert vista.tiempos_decision == [0, COSTO_USAR]
    assert sesion.partida.jugador.vida == 108 and len(sesion.partida.jugador.inventario) == 0


def test_rechazos_no_consumen_tiempo_ni_historial(tmp_path):
    comandos = ["xyz", "A", "S", "AB N", "EQ 1", "U 1", "T 1", "R 5", "W"]
    controlador, vista, sesion, ruta = _juego(tmp_path, comandos)
    controlador.jugar()
    # Todos los rechazos ocurren con el reloj en 0; solo 'W' avanza a 100.
    assert vista.tiempos_decision == [0] * len(comandos) + [100]
    assert dict(controlador.contadores())["rechazos"] == len(comandos) - 1
    assert [a for _, a in _acciones(ruta)] == ["esperar"]


def test_recoger_con_inventario_lleno_se_rechaza_sin_tiempo(tmp_path):
    controlador, vista, sesion, ruta = _juego(tmp_path, ["R", "W"])
    sesion.partida.jugador.inventario_max = 0
    controlador.jugar()
    assert vista.tiempos_decision == [0, 0, 100]
    assert vista.textos("Inventario lleno")
    assert len(sesion.partida.jugador.sala_actual.objetos_suelo) == 1


def test_abrir_sin_llave_y_puerta_cerrada_se_rechazan(tmp_path):
    controlador, vista, sesion, _ = _juego(tmp_path, ["N", "AB E", "E", "W"])
    controlador.jugar()
    assert vista.tiempos_decision == [0, 100, 100, 100, 200]
    assert vista.textos("No tienes la llave") and vista.textos("está cerrada")



def test_pergamino_revierte_sin_tiempo_y_se_registra_solo_en_bitacora(tmp_path):
    controlador, vista, sesion, ruta = _juego(tmp_path, ["W", "R", "P", "P", "W"])
    _dar_pergamino(sesion)
    controlador.jugar()
    partida = sesion.partida
    # W 0->100, R 100->125, P vuelve a 100 (antes de recoger), P falla (sin
    # tiempo, se vuelve a mostrar el estado en 100), W 100->200
    assert vista.tiempos_decision == [0, 100, 125, 100, 100, 200]
    assert len(partida.jugador.sala_actual.objetos_suelo) == 1      # antorcha de vuelta
    assert all(n.valor.clase != "pergamino_retroceso"
               for n in partida.jugador.inventario.recorrer_desde_frente())
    assert vista.textos("No tienes pergaminos")
    assert [(t, a) for t, a in _acciones(ruta)] == [
        (0, "esperar"), (100, "recoger 1"), (125, "pergamino"), (100, "esperar")]
    assert partida.acciones_jugador == 2          # esperar + esperar


def test_pergamino_sin_acciones_previas_no_se_consume(tmp_path):
    controlador, vista, sesion, ruta = _juego(tmp_path, ["P", "Q"])
    pergamino = _dar_pergamino(sesion)
    controlador.jugar()
    assert vista.textos("No hay acciones que deshacer")
    assert sesion.partida.jugador.buscar_nodo(pergamino.instancia_id) is not None
    assert _acciones(ruta) == []



def test_partida_completa_hasta_la_victoria_es_reproducible(tmp_path):
    resultados = []
    for corrida in range(2):
        controlador, vista, sesion, ruta = _juego(tmp_path / str(corrida), RUTA_VICTORIA)
        assert controlador.jugar() == "victoria"
        assert vista.fin == "victoria"
        partida = sesion.partida
        assert partida.jugador.sala_actual.id == partida.cripta.sala_salida_id
        assert partida.enemigos_derrotados == 3
        resultados.append((_acciones(ruta), partida.jugador.vida, vista.mensajes))
    assert resultados[0] == resultados[1]


def test_derrota_termina_el_bucle(tmp_path):
    controlador, vista, sesion, _ = _juego(tmp_path, ["N", "W", "W"], vida=None)
    sesion.partida.jugador.vida = 5
    assert controlador.jugar() == "derrota"
    assert vista.fin == "derrota" and not sesion.partida.jugador.vivo


def test_salir_termina_de_forma_controlada(tmp_path):
    controlador, vista, sesion, ruta = _juego(tmp_path, ["W", "Q"])
    assert controlador.jugar() == "en_curso"
    assert vista.fin == "en_curso" and _acciones(ruta) == [(0, "esperar")]
    assert not sesion.partida.historial.registrando      # intervalo confirmado



def test_movimiento_a_sala_sin_contenido_se_rechaza_sin_tiempo(tmp_path):
    fuente = FuenteContada(DatosOffline())
    controlador, vista, sesion, ruta = _juego(tmp_path, ["N", "N", "N", "Q"], fuente=fuente)
    fuente.fallar_contenido = True          # la precarga de 4 y 6 fallará
    controlador.jugar()
    assert sesion.partida.jugador.sala_actual.id == 3
    assert vista.tiempos_decision[-2:] == [200, 200]
    assert vista.textos("sala 4")
    assert [a for _, a in _acciones(ruta)] == ["mover N", "mover N"]


def test_fichas_de_la_sala_actual_quedan_protegidas(tmp_path):
    controlador, vista, sesion, _ = _juego(tmp_path, ["N", "R", "S", "Q"])
    lru = sesion.red._fichas
    fotos = []

    def foto(partida, original=vista.mostrar_estado):
        original(partida)
        fotos.append((partida.jugador.sala_actual.id,
                      lru._nodo("itm_daga_oxidada").valor.en_uso,
                      lru._nodo("trp_dardos").valor.en_uso))
    vista.mostrar_estado = foto
    controlador.jugar()
    # sala 1: nada protegido; sala 2: daga (suelo) y trampa;
    # tras recogerla la daga sigue protegida (inventario); de vuelta en la
    # sala 1 la trampa se libera pero la daga no.
    assert fotos == [(1, 0, 0), (2, 1, 1), (2, 1, 1), (1, 1, 0)]
