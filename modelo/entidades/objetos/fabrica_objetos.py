"""Construye instancias de objetos a partir de fichas del catálogo."""

from modelo.entidades.objetos.arma import Arma
from modelo.entidades.objetos.armadura import Armadura
from modelo.entidades.objetos.pocion import Pocion
from modelo.entidades.objetos.antidoto import Antidoto
from modelo.entidades.objetos.llave import Llave
from modelo.entidades.objetos.antorcha import Antorcha
from modelo.entidades.objetos.pergamino_retroceso import PergaminoRetroceso


class FabricaObjetos:
    """Asigna identificadores distintos al contenido de salas y al botín.

    Cada origen usa su propia fábrica y un prefijo: objeto para las salas
    y botin para los enemigos. El contador de contenido sigue el orden de
    las solicitudes; el de botín, el de las acciones del jugador. Así los
    identificadores no dependen de la llegada de respuestas de red.
    """

    def __init__(self, siguiente_id=1, prefijo="objeto"):
        if type(siguiente_id) is not int or siguiente_id < 1:
            raise ValueError(
                "La secuencia debe empezar en un entero positivo."
            )
        if not isinstance(prefijo, str) or not prefijo or ":" in prefijo:
            raise ValueError("El prefijo debe ser texto sin ':'.")

        self.siguiente_id = siguiente_id
        self.prefijo = prefijo

    def crear(self, ficha):
        comunes = (
            f"{self.prefijo}:{self.siguiente_id}",
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


