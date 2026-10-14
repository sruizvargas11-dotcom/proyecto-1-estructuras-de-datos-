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
    Debe existir una sola fábrica por ORIGEN de objetos en cada partida.

    siguiente_id identifica la próxima instancia que se creará. El prefijo separa
    los orígenes: el contenido de las salas usa "objeto" (sus ids dependen solo del
    orden de número de las solicitudes de red) y el botín de los enemigos usa
    "botin" (sus ids dependen solo de las acciones). Así ninguno depende de cuándo
    llega una respuesta y los ids son únicos entre ambos.
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


