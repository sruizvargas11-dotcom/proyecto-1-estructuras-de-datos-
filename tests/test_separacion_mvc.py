"""Límites de dependencia exigidos por el §6 del enunciado."""
import ast
from pathlib import Path
import subprocess
import sys


RAIZ = Path(__file__).resolve().parents[1]


def test_modelo_y_estructuras_no_importan_red_disco_ni_presentacion():
    prohibidos = ('pygame', 'requests', 'vista', 'vista_pygame', 'adaptadores', 'persistencia')
    for carpeta in ('modelo', 'estructuras'):
        for ruta in (RAIZ/carpeta).rglob('*.py'):
            arbol = ast.parse(ruta.read_text(encoding='utf-8-sig'))
            for nodo in ast.walk(arbol):
                nombres = ([alias.name for alias in nodo.names] if isinstance(nodo, ast.Import)
                           else [nodo.module or ''] if isinstance(nodo, ast.ImportFrom) else [])
                assert not any(nombre.split('.')[0] in prohibidos for nombre in nombres), ruta
                if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
                    assert nodo.func.id not in ('input', 'print', 'open'), ruta


def test_controlador_grafico_puede_importarse_sin_cargar_pygame():
    codigo = (
        'import sys; from pathlib import Path; '
        'import controlador.controlador_pygame as c; '
        'assert Path(c.__file__).parent.name == "controlador"; '
        'assert not any(n == "pygame" or n.startswith("pygame.") for n in sys.modules)'
    )
    resultado = subprocess.run([sys.executable, '-B', '-c', codigo], cwd=RAIZ,
                               capture_output=True, text=True, timeout=15)
    assert resultado.returncode == 0, resultado.stderr
