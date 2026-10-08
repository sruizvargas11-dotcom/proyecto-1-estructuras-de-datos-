"""Enemigo y selección de su próxima acción."""

from modelo.entidades.actor import Actor
from estructuras.vector_dinamico import Vector


class Enemigo(Actor):
    def __init__(
        self,
        instancia_id,
        tipo_id,
        nombre,
        vida_max,
        ataque,
        defensa,
        velocidad,
        comportamiento,
        sala_actual=None,
        vida=None,
    ):
        if comportamiento not in (
            "guardián",
            "errante",
            "rastreador",
        ):
            raise ValueError(
                "Comportamiento desconocido: "
                "usa guardián, errante o rastreador."
            )

        super().__init__(
            instancia_id,
            vida_max,
            ataque,
            defensa,
            velocidad,
            sala_actual,
            vida,
        )

        self.tipo_id = tipo_id
        self.nombre = nombre
        self.comportamiento = comportamiento

        self.suelta = Vector()
        self.regeneracion = 0

    @classmethod
    def desde_ficha(
        cls,
        instancia_id,
        ficha,
        sala_actual=None,
        vida=None,
    ):
        enemigo = cls(
            instancia_id,
            ficha["id"],
            ficha["nombre"],
            ficha["vida_max"],
            ficha["ataque"],
            ficha["defensa"],
            ficha["velocidad"],
            ficha["comportamiento"],
            sala_actual,
            vida,
        )

        # Conservamos los tipos de objetos que puede soltar.
        # El motor creará sus instancias cuando corresponda.
        for tipo_id in ficha.get("suelta", []):
            enemigo.suelta.agregarValor(tipo_id)

        enemigo.regeneracion = ficha.get("regeneracion", 0)

        return enemigo

    def decidir_accion(self, jugador, tiempo_actual, azar):
        """
        Devuelve (acción, objetivo), sin ejecutar la acción.

        azar debe ser el generador random.Random compartido
        por la partida.
        """
        if type(tiempo_actual) is not int or tiempo_actual < 0:
            raise ValueError(
                "El tiempo virtual debe ser un entero no negativo."
            )

        if (
            not self.vivo
            or not jugador.vivo
            or self.sala_actual is None
        ):
            return ("esperar", None)

        if self.sala_actual is jugador.sala_actual:
            return ("atacar", jugador)

        if self.comportamiento == "guardián":
            return ("esperar", None)

        disponibles = Vector()

        # Mantener este orden hace reproducible la selección aleatoria.
        for direccion in ("N", "S", "E", "O"):
            salida = self.sala_actual.salida_hacia(direccion)

            if salida is not None and not salida.cerrada:
                if salida.sala_destino is None:
                    raise RuntimeError(
                        "La salida todavía no tiene destino enlazado."
                    )

                disponibles.agregarValor(
                    salida.sala_destino
                )

        if len(disponibles) == 0:
            return ("esperar", None)

        if self.comportamiento == "errante":
            indice = azar.randrange(len(disponibles))

            return (
                "mover",
                disponibles.obtenerValor(indice),
            )

        mejor = None

        for sala in disponibles:
            rastro = sala.tiempo_rastro

            if rastro < 0:
                continue

            antiguedad = tiempo_actual - rastro

            if not 0 <= antiguedad < 400:
                continue

            if (
                mejor is None
                or rastro > mejor.tiempo_rastro
                or (
                    rastro == mejor.tiempo_rastro
                    and sala.id < mejor.id
                )
            ):
                mejor = sala

        if mejor is None:
            return ("esperar", None)

        return ("mover", mejor)

