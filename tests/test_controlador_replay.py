import pytest

from adaptadores.datos_offline import DatosOffline
from bitacora_partida import BitacoraPartida, ErrorVersionIncompatible
from controlador.controlador_juego import ControladorJuego
from controlador.controlador_replay import ErrorReplayDivergente, reproducir
from controlador.estado_final import lineas_estado, primera_diferencia
from controlador.inicio_partida import nueva_partida
from main import main
from tests.test_controlador_juego import RUTA_VICTORIA, VistaGuion


class OfflineResistente(DatosOffline):
    """Misma cripta-01 con un jugador de 300 de vida, para poder recorrerla
    entera. Se usa igual en la partida original y en el replay."""

    def datos_cripta(self, cripta_id):
        datos = super().datos_cripta(cripta_id)
        datos["jugador"]["vida_max"] = 300
        return datos


def _jugar(tmp_path, comandos, semilla=3, fuente=None, nombre="partida.log"):
    fuente = fuente or OfflineResistente()
    ruta = str(tmp_path / nombre)
    sesion = nueva_partida(fuente, "cripta-01", str(tmp_path / "cache"),
                           semilla=semilla, ruta_bitacora=ruta)
    vista = VistaGuion(comandos)
    controlador = ControladorJuego(sesion, vista)
    controlador.jugar()
    vista.rechazos = controlador.contador_rechazos
    return ruta, sesion, vista


def _es_subsecuencia(corta, larga):
    i = 0
    for elemento in larga:
        if i < len(corta) and corta[i] == elemento:
            i += 1
    return i == len(corta)


def _reescribir(ruta, cambiar):
    with open(ruta, encoding="utf-8") as f:
        lineas = f.read().split("\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(cambiar(lineas)))


def _cache(tmp_path):
    return str(tmp_path / "cache")



def _texto(vector):
    return [linea for linea in vector]


def test_la_partida_cierra_la_bitacora_con_su_estado_final(tmp_path):
    ruta, sesion, _ = _jugar(tmp_path, ["W", "W"])
    bitacora = BitacoraPartida.abrir(ruta)
    assert bitacora.leer_acciones() == [(0, "esperar"), (100, "esperar")]
    tiempo, estado, lineas = bitacora.leer_cierre()
    assert (tiempo, estado) == (200, "en_curso")
    assert _texto(lineas) == _texto(lineas_estado(sesion.partida))
    assert _texto(lineas)[0].startswith("estado=en_curso t=200")


def test_sin_cierre_si_el_bucle_termina_por_un_error(tmp_path):
    class VistaQueFalla(VistaGuion):
        def leer_comando(self):
            if self._comandos:
                return self._comandos.pop(0)
            raise RuntimeError("fallo simulado")

    ruta = str(tmp_path / "p.log")
    sesion = nueva_partida(OfflineResistente(), "cripta-01", _cache(tmp_path),
                           semilla=3, ruta_bitacora=ruta)
    with pytest.raises(RuntimeError):
        ControladorJuego(sesion, VistaQueFalla(["W"])).jugar()
    bitacora = BitacoraPartida.abrir(ruta)
    assert bitacora.leer_acciones() == [(0, "esperar")]
    assert bitacora.leer_cierre() is None


def test_lineas_de_estado_detectan_cualquier_cambio(tmp_path):
    _, sesion, _ = _jugar(tmp_path, ["W"])
    antes = lineas_estado(sesion.partida)
    assert primera_diferencia(antes, lineas_estado(sesion.partida)) is None
    sesion.partida.jugador.vida -= 1
    numero, esperada, obtenida = primera_diferencia(antes, lineas_estado(sesion.partida))
    assert numero == 2 and esperada.startswith("jugador=") and esperada != obtenida


def test_consultar_el_azar_no_lo_consume(tmp_path):
    _, sesion, _ = _jugar(tmp_path, ["W"])
    azar = sesion.partida.reloj.azar
    estado = azar.getstate()
    lineas_estado(sesion.partida)
    assert azar.getstate() == estado


def test_replay_de_la_ruta_completa_es_identico(tmp_path):
    ruta, sesion, vista = _jugar(tmp_path, RUTA_VICTORIA)
    assert sesion.partida.estado == "victoria"
    resultado = reproducir(ruta, OfflineResistente(), _cache(tmp_path))
    assert resultado.verificado is True
    assert resultado.partida.estado == "victoria"
    assert _texto(resultado.lineas_estado) == _texto(lineas_estado(sesion.partida))
    assert resultado.acciones == BitacoraPartida.abrir(ruta).leer_acciones()
    # Mismos mensajes y en el mismo orden; solo faltan los rechazos de la
    # partida original (comandos inválidos que no llegaron a la bitácora).
    assert _es_subsecuencia(resultado.mensajes, vista.mensajes)
    assert len(vista.mensajes) - len(resultado.mensajes) == vista.rechazos > 0


def test_dos_replays_del_mismo_log_coinciden(tmp_path):
    ruta, _, _ = _jugar(tmp_path, RUTA_VICTORIA[:12])
    a = reproducir(ruta, OfflineResistente(), _cache(tmp_path))
    b = reproducir(ruta, OfflineResistente(), _cache(tmp_path))
    assert _texto(a.lineas_estado) == _texto(b.lineas_estado)
    assert a.mensajes == b.mensajes


def test_comandos_que_no_cambian_el_estado_no_afectan_el_replay(tmp_path):
    # P sin pergamino en el inventario también es un rechazo.
    con_ruido = ["I", "xyz", "H", "R 9", "W", "I peso", "P", "N"]
    ruta, sesion, _ = _jugar(tmp_path, con_ruido)
    assert [a for _, a in BitacoraPartida.abrir(ruta).leer_acciones()] == [
        "esperar", "mover N"]
    resultado = reproducir(ruta, OfflineResistente(), _cache(tmp_path))
    assert resultado.verificado
    assert _texto(resultado.lineas_estado) == _texto(lineas_estado(sesion.partida))


def test_log_sin_cierre_se_reproduce_sin_poder_verificar(tmp_path):
    ruta, sesion, _ = _jugar(tmp_path, ["W", "N"])
    _reescribir(ruta, lambda ls: [l for l in ls if " fin " not in l and not l.startswith("= ")])
    resultado = reproducir(ruta, OfflineResistente(), _cache(tmp_path))
    assert resultado.verificado is None
    assert _texto(resultado.lineas_estado) == _texto(lineas_estado(sesion.partida))



def test_version_incompatible_se_detiene_antes_de_ejecutar(tmp_path):
    ruta, _, _ = _jugar(tmp_path, ["W"])
    _reescribir(ruta, lambda ls: ["version_cripta: otra" if l.startswith("version_cripta")
                                  else l for l in ls])
    with pytest.raises(ErrorVersionIncompatible, match="cripta: log='otra'"):
        reproducir(ruta, OfflineResistente(), _cache(tmp_path))


def test_otra_semilla_da_otro_estado_final(tmp_path):
    ruta, _, _ = _jugar(tmp_path, ["N", "A", "A"])
    _reescribir(ruta, lambda ls: ["semilla: 999" if l.startswith("semilla") else l
                                  for l in ls])
    with pytest.raises(ErrorReplayDivergente, match="estado final no coincide"):
        reproducir(ruta, OfflineResistente(), _cache(tmp_path))


def test_accion_en_otro_tiempo_es_divergencia(tmp_path):
    ruta, _, _ = _jugar(tmp_path, ["W", "W"])
    _reescribir(ruta, lambda ls: ["t=150 esperar" if l == "t=100 esperar" else l
                                  for l in ls])
    with pytest.raises(ErrorReplayDivergente, match="t=150.*t=100"):
        reproducir(ruta, OfflineResistente(), _cache(tmp_path))


def test_accion_rechazada_es_divergencia(tmp_path):
    ruta, _, _ = _jugar(tmp_path, ["W", "W"])
    _reescribir(ruta, lambda ls: ["t=100 recoger 7" if l == "t=100 esperar" else l
                                  for l in ls])
    with pytest.raises(ErrorReplayDivergente, match="fue rechazada.*objeto 7"):
        reproducir(ruta, OfflineResistente(), _cache(tmp_path))


def test_acciones_despues_del_final_son_divergencia(tmp_path):
    # Con la vida normal (30) el jugador muere en la sala de las ratas.
    ruta, sesion, _ = _jugar(tmp_path, ["N"] + ["A"] * 10, fuente=DatosOffline())
    assert sesion.partida.estado == "derrota"
    _reescribir(ruta, lambda ls: [l for l in ls if " fin " not in l]
                + ["t=9999 esperar"])
    with pytest.raises(ErrorReplayDivergente, match="sin reproducir"):
        reproducir(ruta, DatosOffline(), _cache(tmp_path))



def test_main_replay_codigos_de_salida(tmp_path, capsys):
    ruta, _, _ = _jugar(tmp_path, ["N"] + ["A"] * 10, fuente=DatosOffline())
    cache = ["--cache-dir", _cache(tmp_path)]
    assert main(["--offline", "--replay", ruta, "--silencioso"] + cache) == 0
    assert "reproducción idéntica" in capsys.readouterr().out

    _reescribir(ruta, lambda ls: ["version_catalogo: x" if l.startswith("version_catalogo")
                                  else l for l in ls])
    assert main(["--offline", "--replay", ruta] + cache) == 2
    assert "Replay detenido" in capsys.readouterr().out


def test_main_replay_divergente_devuelve_3(tmp_path, capsys):
    ruta, _, _ = _jugar(tmp_path, ["N", "A"], fuente=DatosOffline())
    _reescribir(ruta, lambda ls: ["semilla: 1" if l.startswith("semilla") else l
                                  for l in ls])
    assert main(["--offline", "--replay", ruta, "--cache-dir", _cache(tmp_path)]) == 3
    assert "Replay divergente" in capsys.readouterr().out
