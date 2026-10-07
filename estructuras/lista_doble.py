"""
Lista doblemente enlazada: NodoDoble con punteros anterior y siguiente. A diferencia de la otra lista simple,
eliminar_nodo() y mover_al_frente() son O(1) cuando ya se tiene el nodo a mano, porque no hace falta recorrer
bsucando el anterior. Es la base de la pila, la cola y la lista LRU.
"""

class NodoDoble:
    def __init__(self, valor):
        self.valor = valor
        self.anterior = None
        self.siguiente = None

class ListaDoble:
    def __init__(self):
        self._head = None
        self._cola = None
        self._tamano = 0

        # contadores de operaciones

        self.contador_inserciones = 0
        self.contador_eliminaciones = 0
        self.contador_movimientos_al_frente = 0

    def __len__(self):
        return self._tamano

    def esta_vacia(self):
        return self._tamano == 0

    def head(self):
        return self._head

    def cola(self):
        return self._cola

    def insertar_al_frente(self, valor):
        """O(1). Devuelve el nodo creado, para que quien lo use pueda después
        eliminarlo o moverlo sin tener que volver a buscarlo."""

        nodo = NodoDoble(valor)
        nodo.siguiente = self._head
        if self._head is not None:
            self._head.anterior = nodo
        self._head = nodo
        if self._cola is None:
            self._cola = nodo
        self._tamano += 1
        self.contador_inserciones += 1
        return nodo

    def eliminar_nodo(self, nodo):
        """O(1): no se busca nada, se reconectan directamente los vecinos del nodo
        que ya se tiene en la mano."""

        if nodo.anterior is not None:
            nodo.anterior.siguiente = nodo.siguiente
        else:
            self._head = nodo.siguiente

        if nodo.siguiente is not None:
            nodo.siguiente.anterior = nodo.anterior
        else:
            self._cola = nodo.anterior

        nodo.anterior = None
        nodo.siguiente = None
        self._tamano -= 1
        self.contador_eliminaciones += 1

    def eliminar_del_fondo(self):
        """ Quita y devuelve el valor del extremo más antiguo (la cola).
        O(1) gracias al puntero _cola.
        """
        if self._cola is None:
            return None

        valor = self._cola.valor
        self.eliminar_nodo(self._cola)
        return valor

    def mover_al_frente(self, nodo):
        """Reordena un nodo ya existente para que quede primero, sin crear un nodo nuevo. O(1)."""

        if nodo is self._head:
            return
        # desenganchar sin contarlo como una eliminación lógica

        if nodo.anterior is not None:
            nodo.anterior.siguiente = nodo.siguiente

        else:
            self._head = nodo.siguiente

        if nodo.siguiente is not None:
            nodo.siguiente.anterior = nodo.anterior
        else:
            self._cola = nodo.anterior
        
        nodo.anterior = None
        nodo.siguiente = self._head
        if self._head is not None:
            self._head.anterior = nodo
        self._head = nodo
        if self._cola is None:
            self._cola = nodo

        self.contador_movimientos_al_frente += 1

    def recorrer_desde_frente(self):
        """Generador de nodos (no de valores), de cabeza hacia cola. """
        actual = self._head
        while actual is not None:
            yield actual
            actual = actual.siguiente

    def recorrer_desde_fondo(self):
        """Generador de nodos, de cola hacia el head."""
        actual = self._cola
        while actual is not None:
            yield actual
            actual = actual.anterior

        




