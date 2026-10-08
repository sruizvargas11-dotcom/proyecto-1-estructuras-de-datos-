"""Objeto equipable que aumenta el ataque del jugador."""

from modelo.entidades.objetos.objeto import Objeto, no_negativo


class Arma(Objeto):
    CLASE = "arma"

    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        peso,
        valor,
        ataque_bonus,
    ):
        super().__init__(
            instancia_id,
            tipo_id,
            nombre,
            peso,
            valor,
        )

        self.ataque_bonus = no_negativo(
            ataque_bonus,
            "ataque_bonus",
        )

