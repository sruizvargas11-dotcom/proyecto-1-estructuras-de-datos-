"""
Lista simple (enlazada): NodoSimple con inserción O(1) al inicio.
El recorrido para buscar o eliminar es O(n), porque sin nodo anterior conocido no hay forma de saltar directo
a una posición.
"""

class NodoSimple:
    def __init__(self, valor):
        self.valor = valor
        self.siguiente = None

class ListaSimple:
    def __init__(self):
        self._head = None
        self._tamano = 0

        # contador de operaciones

        self.contador_inserciones = 0
        self.contador_eliminaciones = 0
        self.contador_recorridos = 0

    def __len__(self):
        return self._tamano

    def esta_vacia(self):
        return self._tamano == 0

    def insertar_al_inicio(self, valor):
        """O(1): El nuevo nodo pasa a ser la cabeza directamente. """
        nodo = NodoSimple(valor)
        nodo.siguiente = self._head
        self._tamano += 1
        self.contador_inserciones += 1
        return nodo
    def eliminar_valor(self, valor):
        """Quita la primera ocurrencia del valor. O(N): hay que recorrer buscando, porque no se
        conoce en dónde está."""
        anterior = None
        actual = self._cabeza

        while actual is not None:
            if actual.valor == valor:
                if anterior is None:
                    self._head = actual.siguiente
                else:
                    anterior.siguiente = actual.siguiente
                self._tamano -= 1
                self.contador_eliminaciones += 1
                return True
            anterior = actual
            actual = actual.siguiente
        return False

    def contiene_valor(self, valor):
        for elemento in self.recorrer_valores():
            if elemento == valor:
                return True
        return False

    def recorrer_valores(self):
        """Generador: recorre de head a cola, de uno en uno."""
        self.contador_recorridos += 1
        actual = self._cabeza
        while actual is not None:
            yield actual.valor
            actual = actual.siguiente
