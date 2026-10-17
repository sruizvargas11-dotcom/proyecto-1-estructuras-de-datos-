"""Agenda de prioridad ordenada por tiempo y secuencia de inserción.

La secuencia resuelve los empates entre eventos del mismo instante.
Cancelar una entrada la marca como inválida; se retira del heap cuando
llega a la raíz, sin buscarla entre las demás entradas.
"""

from estructuras.vector_dinamico import Vector

class _EntradaHeap:
    def __init__(self, tiempo, secuencia, dato):
        self.tiempo = tiempo
        self.secuencia = secuencia
        self.dato = dato
        self.valido = True
        self._propietario = None
        self._en_heap = False

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
        self.contador_consultas_minimo = 0
        self.contador_limpiezas = 0
        self.contador_restauraciones = 0

    def __len__(self):
        return len(self._datos)

    def esta_vacio(self):
        return len(self._datos) == 0

    def minimo(self):
        """
        Consulta la entrada de la raíz sin extraerla: O(1).
        Devuelve None si el heap está vacío.
        Puede devolver una entrada cancelada; para obtener el próximo
        evento válido, llamar antes a descartar_cancelados().
        """
        self.contador_consultas_minimo += 1
        if self.esta_vacio():
            return None

        return self._datos.obtenerValor(0)

    def descartar_cancelados(self):
        """
        Retira únicamente las entradas canceladas que llegan a la raíz.
        Devuelve cuántas retiró. No extrae ninguna entrada válida.
        Si descarta k entradas, cuesta O(k log n); sin descartes, O(1).
        """
        self.contador_limpiezas += 1
        descartados = 0

        while not self.esta_vacio():
            raiz = self._datos.obtenerValor(0)

            if raiz.valido:
                break

            self._quitar_raiz()
            self.contador_descartes_cancelados += 1
            descartados += 1

        return descartados

    def insertarEntrada(self, tiempo, dato):
        """
        O(log n). Devuelve la entrada, para poder invalidarla despues si hace falta cancelar o reprogramar un evento.
        """
        if type(tiempo) is not int or tiempo < 0:
            raise ValueError("El tiempo debe ser un entero no negativo.")
        entrada = _EntradaHeap(tiempo, self._siguiente_secuencia, dato)
        entrada._propietario = self
        entrada._en_heap = True
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
        """Extrae el dato del próximo evento válido, o None si no queda ninguno.

        Si antes debe retirar k entradas canceladas, cuesta O((k + 1) log n).
        """

        entrada = self.extraer_entrada()
        return None if entrada is None else entrada.dato

    def extraer_entrada(self):
        """Como extraer_minimo, conservando tiempo, secuencia y referencia."""
        self.contador_intentos_extraccion += 1
        while not self.esta_vacio():
            raiz = self._datos.obtenerValor(0)
            self._quitar_raiz()
            if raiz.valido:
                self._contador_extracciones += 1
                return raiz
            self.contador_descartes_cancelados += 1

        return None

    @property
    def siguiente_secuencia(self):
        return self._siguiente_secuencia

    def restaurar_secuencia(self, secuencia):
        """Solo para deshacer, después de cancelar las inserciones revertidas."""
        if type(secuencia) is not int or secuencia < 0:
            raise ValueError("La secuencia debe ser un entero no negativo.")
        self._siguiente_secuencia = secuencia

    def restaurarEntrada(self, entrada):
        """Deshacer restaura el mismo handle y seq; reprogramar crea otro."""
        if entrada._propietario is not self:
            raise ValueError("La entrada no pertenece a este heap.")
        self.contador_restauraciones += 1
        if not entrada._en_heap:
            self._datos.agregarValor(entrada)
            entrada._en_heap = True
            self._flotar(len(self._datos) - 1)
        entrada.valido = True

    # -- operaciones internas del heap.

    def _quitar_raiz(self):
        self._datos.obtenerValor(0)._en_heap = False
        ultima_posicion = len(self._datos) - 1
        ultimo = self._datos.obtenerValor(ultima_posicion)
        self._datos.eliminarUltimo()

        if len(self._datos) > 0:
            self._datos.asignarValor(0, ultimo)
            self._hundir(0)

    def _flotar(self, indice):
        """Flota la entrada desplazando padres, sin intercambios repetidos."""
        vector = self._datos
        datos = vector._datos
        entrada = datos[indice]
        clave = entrada.clave()
        accesos, asignaciones = 1, 1
        while indice > 0:
            padre = (indice - 1) // 2
            superior = datos[padre]
            accesos += 1
            self.contador_comparaciones += 1
            if clave >= superior.clave():
                break
            datos[indice] = superior
            asignaciones += 1
            indice = padre
        datos[indice] = entrada
        vector.contador_accesos += accesos
        vector.contador_asignaciones += asignaciones

    def _hundir(self, indice):
        # Comparar enteros evita crear una tupla por cada hijo examinado.
        vector=self._datos
        n=len(vector)
        datos=vector._datos
        entrada=datos[indice]
        tiempo,secuencia=entrada.tiempo,entrada.secuencia
        accesos,asignaciones=1,1
        while 2*indice+1<n:
            menor=2*indice+1
            hijo=datos[menor]
            accesos+=1
            derecha=menor+1
            if derecha<n:
                otro=datos[derecha]
                accesos+=1
                self.contador_comparaciones+=1
                if otro.tiempo<hijo.tiempo or (otro.tiempo==hijo.tiempo and otro.secuencia<hijo.secuencia):
                    menor,hijo=derecha,otro
            self.contador_comparaciones+=1
            if tiempo<hijo.tiempo or (tiempo==hijo.tiempo and secuencia<=hijo.secuencia):
                break
            datos[indice]=hijo
            asignaciones+=1
            indice=menor
        datos[indice]=entrada
        vector.contador_accesos+=accesos
        vector.contador_asignaciones+=asignaciones

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
            ("consultas_minimo", self.contador_consultas_minimo),
            ("limpiezas", self.contador_limpiezas),
            ("restauraciones", self.contador_restauraciones),
        )
