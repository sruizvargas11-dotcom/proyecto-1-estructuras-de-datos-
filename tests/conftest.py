"""La suite es reproducible sin conexión; una petición real es un error del test."""
import pytest
import requests


@pytest.fixture(autouse=True)
def impedir_red_real(monkeypatch):
    def prohibida(*args, **kwargs):
        raise AssertionError('El test intentó usar red real; emplear una fuente falsa o un mock.')
    monkeypatch.setattr(requests.sessions.Session, 'request', prohibida)
