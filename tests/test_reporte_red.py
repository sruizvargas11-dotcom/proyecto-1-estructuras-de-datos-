import io
from datetime import datetime

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import nueva_partida
from controlador.reporte_red import (HistorialReportesRed, construir_reporte, motivo_error,
                                     motivo_partida, registrar_reporte)
from main import main
from tests.test_controlador_juego import VistaGuion

AHORA = datetime(2026, 10, 14, 17, 0, 0)


class FuenteContadaRed(DatosOffline):
    """Lee los datos locales pero cuenta cada llamada como una solicitud HTTP."""

    def __init__(self):
        super().__init__()
        self.requests_realizados = 0

    def modo(self):
        return "simulado"

    def _contar(self, metodo, *args):
        self.requests_realizados += 1
        return getattr(super(), metodo)(*args)

    def listar_criptas(self):
        return self._contar("listar_criptas")

    def datos_cripta(self, cripta_id):
        return self._contar("datos_cripta", cripta_id)

    def esqueleto_cripta(self, cripta_id, pagina):
        return self._contar("esqueleto_cripta", cripta_id, pagina)

    def contenido_salas(self, cripta_id, sala_ids):
        return self._contar("contenido_salas", cripta_id, sala_ids)

    def catalogo(self, tipo_ids):
        return self._contar("catalogo", tipo_ids)

    def version_cripta(self, cripta_id):
        return self._contar("version_cripta", cripta_id)

    def version_catalogo(self):
        return self._contar("version_catalogo")


def _sesion_jugada(tmp_path, fuente, comandos=("N", "W")):
    sesion = nueva_partida(fuente, "cripta-01", str(tmp_path / "cache"), semilla=3)
    sesion.partida.jugador.vida_max = sesion.partida.jugador.vida = 300
    ControladorJuego(sesion, VistaGuion(list(comandos))).jugar()
    return sesion


def _campo(lineas, clave):
    for linea in lineas:
        if linea.startswith(clave + ": "):
            return linea[len(clave) + 2:]
    return None



def test_reporte_con_cifras_coherentes_con_los_contadores(tmp_path):
    fuente = FuenteContadaRed()
    sesion = _sesion_jugada(tmp_path, fuente)
    lineas = construir_reporte(fuente, sesion, "partida", motivo_partida("en_curso"), AHORA)
    realizadas = fuente.requests_realizados
    assert realizadas > 0
    assert _campo(lineas, "cripta") == "cripta-01"
    assert _campo(lineas, "motivo_fin").startswith("salida controlada")
    assert _campo(lineas, "solicitudes_realizadas") == str(realizadas)
    assert _campo(lineas, "presupuesto_solicitudes") == "9"          # de general.json
    assert _campo(lineas, "restantes") == str(9 - realizadas)
    # contenido + catálogo + otras suman exactamente las solicitudes realizadas.
    por_tipo = _campo(lineas, "por_tipo").replace(",", "").split()
    assert int(por_tipo[1]) + int(por_tipo[3]) + int(por_tipo[5]) == realizadas
    assert _campo(lineas, "esqueleto") == "descargado de la fuente"


def test_cache_caliente_usa_menos_solicitudes(tmp_path):
    fria, caliente = FuenteContadaRed(), FuenteContadaRed()
    _sesion_jugada(tmp_path, fria)
    sesion = _sesion_jugada(tmp_path, caliente)
    assert caliente.requests_realizados < fria.requests_realizados
    lineas = construir_reporte(caliente, sesion, "partida", "x", AHORA)
    assert _campo(lineas, "esqueleto") == "desde caché en disco"
    assert "0 desde la fuente" in _campo(lineas, "salas_incorporadas")


def test_offline_no_cuenta_solicitudes(tmp_path):
    sesion = _sesion_jugada(tmp_path, DatosOffline())
    lineas = construir_reporte(sesion.fuente, sesion, "partida", "x", AHORA)
    assert _campo(lineas, "solicitudes_realizadas").startswith("0 (offline")
    assert _campo(lineas, "lotes_leidos_localmente") is not None
    assert _campo(lineas, "por_tipo") is None


def test_reporte_sin_partida_por_error_al_cargar():
    error = RuntimeError("Presupuesto de solicitudes agotado al consultar GET /criptas.")
    lineas = construir_reporte(FuenteContadaRed(), None, "partida", motivo_error(error), AHORA)
    assert _campo(lineas, "motivo_fin").startswith("presupuesto de solicitudes agotado")
    assert _campo(lineas, "presupuesto_solicitudes").startswith("desconocido")


def test_motivos_de_fin():
    assert motivo_partida("victoria").startswith("victoria")
    assert motivo_partida("derrota").startswith("derrota")
    assert motivo_error(ValueError("x")) == "error: ValueError: x"



def test_historial_mas_reciente_primero_y_numeracion(tmp_path):
    historial = HistorialReportesRed(str(tmp_path / "r.txt"))
    for motivo in ("uno", "dos", "tres"):
        historial.agregar([f"motivo_fin: {motivo}"])
    reportes = historial.leer()
    assert [r.numero for r in reportes] == [3, 2, 1]
    assert "motivo_fin: tres" in reportes.obtenerValor(0).texto
    assert historial.cargar().ver_tope().numero == 3


def test_historial_descarta_los_mas_viejos_al_llenarse(tmp_path):
    historial = HistorialReportesRed(str(tmp_path / "r.txt"), capacidad=2)
    for i in range(4):
        historial.agregar([f"motivo_fin: {i}"])
    assert [r.numero for r in historial.leer()] == [4, 3]
    numero, _ = historial.agregar(["motivo_fin: 5"])
    assert numero == 5                     # la numeración no se reinicia


def test_archivo_ajeno_no_se_sobrescribe(tmp_path):
    ruta = tmp_path / "r.txt"
    ruta.write_text("no es un historial\n", encoding="utf-8")
    texto = registrar_reporte(DatosOffline(), None, "partida", "x", ruta=str(ruta), ahora=AHORA)
    assert "no se pudo guardar" in texto and "motivo_fin: x" in texto
    assert ruta.read_text(encoding="utf-8") == "no es un historial\n"



def test_main_registra_partida_y_replay(tmp_path, monkeypatch, capsys):
    import controlador.inicio_partida as inicio
    bitacoras = tmp_path / "bitacoras"
    monkeypatch.setattr(inicio, "ruta_bitacora_por_defecto",
                        lambda cripta_id, semilla, carpeta=None:
                        str(bitacoras / f"{cripta_id}_{semilla}.log"))
    # Enter elige la cripta, luego esperar y salir.
    monkeypatch.setattr("sys.stdin", io.StringIO("\nW\nQ\n"))
    reportes = str(tmp_path / "reportes.txt")
    comunes = ["--offline", "--cache-dir", str(tmp_path / "cache"), "--reportes", reportes,
               "--partidas-dir", str(tmp_path / "partidas")]

    assert main(comunes) == 0
    assert "=== Reporte de red #1 ===" in capsys.readouterr().out

    log = str(next(bitacoras.iterdir()))
    assert main(comunes + ["--replay", log, "--silencioso"]) == 0

    historial = HistorialReportesRed(reportes).leer()
    assert [r.numero for r in historial] == [2, 1]
    assert "modo: replay" in historial.obtenerValor(0).texto
    assert "idéntico a la partida original" in historial.obtenerValor(0).texto
    assert "modo: partida" in historial.obtenerValor(1).texto
    assert "salida controlada" in historial.obtenerValor(1).texto


def test_main_replay_divergente_queda_en_el_historial(tmp_path, capsys):
    ruta_log = str(tmp_path / "p.log")
    sesion = nueva_partida(DatosOffline(), "cripta-01", str(tmp_path / "cache"),
                           semilla=3, ruta_bitacora=ruta_log)
    ControladorJuego(sesion, VistaGuion(["N", "A"])).jugar()
    with open(ruta_log, encoding="utf-8") as f:
        texto = f.read().replace("semilla: 3", "semilla: 4")
    with open(ruta_log, "w", encoding="utf-8") as f:
        f.write(texto)
    reportes = str(tmp_path / "reportes.txt")
    assert main(["--offline", "--replay", ruta_log, "--cache-dir", str(tmp_path / "cache"),
                 "--reportes", reportes, "--silencioso"]) == 3
    assert "motivo_fin: replay divergente" in HistorialReportesRed(reportes).leer() \
        .obtenerValor(0).texto
