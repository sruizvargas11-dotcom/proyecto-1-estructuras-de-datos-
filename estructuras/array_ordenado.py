"""
Array ordenado de pares (clave, valor), mantenido siempre ordenado por
clave. Permite busqueda_binaria() en O(log n). Se usa como indice del
archivo de guardado: clave=id_sala, valor=offset de bytes dentro del
archivo (Sec. 4.10), para saltar directo a una sala sin leer todo el
archivo secuencialmente.

Se construye sobre el vector propio.
"""

from vector_dinamico import Vector


class ArrayOrdenado:
    def __init__(self):
        self._datos = Vector()   # cada elemento es una tupla (clave, valor)

        # contadores de operaciones
        self.contador_inserciones = 0
        self.contador_busquedas = 0
        self.contador_comparaciones = 0

    def __len__(self):
        return len(self._datos)

    def insertar(self, clave, valor):
        """O(n): encuentra la posicion correcta con busqueda binaria
        (O(log n)) pero insertar en el medio de un arreglo exige
        desplazar los elementos siguientes, que es O(n). Esta es la
        razon por la que esta estructura conviene cuando se inserta
        pocas veces y se busca muchas (justo el patron del indice de
        guardado: se escribe una vez por partida, se busca muchas)."""

        posicion = self._encontrar_posicion_de_insercion(clave)

        # desplazar todo lo que esta a partir de 'posicion' una casilla
        # a la derecha, para abrir espacio
        self._datos.agregarValor(None)   # crece el vector en uno
        for i in range(len(self._datos) - 1, posicion, -1):
            self._datos.asignarValor(i, self._datos.obtenerValor(i - 1))

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
            elif clave_actual < clave:
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

            if clave_actual < clave:
                inicio = medio + 1
            else:
                fin = medio - 1

        return inicio