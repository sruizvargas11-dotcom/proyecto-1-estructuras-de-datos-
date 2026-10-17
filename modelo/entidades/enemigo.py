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
        self.evento_regeneracion = None

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

        # Una sola pasada por las salidas (antes, una por dirección). Se ubican
        # por dirección y luego se arman en orden N, S, E, O: ese orden hace
        # reproducible la selección aleatoria del errante.
        norte = sur = este = oeste = None
        for salida in self.sala_actual.salidas:
            direccion = salida.direccion
            if direccion == "N":
                if norte is None:
                    norte = salida
            elif direccion == "S":
                if sur is None:
                    sur = salida
            elif direccion == "E":
                if este is None:
                    este = salida
            elif direccion == "O" and oeste is None:
                oeste = salida

        if self.comportamiento == "errante":
            disponibles = Vector()
            for salida in (norte, sur, este, oeste):
                destino = self._destino_abierto(salida)
                if destino is not None:
                    disponibles.agregarValor(destino)

            if len(disponibles) == 0:
                return ("esperar", None)

            indice = azar.randrange(len(disponibles))

            return (
                "mover",
                disponibles.obtenerValor(indice),
            )

        # Rastreador: no necesita la lista de candidatas, solo la mejor; así no
        # se crea un Vector en cada decisión (es el enemigo que más decide).
        mejor = None

        for salida in (norte, sur, este, oeste):
            sala = self._destino_abierto(salida)

            if sala is None:
                continue

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

    @staticmethod
    def _destino_abierto(salida):
        """Sala a la que lleva una salida abierta, o None si no existe o está cerrada."""
        if salida is None or salida.cerrada:
            return None
        if salida.sala_destino is None:
            raise RuntimeError(
                "La salida todavía no tiene destino enlazado."
            )
        return salida.sala_destino
