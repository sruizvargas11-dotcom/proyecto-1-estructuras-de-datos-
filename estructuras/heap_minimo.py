"""
Heap mínimo (cola de prioridad) sobre el vector propio. Ordena por (tiempo, secuencia) para el desempate.
Usa eliminación diferida ('lazy deletion'): cancelar un evento no lo busca ni lo saca del medio del heap,
simplemente lo marca inválido y se descarta sólo cuando llega a la raíz. Leer la documentación de este método acá: https://realpython.com/python-lazy-evaluation/
"""

from estructuras.vector_dinamico import Vector

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
        self.contador_intentos_extraccion = 0
        self.contador_cancelaciones = 0
        self.contador_reprogramaciones = 0
        self.contador_descartes_cancelados = 0

    def __len__(self):
        return len(self._datos)

    def esta_vacio(self):
        return len(self._datos) == 0

    def insertarEntrada(self, tiempo, dato):
        """
        O(log n). Devuelve la entrada, para poder invalidarla despues si hace falta cancelar o reprogramar un evento.
        """
        if type(tiempo) is not int or tiempo < 0:
            raise ValueError("El tiempo debe ser un entero no negativo.")
        entrada = _EntradaHeap(tiempo, self._siguiente_secuencia, dato)
        self._siguiente_secuencia += 1
        self._datos.agregarValor(entrada)
        self._flotar(len(self._datos) - 1)
        self._contador_inserciones += 1
        return entrada
    def invalidarEntrada(self, entrada):
        """
        Cancela un evento sin tocar el heap por dentro.
        """
        if entrada.valido:
            self.contador_cancelaciones += 1
        entrada.valido = False

    def reprogramarEntrada(self, entrada, nuevo_tiempo):
        """
        Invalida la entrada vieja e inserta una nueva con el nuevo tiempo. Devuelve la nueva entrada.
        """
        nueva = self.insertarEntrada(nuevo_tiempo, entrada.dato)
        self.invalidarEntrada(entrada)
        self.contador_reprogramaciones += 1
        return nueva

    def extraer_minimo(self):
        """
        O((k + 1) log n) si descarta k entradas canceladas. Puede devolver None por dos motivos: el heap está realmente vacio, o solo quedaban entradas canceladas, que se
        descartan automáticamente en el camino.
        """

        self.contador_intentos_extraccion += 1
        while not self.esta_vacio():
            raiz = self._datos.obtenerValor(0)
            self._quitar_raiz()
            if raiz.valido:
                self._contador_extracciones += 1
                return raiz.dato
            self.contador_descartes_cancelados += 1

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

    def contadores(self):
        """Cancelaciones cuenta marcas nuevas hechas por invalidarEntrada.
        Una marca directa del dueño se observa al descartar la entrada.
        Reprogramar también cuenta la inserción y cancelación que realiza.
        """
        return (
            ("inserciones", self._contador_inserciones),
            ("extracciones", self._contador_extracciones),
            ("intentos_extraccion", self.contador_intentos_extraccion),
            ("cancelaciones", self.contador_cancelaciones),
            ("reprogramaciones", self.contador_reprogramaciones),
            ("descartes_cancelados", self.contador_descartes_cancelados),
            ("comparaciones", self.contador_comparaciones),
        )
