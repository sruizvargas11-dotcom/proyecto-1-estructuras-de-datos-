"""Estado y operaciones básicas compartidas por jugador y enemigos."""


class Actor:
    def __init__(
        self,
        instancia_id,
        vida_max,
        ataque,
        defensa,
        velocidad,
        sala_actual=None,
        vida=None,
    ):
        if vida_max <= 0:
            raise ValueError("La vida máxima debe ser mayor que cero.")

        if velocidad <= 0:
            raise ValueError("La velocidad debe ser mayor que cero.")

        if vida is None:
            vida = vida_max

        if vida < 0 or vida > vida_max:
            raise ValueError(
                "La vida inicial debe estar entre cero y vida_max."
            )

        self.instancia_id = instancia_id
        self.vida_max = vida_max
        self.vida = vida
        self.ataque = ataque
        self.defensa = defensa
        self.velocidad = velocidad
        self.sala_actual = sala_actual

        self.vivo = vida > 0
        self.evento_actual = None

    def recibir_dano(self, cantidad):
        """Recibe daño ya calculado y devuelve la vida perdida."""
        if cantidad < 0:
            raise ValueError("El daño no puede ser negativo.")

        if not self.vivo:
            return 0

        vida_anterior = self.vida
        self.vida = max(0, self.vida - cantidad)

        if self.vida == 0:
            self.morir()

        return vida_anterior - self.vida

    def curar(self, cantidad):
        """Recupera vida sin superar el máximo ni revivir al actor."""
        if cantidad < 0:
            raise ValueError("La curación no puede ser negativa.")

        if not self.vivo:
            return 0

        vida_anterior = self.vida
        self.vida = min(self.vida_max, self.vida + cantidad)

        return self.vida - vida_anterior

    def morir(self):
        self.vida = 0
        self.vivo = False

        if self.evento_actual is not None:
            self.evento_actual.cancelado = True

