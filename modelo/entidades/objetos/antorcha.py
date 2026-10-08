"""Objeto que proporciona iluminación durante un intervalo virtual."""

from modelo.entidades.objetos.objeto import Objeto


class Antorcha(Objeto):
    CLASE = "antorcha"

    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        peso,
        valor,
        duracion,
    ):
        super().__init__(
            instancia_id,
            tipo_id,
            nombre,
            peso,
            valor,
        )

        if type(duracion) is not int or duracion <= 0:
            raise ValueError(
                "La duración debe ser un entero positivo."
            )

        self.duracion = duracion


