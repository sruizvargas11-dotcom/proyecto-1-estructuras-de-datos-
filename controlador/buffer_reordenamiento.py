import threading

from estructuras.vector_dinamico import Vector

_COMPACTAR_DESDE = 32


class _Ranura:
    __slots__ = ("numero", "solicitud", "lista", "respuesta", "error")

    def __init__(self, numero, solicitud):
        self.numero = numero
        self.solicitud = solicitud
        self.lista = False
        self.respuesta = None
        self.error = None


class BufferReordenamiento:
    def __init__(self):
        self._ranuras = Vector()
        self._base = 1            # número de la ranura en el índice 0
        self._siguiente = 1       # próximo número a entregar al modelo
        self._proximo_numero = 1  # próximo número a asignar
        self._condicion = threading.Condition()
        # contadores (documento, punto 1)
        self.contador_reservas = 0
        self.contador_entregas = 0
        self.contador_adelantadas = 0   # llegaron antes que una anterior
        self.contador_tomadas = 0


    def reservar(self, solicitud):
        """Asigna el siguiente número a 'solicitud' y le crea su ranura."""
        with self._condicion:
            numero = self._proximo_numero
            self._proximo_numero += 1
            self._ranuras.agregarValor(_Ranura(numero, solicitud))
            self.contador_reservas += 1
            return numero

    @property
    def proximo_numero(self):
        return self._proximo_numero

    @property
    def siguiente_a_incorporar(self):
        return self._siguiente

    def en_vuelo(self):
        """Cantidad de solicitudes reservadas que el modelo todavía no tomó."""
        with self._condicion:
            return self._proximo_numero - self._siguiente

    def pendientes(self):
        """Solicitudes aún no tomadas, en orden de número (para buscar una sala)."""
        with self._condicion:
            resultado = Vector()
            for indice in range(self._siguiente - self._base, len(self._ranuras)):
                resultado.agregarValor(self._ranuras.obtenerValor(indice).solicitud)
            return resultado

    def tomar_siguiente(self):
        """(solicitud, respuesta, error) del próximo número si ya llegó; si no, None.

        Nunca salta un número: una respuesta adelantada espera a las anteriores.
        """
        with self._condicion:
            if self._siguiente >= self._proximo_numero:
                return None
            ranura = self._ranura(self._siguiente)
            if not ranura.lista:
                return None
            self._siguiente += 1
            self.contador_tomadas += 1
            resultado = (ranura.solicitud, ranura.respuesta, ranura.error)
            ranura.solicitud = ranura.respuesta = ranura.error = None
            self._compactar()
            return resultado

    def esperar(self, numero, tiempo_maximo=None):
        """Bloquea (tiempo real) hasta que estén listas todas las ranuras <= numero.

        Devuelve False si se agotó tiempo_maximo. Esperar no toca el reloj virtual.
        """
        with self._condicion:
            return self._condicion.wait_for(
                lambda: self._listas_hasta(numero), timeout=tiempo_maximo)

    def abandonar_hasta(self, numero, error):
        """Marca como fallidas las ranuras <= numero que no llegaron a tiempo.

        Una respuesta tardía para una ranura abandonada se descarta.
        """
        with self._condicion:
            for n in range(self._siguiente, min(numero, self._proximo_numero - 1) + 1):
                ranura = self._ranura(n)
                if not ranura.lista:
                    ranura.lista = True
                    ranura.error = error
            self._condicion.notify_all()


    def entregar(self, numero, respuesta=None, error=None):
        """Registra la respuesta (o el error) de la solicitud 'numero'."""
        with self._condicion:
            if numero < self._siguiente or numero >= self._proximo_numero:
                return False
            ranura = self._ranura(numero)
            if ranura.lista:          # abandonada o duplicada
                return False
            ranura.lista = True
            ranura.respuesta = respuesta
            ranura.error = error
            self.contador_entregas += 1
            if not self._listas_hasta(numero - 1):
                self.contador_adelantadas += 1
            self._condicion.notify_all()
            return True


    def _ranura(self, numero):
        return self._ranuras.obtenerValor(numero - self._base)

    def _listas_hasta(self, numero):
        for n in range(self._siguiente, min(numero, self._proximo_numero - 1) + 1):
            if not self._ranura(n).lista:
                return False
        return True

    def _compactar(self):
        consumidas = self._siguiente - self._base
        if consumidas < _COMPACTAR_DESDE or consumidas * 2 < len(self._ranuras):
            return
        nuevas = Vector()
        for indice in range(consumidas, len(self._ranuras)):
            nuevas.agregarValor(self._ranuras.obtenerValor(indice))
        self._ranuras = nuevas
        self._base = self._siguiente

    def contadores(self):
        return (("reservas", self.contador_reservas),
                ("entregas", self.contador_entregas),
                ("adelantadas", self.contador_adelantadas),
                ("tomadas", self.contador_tomadas))
