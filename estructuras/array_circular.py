"""
Array circular de tamaño fijo: nunca redimensiona, nunca desplaza elementos.
Al llenarse sobreescribe la posición más antigua. Memoria estrictamente constante,
tal y como se pide en la bitácora en pantalla.
"""

class ArrayCircular:
    def __init__(self, capacidad):
        if type(capacidad) is not int or capacidad <= 0:
            raise ValueError("La capacidad debe ser mayor a 0.")
        self._datos = [None] * capacidad
        self._capacidad = capacidad
        self._inicio = 0 # posicion del elemento más antiguo
        self._tamano = 0 # cuántos elementos hay realmente

        # contadores de operaciones

        self.contador_agregados = 0
        self.contador_sobrescrituras = 0
        self.contador_listados = 0
        self.contador_elementos_listados = 0


    def __len__(self):
        return self._tamano

    def esta_lleno(self):
        return self._tamano == self._capacidad

    def agregarValor(self, valor):
        """Agrega al final lógico. Si ya está lleno, sobrescribe la posición más antigua
        y avanza _inicio para que esa deje de contar como el elemento más viejo."""

        posicion = (self._inicio + self._tamano) % self._capacidad

        if self.esta_lleno():
            self._datos[posicion] = valor
            self._inicio = (self._inicio + 1) % self._capacidad
            self.contador_sobrescrituras += 1

        else:
            self._datos[posicion] = valor
            self._tamano += 1

        self.contador_agregados += 1

    def listar_en_orden(self):
        """Del elemento más antiguo al más reciente. """

        self.contador_listados += 1
        resultado = []

        for i in range(self._tamano):
            posicion = (self._inicio + i) % self._capacidad
            resultado.append(self._datos[posicion])
            self.contador_elementos_listados += 1

        return resultado

    def contadores(self):
        """Devuelve las métricas sin modificar los contadores."""
        return (
            ("agregados", self.contador_agregados),
            ("sobrescrituras", self.contador_sobrescrituras),
            ("listados", self.contador_listados),
            ("elementos_listados", self.contador_elementos_listados),
        )
