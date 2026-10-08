"""Datos comunes de todos los objetos del juego."""

from math import isfinite


def no_negativo(valor, nombre):
    """Valida cantidades como peso, valor, curación y bonos."""
    if (
        type(valor) not in (int, float)
        or not isfinite(valor)
        or valor < 0
    ):
        raise ValueError(
            f"{nombre} debe ser un número finito no negativo."
        )

    return valor


class Objeto:
    CLASE = "objeto"

    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        peso,
        valor,
    ):
        if not isinstance(instancia_id, str) or not instancia_id:
            raise ValueError(
                "instancia_id debe ser texto no vacío."
            )

        if not isinstance(tipo_id, str) or not tipo_id:
            raise ValueError(
                "tipo_id debe ser texto no vacío."
            )

        self.instancia_id = instancia_id
        self.tipo_id = tipo_id
        self.clase = self.CLASE
        self.nombre = nombre
        self.peso = no_negativo(peso, "peso")
        self.valor = no_negativo(valor, "valor")

