"""La suite es reproducible sin conexión; una petición real es un error del test."""
import pytest
import requests


@pytest.fixture(autouse=True)
def impedir_red_real(monkeypatch):
    def prohibida(*args, **kwargs):
        raise AssertionError('El test intentó usar red real; emplear una fuente falsa o un mock.')
    monkeypatch.setattr(requests.sessions.Session, 'request', prohibida)


@pytest.fixture(autouse=True)
def reportes_red_temporales(monkeypatch, tmp_path):
    """Los tests no escriben en el historial real de partidas/reportes_red.txt."""
    from controlador import reporte_red
    monkeypatch.setattr(reporte_red, 'RUTA_POR_DEFECTO', str(tmp_path / 'reportes_red.txt'))
