"""Cola FIFO con nodos enlazados y una referencia al último nodo.

Encolar y desencolar cuestan O(1). Si se fija una capacidad, al llenarse
se descarta el elemento más antiguo. La precarga usa la cola sin límite
para conservar todas las solicitudes pendientes.
"""

class _NodoCola:
    def __init__(self, valor):
        self.valor = valor
        self.siguiente = None

class Cola:
    def __init__(self, capacidad_maxima = None):
        if capacidad_maxima is not None and (
            type(capacidad_maxima) is not int or capacidad_maxima <= 0
        ):
            raise ValueError("La capacidad debe ser un entero positivo o None.")
        self._frente = None
        self._final = None
        self._tamano = 0
        self._capacidad_maxima = capacidad_maxima

        # contadores de operaciones

        self.contador_encolados = 0
        self.contador_desencolados = 0
        self.contador_descartes_por_limite = 0

        self.contador_intentos_desencolar = 0
        self.contador_consultas_frente = 0

    def __len__(self):
        return self._tamano

    def esta_vacia(self):
        return self._tamano == 0

    def encolar(self, valor):
        """Agrega al final sin recorrer la cola."""
        nodo = _NodoCola(valor)

        # Conectar el último nodo existente con el nuevo.
        if self._final is not None:
            self._final.siguiente = nodo

        # El nuevo nodo siempre pasa a ser el último.
        self._final = nodo

        # Si estaba vacía, también será el primero.
        if self._frente is None:
            self._frente = nodo

        self._tamano += 1
        self.contador_encolados += 1

        if (
                self._capacidad_maxima is not None
                and self._tamano > self._capacidad_maxima
        ):
            self._frente = self._frente.siguiente
            self._tamano -= 1
            self.contador_descartes_por_limite += 1

    def desencolar(self):
        """O(1). Se quita directo de _frente, sin recorrer la cola. Devuelve None si la cola está vacía."""

        self.contador_intentos_desencolar += 1
        if self._frente is None:
            return None

        valor = self._frente.valor
        self._frente = self._frente.siguiente
        if self._frente is None:
            self._final = None
        self._tamano -= 1
        self.contador_desencolados += 1
        return valor

    def ver_frente(self):
        """Consulta el próximo elemento a salir, sin quitarlo. """
        self.contador_consultas_frente += 1
        return self._frente.valor if self._frente is not None else None

    def contadores(self):
        """Devuelve las métricas sin modificar los contadores."""
        return (
            ("encolados", self.contador_encolados),
            ("desencolados", self.contador_desencolados),
            ("descartes_por_limite", self.contador_descartes_por_limite),
            ("intentos_desencolar", self.contador_intentos_desencolar),
            ("consultas_frente", self.contador_consultas_frente),
        )