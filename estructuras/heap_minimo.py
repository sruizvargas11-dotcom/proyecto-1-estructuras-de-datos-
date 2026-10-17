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
        # tiempo y secuencia no cambian nunca (reprogramar crea otra entrada):
        # la clave se arma una sola vez y no en cada comparación.
        self._clave = (tiempo, secuencia)
        self.dato = dato
        self.valido = True
        self._propietario = None
        self._en_heap = False

    def clave(self):
        return self._clave

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

    def vista_ordenada(self, n):
        """Hasta las primeras n entradas válidas (no canceladas), en orden de
        (tiempo, secuencia), de solo lectura: no extrae nada, no reordena ni
        copia el heap completo, y no toca ningún contador.

        Usa un heap auxiliar de índices hacia self._datos (no de los eventos en
        sí): arranca en la raíz y, por cada índice que retira, empuja sus dos
        hijos. Como cada índice tiene un único padre, nunca se encola dos veces,
        así que visita como mucho unos pocos nodos más que el resultado pedido,
        nunca el árbol entero (salvo que casi todo esté cancelado cerca de la
        raíz, caso degenerado). Para consulta informativa (p. ej. un panel de
        'próximos turnos'), no para el bucle principal del juego.
        """
        resultado = Vector()
        total = len(self._datos)
        if total == 0 or n <= 0:
            return resultado

        indices = Vector()   # heap auxiliar: índices hacia self._datos

        def clave(pos_aux):
            return self._datos.obtenerValor(indices.obtenerValor(pos_aux)).clave()

        def intercambiar(a, b):
            temp = indices.obtenerValor(a)
            indices.asignarValor(a, indices.obtenerValor(b))
            indices.asignarValor(b, temp)

        def subir(pos):
            while pos > 0:
                padre = (pos - 1) // 2
                if clave(pos) < clave(padre):
                    intercambiar(pos, padre)
                    pos = padre
                else:
                    break

        def bajar(pos):
            largo = len(indices)
            while True:
                izquierda, derecha, menor = 2 * pos + 1, 2 * pos + 2, pos
                if izquierda < largo and clave(izquierda) < clave(menor):
                    menor = izquierda
                if derecha < largo and clave(derecha) < clave(menor):
                    menor = derecha
                if menor == pos:
                    break
                intercambiar(pos, menor)
                pos = menor

        def empujar(indice_real):
            indices.agregarValor(indice_real)
            subir(len(indices) - 1)

        def sacar():
            intercambiar(0, len(indices) - 1)
            indice_real = indices.eliminarUltimo()
            if len(indices):
                bajar(0)
            return indice_real

        empujar(0)
        while len(indices) and len(resultado) < n:
            indice_real = sacar()
            entrada = self._datos.obtenerValor(indice_real)
            izquierda, derecha = 2 * indice_real + 1, 2 * indice_real + 2
            if izquierda < total:
                empujar(izquierda)
            if derecha < total:
                empujar(derecha)
            if entrada.valido:
                resultado.agregarValor(entrada)
        return resultado

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
        datos = self._datos.almacenamiento()
        datos[0]._en_heap = False
        ultimo = self._datos.eliminarUltimo()
        if len(self._datos) > 0:
            datos[0] = ultimo
            self._hundir(0)

    # _flotar y _hundir mueven un "hueco" en lugar de intercambiar: cada nivel
    # cuesta una escritura en vez de tres. Leen el arreglo interno del Vector
    # porque todos los índices ya están dentro del rango.

    def _flotar(self, indice):
        """Flota el elemento en la posición 'indice' hasta que quede en su lugar."""
        datos = self._datos.almacenamiento()
        elemento = datos[indice]
        clave = elemento._clave
        comparaciones = 0
        while indice > 0:
            padre = (indice - 1) >> 1
            comparaciones += 1
            if clave < datos[padre]._clave:
                datos[indice] = datos[padre]
                indice = padre
            else:
                break
        datos[indice] = elemento
        self.contador_comparaciones += comparaciones

    def _hundir(self, indice):
        datos = self._datos.almacenamiento()
        n = len(self._datos)
        elemento = datos[indice]
        clave = elemento._clave
        comparaciones = 0
        while True:
            hijo = 2 * indice + 1
            if hijo >= n:
                break
            derecha = hijo + 1
            if derecha < n:
                comparaciones += 1
                if datos[derecha]._clave < datos[hijo]._clave:
                    hijo = derecha
            comparaciones += 1
            if datos[hijo]._clave < clave:
                datos[indice] = datos[hijo]
                indice = hijo
            else:
                break
        datos[indice] = elemento
        self.contador_comparaciones += comparaciones

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
