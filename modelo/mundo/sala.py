"""Representa una sala y las entidades que contiene."""

from estructuras.lista_simple import ListaSimple


class Sala:
    def __init__(self, sala_id, nombre):
        self.id = sala_id
        self.nombre = nombre

        # -1 indica que el jugador todavía no ha dejado rastro aquí.
        self.tiempo_rastro = -1

        self.salidas = ListaSimple()
        self.enemigos_activos = ListaSimple()
        self.enemigos_dormidos = ListaSimple()
        self.objetos_suelo = ListaSimple()
        self.trampas = ListaSimple()

    def salida_hacia(self, direccion):
        """Devuelve la salida indicada, o None si no existe."""
        for salida in self.salidas.recorrer_valores():
            if salida.direccion == direccion:
                return salida

        return None

    def salidas_abiertas(self):
        """Entrega las salidas cuya puerta está abierta."""
        for salida in self.salidas.recorrer_valores():
            if not salida.cerrada:
                yield salida