"""Índice de pares (clave, valor) ordenados sobre nuestro Vector.

Se usa para relacionar cada sala con su posición en el archivo de guardado.
La búsqueda binaria localiza una clave en O(log n).
"""

from estructuras.vector_dinamico import Vector


class ArrayOrdenado:
    def __init__(self):
        self._datos = Vector()   # cada elemento es una tupla (clave, valor)

        # contadores de operaciones
        self.contador_inserciones = 0
        self.contador_busquedas = 0
        self.contador_comparaciones = 0
        self.contador_actualizaciones = 0
        self.contador_desplazamientos = 0

    def __len__(self):
        return len(self._datos)

    def insertar(self, clave, valor):
        """Inserta o actualiza un par conservando el orden de las claves.

        La posición se busca en O(log n), pero abrir espacio requiere desplazar
        elementos y cuesta O(n). Resulta útil para índices con más consultas
        que modificaciones.
        """

        posicion = self._encontrar_posicion_de_insercion(clave)

        # Un índice tiene una sola entrada por clave: actualizar si ya existe.
        if posicion < len(self._datos):
            self.contador_comparaciones += 1
        if posicion < len(self._datos) and self._datos.obtenerValor(posicion)[0] == clave:
            self._datos.asignarValor(posicion, (clave, valor))
            self.contador_actualizaciones += 1
            return

        # desplazar todo lo que esta a partir de 'posicion' una casilla
        # a la derecha, para abrir espacio
        self._datos.agregarValor(None)   # crece el vector en uno
        for i in range(len(self._datos) - 1, posicion, -1):
            self._datos.asignarValor(i, self._datos.obtenerValor(i - 1))
            self.contador_desplazamientos += 1

        self._datos.asignarValor(posicion, (clave, valor))
        self.contador_inserciones += 1

    def busqueda_binaria(self, clave):
        """O(log n). Devuelve el valor asociado a la clave, o None si
        no existe."""
        self.contador_busquedas += 1
        inicio = 0
        fin = len(self._datos) - 1

        while inicio <= fin:
            medio = (inicio + fin) // 2
            clave_actual, valor_actual = self._datos.obtenerValor(medio)
            self.contador_comparaciones += 1

            if clave_actual == clave:
                return valor_actual
            self.contador_comparaciones += 1
            if clave_actual < clave:
                inicio = medio + 1
            else:
                fin = medio - 1

        return None

    def _encontrar_posicion_de_insercion(self, clave):
        """Busqueda binaria que, en vez de devolver el valor, devuelve
        en que posicion deberia ir una clave nueva para mantener el
        orden."""
        inicio = 0
        fin = len(self._datos) - 1

        while inicio <= fin:
            medio = (inicio + fin) // 2
            clave_actual, _ = self._datos.obtenerValor(medio)
            self.contador_comparaciones += 1

            if clave_actual < clave:
                inicio = medio + 1
            else:
                fin = medio - 1

        return inicio

    def contadores(self):
        """Comparaciones cuenta pruebas entre claves, al insertar y buscar."""
        return (
            ("inserciones", self.contador_inserciones),
            ("actualizaciones", self.contador_actualizaciones),
            ("busquedas", self.contador_busquedas),
            ("comparaciones", self.contador_comparaciones),
            ("desplazamientos", self.contador_desplazamientos),
        )
