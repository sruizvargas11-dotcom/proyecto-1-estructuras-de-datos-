"""Objeto equipable que aumenta la defensa del jugador."""

from modelo.entidades.objetos.objeto import Objeto, no_negativo


class Armadura(Objeto):
    CLASE = "armadura"

    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        peso,
        valor,
        defensa_bonus,
    ):
        super().__init__(
            instancia_id,
            tipo_id,
            nombre,
            peso,
            valor,
        )

        self.defensa_bonus = no_negativo(
            defensa_bonus,
            "defensa_bonus",
        )

