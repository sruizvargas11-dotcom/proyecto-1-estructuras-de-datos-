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

        self.contador_busquedas = 0
        self.contador_intentos_eliminacion = 0
        self.contador_comparaciones = 0
        self.contador_elementos_recorridos = 0

    def __len__(self):
        return self._tamano

    def esta_vacia(self):
        return self._tamano == 0


    """CORRECCION DE NODOS"""

    def insertar_al_inicio(self, valor):
        """O(1): El nuevo nodo pasa a ser la cabeza directamente. """
        nodo = NodoSimple(valor)
        nodo.siguiente = self._head
        self._head = nodo
        self._tamano += 1
        self.contador_inserciones += 1
        return nodo

    def eliminar_valor(self, valor):
        """Quita la primera ocurrencia del valor. O(N): hay que recorrer buscando, porque no se
        conoce en dónde está."""
        self.contador_intentos_eliminacion += 1
        anterior = None
        actual = self._head

        while actual is not None:
            self.contador_comparaciones += 1
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
        self.contador_busquedas += 1
        for elemento in self.recorrer_valores():
            self.contador_comparaciones += 1
            if elemento == valor:
                return True
        return False

    def recorrer_valores(self):
        """Generador: recorre de head a cola, de uno en uno."""
        self.contador_recorridos += 1
        actual = self._head
        while actual is not None:
            self.contador_elementos_recorridos += 1
            yield actual.valor
            actual = actual.siguiente

    def insertar_al_final(self, valor):
        """O(n): esta implementación conserva únicamente la cabeza."""
        if self._head is None:
            return self.insertar_al_inicio(valor)
        actual = self._head
        while actual.siguiente is not None:
            actual = actual.siguiente
        nodo = NodoSimple(valor)
        actual.siguiente = nodo
        self._tamano += 1
        self.contador_inserciones += 1
        return nodo

    def __iter__(self):
        return self.recorrer_valores()

    def a_lista_python(self):
        return list(self.recorrer_valores())

    def contadores(self):
        """Devuelve las métricas sin modificar los contadores."""
        return (
            ("inserciones", self.contador_inserciones),
            ("eliminaciones", self.contador_eliminaciones),
            ("recorridos", self.contador_recorridos),
            ("busquedas", self.contador_busquedas),
            ("intentos_eliminacion", self.contador_intentos_eliminacion),
            ("comparaciones", self.contador_comparaciones),
            ("elementos_recorridos", self.contador_elementos_recorridos),
        )

