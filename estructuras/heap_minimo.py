"""
Heap mínimo (cola de prioridad) sobre el vector propio. Ordena por (tiempo, secuencia) para el desempate.
Usa un método de eliminación conocido como 'lazy evaluation': cancelar un evento no lo busca ni lo saca del medio del heap,
simplemente lo marca inválido y se descarta sólo cuando llega a la raíz. Leer la documentación de este método acá: https://realpython.com/python-lazy-evaluation/
"""

from vector_dinamico import Vector

class _EntradaHeap:
    def __init__(self, tiempo, secuencia, dato):
        self.tiempo = tiempo
        self.secuencia = secuencia
        self.dato = dato
        self.valido = True

    def clave(self):
        return (self.tiempo, self.secuencia)

class HeapMinimo:
    def __init__(self):
        self._datos = Vector()
        self._siguiente_secuencia = 0

        # contadores de operaciones

        self._contador_inserciones = 0
        self._contador_extracciones = 0
        self.contador_comparaciones = 0

    def __len__(self):
        return len(self._datos)

    def esta_vacio(self):
        return len(self._datos) == 0

    def insertarEntrada(self, tiempo, dato):
        """
        O(log n). Devuelve la entrada, para poder invalidarla despues si hace falta cancelar o reprogramar un evento.
        """
        entrada = _EntradaHeap(tiempo, self._siguiente_secuencia, dato)
        self._siguiente_secuencia += 1
        self._datos.agregarValor(entrada)
        self._contador_inserciones += 1
        return entrada
    def invalidarEntrada(self, entrada):
        """
        Cancela un evento sin tocar el heap por dentro.
        """
        entrada.valido = False

    def reprogramarEntrada(self, entrada, nuevo_tiempo):
        """
        Invalida la entrada vieja e inserta una nueva con el nuevo tiempo. Devuelve la nueva entrada.
        """
        self.invalidarEntrada(entrada)
        return self.insertarEntrada(nuevo_tiempo, entrada.dato)

    def extraer_minimo(self):
        """
        O(log n). Puede devolver None por dos motivos: el heap está realmente vacio, o solo quedaban entradas canceladas, que se
        descartan automáticamente en el camino.
        """

        while not self.esta_vacio():
            raiz = self._datos.obtenerValor(0)
            self._quitar_raiz()
            if raiz.valido:
                self._contador_extracciones += 1
                return raiz.dato

        return None
    # -- operaciones internas del heap.

    def _quitar_raiz(self):
        ultima_posicion = len(self._datos) - 1
        ultimo = self._datos.obtenerValor(ultima_posicion)
        self._datos.eliminarUltimo()

        if len(self._datos) > 0:
            self._datos.asignarValor(0, ultimo)
            self._hundir(0)

    def _flotar(self, indice):
        """
        Flota el elemento en la posición 'indice' hasta que quede en su lugar.
        """
        while indice > 0:
            padre = (indice - 1) // 2
            self.contador_comparaciones += 1
            if self._datos.obtenerValor(indice).clave() < self._datos.obtenerValor(padre).clave():
                self._intercambiar(indice, padre)
                indice = padre
            else:
                break

    def _hundir(self, indice):
        n = len(self._datos)

        while True:
            izquierda = 2 * indice + 1
            derecha = 2 * indice + 2
            menor = indice

            if izquierda < n:
                self.contador_comparaciones += 1
                if self._datos.obtenerValor(izquierda).clave() < self._datos.obtenerValor(menor).clave():
                    menor = izquierda
            if derecha < n:
                self.contador_comparaciones += 1
                if self._datos.obtenerValor(derecha).clave() < self._datos.obtenerValor(menor).clave():
                    menor = derecha

            if menor == indice:
                break
            self._intercambiar(indice, menor)
            indice = menor

    def _intercambiar(self, i, j):
        temp = self._datos.obtenerValor(i)
        self._datos.asignarValor(i, self._datos.obtenerValor(j))
        self._datos.asignarValor(j, temp)



