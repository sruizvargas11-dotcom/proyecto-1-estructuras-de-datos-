"""
Vector dinámico propio: básicamente un array con redimensión al doble [ajustar tamaño].

Usa una lista de Python únicamente como almacenamiento contiguo de bajo nivel, permitido específicamente en: 7. Restricciones de implementación
'Sí se permite list como almacenamiento contiguo de bajo nivel, además de struct, json, requests y bibliotecas
de interfaz.'
La clase por sí sola decide cuándo y cuánto crecer, no python.
"""

class Vector:
    CAPACIDAD_INICIAL = 4

    def __init__(self):
        self._datos = [None] * self.CAPACIDAD_INICIAL
        self._tamano = 0 # -> tamaño real del vector
        self._capacidad = self.CAPACIDAD_INICIAL

        # contadores de operaciones
        self.contador_agregados = 0
        self.contador_accesos = 0
        self.contador_redimensiones = 0 # cuántas veces el vector necesita redimensionarse

    def __len__(self):
        return self._tamano

    def agregarValor(self, valor):
        """
        Agrega al final; si no hay espacio, duplica la capacidad primero.
        """
        if self._tamano == self._capacidad:
            self._redimensionarVector(self._capacidad * 2)
        self._datos[self._tamano] = valor
        self._tamano += 1
        self.contador_agregados += 1

    def obtenerValor(self, indice):
        """ Acceso O(1) por posición. """
        self._validar_indice(indice)
        self.contador_accesos += 1
        return self._datos[indice]

    def asignarValor(self, indice, valor):
        """ Sobrescribe el valor en una posición que ya existe. """
        self._validar_indice(indice)
        self._datos[indice] = valor

    """CORRECCION DE REDIMENSION"""
    def _redimensionarVector(self, nueva_capacidad):
        datos_nuevos = [None] * nueva_capacidad

        # Leer del almacenamiento original hasta terminar la copia.
        for i in range(self._tamano):
            datos_nuevos[i] = self._datos[i]

        # Estas instrucciones se ejecutan una sola vez, después del ciclo.
        self._datos = datos_nuevos
        self._capacidad = nueva_capacidad
        self.contador_redimensiones += 1


    def _validar_indice(self, indice):
        if indice < 0 or indice >= self._tamano:
            raise IndexError(f"Índice {indice} fuera de rango (tamaño actual: {self._tamano})")



