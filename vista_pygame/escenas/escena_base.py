"""Reexporta el contrato EscenaBase desde un lugar estable para las escenas
del paquete (vista_pygame/escenas/), sin duplicar su definición: la fuente
de verdad sigue siendo vista_pygame/contratos.py."""
from vista_pygame.contratos import EscenaBase

__all__ = ["EscenaBase"]
