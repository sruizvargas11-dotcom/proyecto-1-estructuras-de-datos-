"""Estado y operaciones básicas de una trampa de sala."""

from modelo.entidades.objetos.objeto import no_negativo


class Trampa:
    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        dano,
        rearme=None,
    ):
        self.instancia_id = instancia_id
        self.tipo_id = tipo_id
        self.nombre = nombre
        self.dano = no_negativo(dano, "daño")

        self.rearme = 300 if rearme is None else rearme

        if type(self.rearme) is not int or self.rearme <= 0:
            raise ValueError(
                "El rearme debe ser un entero positivo."
            )

        self.armada = True

    def activar(self, actor):
        """Aplica daño una vez y devuelve la vida realmente perdida."""
        if not self.armada or not actor.vivo:
            return 0

        perdido = actor.recibir_dano(self.dano)
        self.armada = False

        return perdido

    def rearmar(self):
        """Deja la trampa preparada para otra activación."""
        self.armada = True

    @classmethod
    def desde_ficha(cls, instancia_id, ficha):
        """Construye una trampa a partir de su ficha del catálogo."""
        return cls(
            instancia_id,
            ficha["id"],
            ficha["nombre"],
            ficha["daño"],
            ficha.get("rearme"),
        )

