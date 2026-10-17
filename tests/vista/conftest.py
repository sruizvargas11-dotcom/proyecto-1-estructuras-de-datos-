"""Las pruebas de vista_pygame corren sin pantalla ni audio reales.

Se fija ANTES de cualquier 'import pygame' de los módulos hermanos: pytest
importa conftest.py primero al recolectar este paquete.
"""
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(scope="session", autouse=True)
def _pantalla_dummy():
    """Surface.convert() exige un modo de video ya establecido, incluso con
    el driver dummy. Una sola vez por sesión: las pruebas no abren ventanas."""
    import pygame
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    pygame.quit()
