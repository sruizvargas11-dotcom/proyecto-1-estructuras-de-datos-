"""Poción con datos de curación o modificación temporal de velocidad."""

from math import isfinite

from modelo.entidades.objetos.objeto import Objeto, no_negativo


class Pocion(Objeto):
    CLASE = "pocion"

    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        peso,
        valor,
        cura=0,
        modificador_velocidad=0,
        duracion=None,
    ):
        super().__init__(
            instancia_id,
            tipo_id,
            nombre,
            peso,
            valor,
        )

        self.cura = no_negativo(cura, "cura")

        if (
            type(modificador_velocidad) not in (int, float)
            or not isfinite(modificador_velocidad)
        ):
            raise ValueError(
                "El modificador de velocidad debe ser un número finito."
            )

        if duracion is not None and (
            type(duracion) is not int or duracion <= 0
        ):
            raise ValueError(
                "La duración debe ser un entero positivo."
            )

        if modificador_velocidad != 0 and duracion is None:
            raise ValueError(
                "Una modificación temporal necesita duración."
            )

        self.modificador_velocidad = modificador_velocidad
        self.duracion = duracion

