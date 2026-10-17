"""
Lista simple (enlazada): NodoSimple con inserción O(1) al inicio y al final.
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
        self._cola = None   # último nodo, para agregar al final en O(1)
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



    def insertar_al_inicio(self, valor):
        """O(1): El nuevo nodo pasa a ser la cabeza directamente. """
        nodo = NodoSimple(valor)
        nodo.siguiente = self._head
        self._head = nodo
        if self._cola is None:
            self._cola = nodo
        self._tamano += 1
        self.contador_inserciones += 1
        return nodo

    def eliminar_valor(self, valor):
        """Elimina la primera coincidencia. Recorre la lista en O(n)."""
        self.contador_intentos_eliminacion += 1
        anterior = None
        actual = self._head

        while actual is not None:
            self.contador_comparaciones += 1
            if actual.valor == valor:
                self._desenlazar(anterior, actual)
                return True
            anterior = actual
            actual = actual.siguiente
        return False

    def eliminar_valor_y_posicion(self, valor):
        """Quita el valor (por identidad) y devuelve la posición que ocupaba, o None.

        Un solo recorrido O(i): sirve para registrar el delta de una salida sin
        recorrer la lista una vez para buscar la posición y otra para eliminar.
        """
        self.contador_intentos_eliminacion += 1
        anterior = None
        actual = self._head
        indice = 0
        while actual is not None:
            self.contador_comparaciones += 1
            if actual.valor is valor:
                self._desenlazar(anterior, actual)
                return indice
            anterior = actual
            actual = actual.siguiente
            indice += 1
        return None

    def ultimo_nodo(self):
        return self._cola

    def quitar_cola(self, nodo, anterior):
        """Quita 'nodo' en O(1) si sigue siendo el último y 'anterior' lo precede
        (None si es la cabeza). Si la lista cambió, no toca nada y devuelve False."""
        enlace = self._head if anterior is None else anterior.siguiente
        if nodo is None or self._cola is not nodo or enlace is not nodo:
            return False
        self._desenlazar(anterior, nodo)
        return True

    def _desenlazar(self, anterior, actual):
        if anterior is None:
            self._head = actual.siguiente
        else:
            anterior.siguiente = actual.siguiente
        if actual is self._cola:
            self._cola = anterior
        self._tamano -= 1
        self.contador_eliminaciones += 1

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
        """O(1) gracias a la referencia a la cola."""
        if self._head is None:
            return self.insertar_al_inicio(valor)
        nodo = NodoSimple(valor)
        self._cola.siguiente = nodo
        self._cola = nodo
        self._tamano += 1
        self.contador_inserciones += 1
        return nodo

    def insertar_varios_al_final(self, valores):
        """Agrega los valores en orden. O(m)."""
        ultimo = self._cola
        for valor in valores:
            nodo = NodoSimple(valor)
            if ultimo is None:
                self._head = nodo
            else:
                ultimo.siguiente = nodo
            ultimo = nodo
            self._cola = nodo
            self._tamano += 1
            self.contador_inserciones += 1

    def conservar_primeros(self, cantidad):
        """Descarta todo lo que sigue a los primeros 'cantidad' elementos. O(cantidad)."""
        if type(cantidad) is not int or not 0 <= cantidad <= self._tamano:
            raise IndexError("Cantidad inválida para la lista.")
        if cantidad == 0:
            self._head = self._cola = None
        else:
            actual = self._head
            for _ in range(cantidad - 1):
                actual = actual.siguiente
            actual.siguiente = None
            self._cola = actual
        self.contador_eliminaciones += self._tamano - cantidad
        self._tamano = cantidad

    def __iter__(self):
        return self.recorrer_valores()

    def insertar_en(self, indice, valor):
        """Inserta en una posición lógica; sirve para restaurar un objeto. O(n)."""
        if type(indice) is not int or not 0 <= indice <= len(self):
            raise IndexError("Posición inválida en la lista.")
        if indice == 0:
            return self.insertar_al_inicio(valor)
        anterior = self._head
        for _ in range(indice - 1):
            anterior = anterior.siguiente
        nodo = NodoSimple(valor)
        nodo.siguiente = anterior.siguiente
        anterior.siguiente = nodo
        if nodo.siguiente is None:
            self._cola = nodo
        self._tamano += 1
        self.contador_inserciones += 1
        return nodo

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

