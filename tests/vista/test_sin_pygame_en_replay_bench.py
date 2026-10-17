"""Regla 5: --replay y --bench nunca importan ni inicializan pygame.

Corre en un subproceso aparte (sys.modules es del proceso: una vez que
cualquier otra prueba de tests/vista/ importa pygame, seguiría cargado para
el resto de la sesión de pytest). stdout/stderr van a un archivo, no a un
pipe: evita un problema conocido de Windows al heredar descriptores cuando
pytest ya está capturando la salida del proceso de prueba.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _correr(args, cwd, timeout=60):
    with tempfile.TemporaryDirectory() as carpeta:
        salida = Path(carpeta) / "salida.txt"
        codigo = (
            "import sys; "
            "import main; "
            f"r = main.main({args!r}); "
            "huella = 'PYGAME_CARGADO' if any("
            "n == 'pygame' or n.startswith('pygame.') or n.startswith('vista_pygame') "
            "for n in sys.modules) else 'SIN_PYGAME'; "
            "print(huella); "
            "sys.exit(r)"
        )
        with open(salida, "wb") as f:
            resultado = subprocess.run(
                [sys.executable, "-c", codigo], cwd=cwd,
                stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT,
                timeout=timeout,
            )
        texto = salida.read_text(encoding="utf-8", errors="replace")
        return resultado.returncode, texto


def test_bench_no_carga_pygame():
    with tempfile.TemporaryDirectory() as carpeta:
        salida = Path(carpeta) / "salida.txt"
        # Reemplaza main_bench por uno trivial: lo que importa es la ruta de
        # importación de main.py --bench, no repetir la medición completa.
        codigo = (
            "import sys; import bench.runner; "
            "bench.runner.main_bench = lambda: []; "
            "import main; "
            "r = main.main(['--bench']); "
            "huella = 'PYGAME_CARGADO' if any("
            "n == 'pygame' or n.startswith('pygame.') or n.startswith('vista_pygame') "
            "for n in sys.modules) else 'SIN_PYGAME'; "
            "print(huella); sys.exit(r)"
        )
        with open(salida, "wb") as f:
            resultado = subprocess.run(
                [sys.executable, "-c", codigo], cwd=str(Path(__file__).resolve().parents[2]),
                stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, timeout=30)
        texto = salida.read_text(encoding="utf-8", errors="replace")
    assert "SIN_PYGAME" in texto, texto
    assert resultado.returncode == 0, texto


def test_replay_no_carga_pygame(tmp_path):
    from adaptadores.datos_offline import DatosOffline
    from controlador.controlador_juego import ControladorJuego
    from controlador.inicio_partida import nueva_partida

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

    ruta_log = tmp_path / "partida.log"
    sesion = nueva_partida(DatosOffline(), "cripta-01", str(tmp_path / "cache"),
                           semilla=1, ruta_bitacora=str(ruta_log))
    ControladorJuego(sesion, VistaGuion(["W", "Q"])).jugar()

    raiz = Path(__file__).resolve().parents[2]
    codigo, texto = _correr(
        ["--offline", "--cache-dir", str(tmp_path / "cache"), "--replay", str(ruta_log)],
        cwd=str(raiz))
    assert "SIN_PYGAME" in texto, texto
    assert codigo == 0, texto
