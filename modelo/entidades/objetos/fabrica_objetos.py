"""Construye instancias de objetos a partir de fichas del catálogo."""

from modelo.entidades.objetos.arma import Arma
from modelo.entidades.objetos.armadura import Armadura
from modelo.entidades.objetos.pocion import Pocion
from modelo.entidades.objetos.antidoto import Antidoto
from modelo.entidades.objetos.llave import Llave
from modelo.entidades.objetos.antorcha import Antorcha
from modelo.entidades.objetos.pergamino_retroceso import PergaminoRetroceso


class FabricaObjetos:
    """
    Debe existir una sola fábrica compartida por partida.

    siguiente_id identifica la próxima instancia que se creará.
    """

    def __init__(self, siguiente_id=1):
        if type(siguiente_id) is not int or siguiente_id < 1:
            raise ValueError(
                "La secuencia debe empezar en un entero positivo."
            )

        self.siguiente_id = siguiente_id

    def crear(self, ficha):
        comunes = (
            f"objeto:{self.siguiente_id}",
            ficha["id"],
            ficha["nombre"],
            ficha["peso"],
            ficha["valor"],
        )

        clase = ficha["clase"]

        if clase == "arma":
            objeto = Arma(
                *comunes,
                ficha["ataque_bonus"],
            )

        elif clase == "armadura":
            objeto = Armadura(
                *comunes,
                ficha["defensa_bonus"],
            )

        elif clase == "pocion":
            objeto = Pocion(
                *comunes,
                ficha.get("cura", 0),
                ficha.get("modificador_velocidad", 0),
                ficha.get("duracion"),
            )

        elif clase == "antidoto":
            objeto = Antidoto(*comunes)

        elif clase == "llave":
            objeto = Llave(
                *comunes,
                ficha["abre"],
            )

        elif clase == "antorcha":
            objeto = Antorcha(
                *comunes,
                ficha["duracion"],
            )

        elif clase == "pergamino_retroceso":
            objeto = PergaminoRetroceso(*comunes)

        else:
            raise ValueError(
                f"Clase de objeto desconocida: {clase}"
            )

        # Solo avanzamos si la construcción terminó correctamente.
        self.siguiente_id += 1

        return objeto


