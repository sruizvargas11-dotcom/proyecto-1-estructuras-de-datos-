"""
Lista doblemente enlazada: NodoDoble con punteros anterior y siguiente. A diferencia de la otra lista simple,
eliminar_nodo() y mover_al_frente() son O(1) cuando ya se tiene el nodo a mano, porque no hace falta recorrer
buscando el anterior. Es la base de la pila y la lista LRU.
"""


class NodoDoble:
    def __init__(self, valor, propietario=None):
        self.valor = valor
        self.anterior = None
        self.siguiente = None
        self._propietario = propietario

class ListaDoble:
    def __init__(self):
        self._head = None
        self._cola = None
        self._tamano = 0

        # contadores de operaciones

        self.contador_inserciones = 0
        self.contador_eliminaciones = 0
        self.contador_movimientos_al_frente = 0

        self.contador_recorridos_desde_frente = 0
        self.contador_recorridos_desde_fondo = 0
        self.contador_nodos_recorridos = 0

    def __len__(self):
        return self._tamano

    def esta_vacia(self):
        return self._tamano == 0

    def head(self):
        return self._head

    def cola(self):
        return self._cola

    def pertenece(self, nodo):
        return (
                isinstance(nodo, NodoDoble)
                and nodo._propietario is self
        )

    def _validar_nodo(self, nodo):
        if not self.pertenece(nodo):
            raise ValueError(
                "El nodo no pertenece a esta lista o ya fue eliminado."
            )

    def insertar_al_frente(self, valor):
        """O(1). Devuelve el nodo creado, para que quien lo use pueda después
                eliminarlo o moverlo sin tener que volver a buscarlo."""
        nodo = NodoDoble(valor, self)
        nodo.siguiente = self._head

        if self._head is None:
            self._cola = nodo
        else:
            self._head.anterior = nodo

        self._head = nodo
        self._tamano += 1
        self.contador_inserciones += 1

        return nodo

    def insertar_al_final(self, valor):
        nodo = NodoDoble(valor, self)
        nodo.anterior = self._cola

        if self._cola is None:
            self._head = nodo
        else:
            self._cola.siguiente = nodo

        self._cola = nodo
        self._tamano += 1
        self.contador_inserciones += 1

        return nodo

    def _desenlazar(self, nodo):
        """Reconecta los vecinos, sin cambiar tamaño ni pertenencia."""
        if nodo.anterior is None:
            self._head = nodo.siguiente
        else:
            nodo.anterior.siguiente = nodo.siguiente

        if nodo.siguiente is None:
            self._cola = nodo.anterior
        else:
            nodo.siguiente.anterior = nodo.anterior


    def eliminar_nodo(self, nodo):
        """O(1): no se busca nada, se reconectan directamente los vecinos del nodo
                que ya se tiene en la mano."""
        self._validar_nodo(nodo)
        self._desenlazar(nodo)

        nodo.anterior = nodo.siguiente = None
        nodo._propietario = None

        self._tamano -= 1
        self.contador_eliminaciones += 1

    def eliminar_del_fondo(self):
        """ Quita y devuelve el valor del extremo más antiguo (la cola).
                O(1) gracias al puntero _cola.
                """
        if self._cola is None:
            return None

        nodo = self._cola
        self.eliminar_nodo(nodo)

        return nodo.valor

    def mover_al_frente(self, nodo):
        """Reordena un nodo ya existente para que quede primero, sin crear un nodo nuevo. O(1)."""
        self._validar_nodo(nodo)
        self.contador_movimientos_al_frente += 1

        if nodo is self._head:
            return

        self._desenlazar(nodo)

        nodo.anterior = None
        nodo.siguiente = self._head
        self._head.anterior = nodo
        self._head = nodo

    def recorrer_desde_frente(self):
        """Generador de nodos (no de valores), de cabeza hacia cola. """
        self.contador_recorridos_desde_frente += 1
        actual = self._head

        while actual is not None:
            self.contador_nodos_recorridos += 1
            yield actual
            actual = actual.siguiente

    def recorrer_desde_fondo(self):
        """Generador de nodos, de cola hacia el head."""
        self.contador_recorridos_desde_fondo += 1
        actual = self._cola

        while actual is not None:
            self.contador_nodos_recorridos += 1
            yield actual
            actual = actual.anterior

    def contadores(self):
        """Devuelve las métricas sin modificar los contadores."""
        return (
            ("inserciones", self.contador_inserciones),
            ("eliminaciones", self.contador_eliminaciones),
            ("movimientos_al_frente", self.contador_movimientos_al_frente),
            ("recorridos_desde_frente", self.contador_recorridos_desde_frente),
            ("recorridos_desde_fondo", self.contador_recorridos_desde_fondo),
            ("nodos_recorridos", self.contador_nodos_recorridos),
        )

