"""Objeto que conserva la información de apertura de una llave."""

from modelo.entidades.objetos.objeto import Objeto


class Llave(Objeto):
    CLASE = "llave"

    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        peso,
        valor,
        abre,
    ):
        super().__init__(
            instancia_id,
            tipo_id,
            nombre,
            peso,
            valor,
        )

        self.abre = abre


