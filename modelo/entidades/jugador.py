"""Jugador con inventario en lista doble y selección mediante cursor."""

from estructuras.lista_doble import ListaDoble
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar

from modelo.entidades.actor import Actor
from modelo.entidades.objetos.arma import Arma
from modelo.entidades.objetos.armadura import Armadura


class Jugador(Actor):
    def __init__(
        self,
        instancia_id,
        vida_max,
        ataque,
        defensa,
        velocidad,
        inventario_max,
        sala_actual=None,
        vida=None,
    ):
        super().__init__(
            instancia_id,
            vida_max,
            ataque,
            defensa,
            velocidad,
            sala_actual,
            vida,
        )

        if type(inventario_max) is not int or inventario_max < 0:
            raise ValueError(
                "inventario_max debe ser un entero no negativo."
            )

        self.inventario_max = inventario_max
        self.inventario = ListaDoble()
        self.cursor = None

        self.arma_equipada = None
        self.armadura_equipada = None

        self.contador_recogidos = 0
        self.contador_soltados = 0

    def buscar_nodo(self, instancia_id):
        """Busca por ID en O(n); devuelve None si no lo encuentra."""
        for nodo in self.inventario.recorrer_desde_frente():
            if nodo.valor.instancia_id == instancia_id:
                return nodo

        return None

    def recoger(self, objeto):
        """Transfiere un objeto del suelo al inventario si hay espacio."""
        if not self.vivo:
            return False

        if len(self.inventario) >= self.inventario_max:
            return False

        if self.buscar_nodo(objeto.instancia_id) is not None:
            return False

        if self.sala_actual is None:
            return False

        if not self.sala_actual.objetos_suelo.eliminar_valor(objeto):
            return False

        nodo = self.inventario.insertar_al_final(objeto)

        if self.cursor is None:
            self.cursor = nodo

        self.contador_recogidos += 1

        return True

    def siguiente(self):
        """Avanza el cursor; permanece en el último si no hay siguiente."""
        if self.cursor is not None:
            if self.cursor.siguiente is not None:
                self.cursor = self.cursor.siguiente

        return None if self.cursor is None else self.cursor.valor

    def anterior(self):
        """Retrocede el cursor; permanece en el primero si no hay anterior."""
        if self.cursor is not None:
            if self.cursor.anterior is not None:
                self.cursor = self.cursor.anterior

        return None if self.cursor is None else self.cursor.valor

    def soltar_nodo(self, nodo):
        """Retira un nodo conocido y coloca su objeto en el suelo: O(1)."""
        if not self.inventario.pertenece(nodo):
            raise ValueError(
                "El nodo no pertenece al inventario o ya fue retirado."
            )

        if self.sala_actual is None:
            raise ValueError(
                "Hace falta una sala donde soltar el objeto."
            )

        objeto = nodo.valor

        if objeto is self.arma_equipada:
            self.ataque -= objeto.ataque_bonus
            self.arma_equipada = None

        if objeto is self.armadura_equipada:
            self.defensa -= objeto.defensa_bonus
            self.armadura_equipada = None

        if self.cursor is nodo:
            if nodo.siguiente is not None:
                self.cursor = nodo.siguiente
            else:
                self.cursor = nodo.anterior

        self.inventario.eliminar_nodo(nodo)
        self.sala_actual.objetos_suelo.insertar_al_inicio(objeto)

        self.contador_soltados += 1

        return objeto

    def soltar_actual(self):
        """Suelta el objeto seleccionado sin buscarlo."""
        if self.cursor is None:
            return None

        return self.soltar_nodo(self.cursor)

    def soltar(self, instancia_id):
        """Busca en O(n) y después retira el nodo en O(1)."""
        nodo = self.buscar_nodo(instancia_id)

        if nodo is None:
            return None

        return self.soltar_nodo(nodo)

    def equipar_nodo(self, nodo):
        """Equipa un arma o armadura y mueve su nodo al frente."""
        if not self.inventario.pertenece(nodo):
            raise ValueError(
                "El nodo no pertenece al inventario o ya fue retirado."
            )

        objeto = nodo.valor

        if isinstance(objeto, Arma):
            if self.arma_equipada is not None:
                self.ataque -= self.arma_equipada.ataque_bonus

            self.arma_equipada = objeto
            self.ataque += objeto.ataque_bonus

        elif isinstance(objeto, Armadura):
            if self.armadura_equipada is not None:
                self.defensa -= self.armadura_equipada.defensa_bonus

            self.armadura_equipada = objeto
            self.defensa += objeto.defensa_bonus

        else:
            return False

        self.inventario.mover_al_frente(nodo)
        self.cursor = nodo

        return True

    def equipar(self, instancia_id):
        """Localiza el objeto por ID y trata de equiparlo."""
        nodo = self.buscar_nodo(instancia_id)

        if nodo is None:
            return False

        return self.equipar_nodo(nodo)

    def inventario_ordenado(self, criterio="nombre"):
        """Devuelve una vista ordenada sin modificar el inventario real."""
        if criterio not in ("peso", "valor", "nombre"):
            raise ValueError(
                "El criterio debe ser peso, valor o nombre."
            )

        copia = Vector()

        for nodo in self.inventario.recorrer_desde_frente():
            copia.agregarValor(nodo.valor)

        def comparar(a, b):
            primero = getattr(a, criterio)
            segundo = getattr(b, criterio)

            return (
                (primero > segundo)
                - (primero < segundo)
            )

        ordenar(copia, comparar)

        return copia

    @classmethod
    def desde_generales(cls, generales, sala_inicial):
        """Construye al jugador con las estadísticas recibidas."""
        datos = generales["jugador"]

        return cls(
            instancia_id="jugador",
            vida_max=datos["vida_max"],
            ataque=datos["ataque"],
            defensa=datos["defensa"],
            velocidad=datos["velocidad"],
            inventario_max=generales["inventario_max"],
            sala_actual=sala_inicial,
        )

