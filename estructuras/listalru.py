"""
Caché LRU sobre una lista doble propia, sin dict como índice.

Buscar una ficha cuesta O(n).
Moverla al frente, una vez localizado su nodo, cuesta O(1).

El coordinador deberá persistir las fichas antes de que puedan
ser desalojadas de memoria.
"""

from estructuras.lista_doble import ListaDoble


class _EntradaCatalogo:
    def __init__(self, id_ficha, ficha):
        self.id_ficha = id_ficha
        self.ficha = ficha
        self.en_uso = 0


class ListaLRU:
    def __init__(self, capacidad=25):
        if type(capacidad) is not int or capacidad <= 0:
            raise ValueError(
                "La capacidad debe ser un entero positivo."
            )

        self._capacidad = capacidad
        self._lista = ListaDoble()

        self.contador_aciertos = 0
        self.contador_fallos = 0
        self.contador_desalojos = 0
        self.contador_inserciones = 0
        self.contador_actualizaciones = 0
        self.contador_rechazos_capacidad = 0
        self.contador_referencias_adquiridas = 0
        self.contador_referencias_liberadas = 0
        self.contador_comparaciones = 0

    def __len__(self):
        return len(self._lista)

    def _nodo(self, id_ficha):
        """Localiza una entrada sin cambiar su orden ni los aciertos/fallos."""
        for nodo in self._lista.recorrer_desde_frente():
            self.contador_comparaciones += 1
            if nodo.valor.id_ficha == id_ficha:
                return nodo

        return None

    def buscar(self, id_ficha):
        """Devuelve la ficha y la marca como recientemente consultada."""
        nodo = self._nodo(id_ficha)

        if nodo is None:
            self.contador_fallos += 1
            return None

        self.contador_aciertos += 1
        self._lista.mover_al_frente(nodo)

        return nodo.valor.ficha

    # Permite usar también el nombre empleado en el plan.
    obtener = buscar

    def insertar(self, id_ficha, ficha):
        """
        Devuelve True si la ficha quedó almacenada.

        Devuelve False si no hay espacio y todas las fichas
        existentes están protegidas.
        """
        if ficha is None:
            raise ValueError(
                "None se reserva para indicar una ficha ausente."
            )

        existente = self._nodo(id_ficha)

        if existente is not None:
            if (
                existente.valor.en_uso > 0
                and existente.valor.ficha is not ficha
            ):
                raise ValueError(
                    "No se sustituye una ficha mientras esté en uso."
                )

            existente.valor.ficha = ficha
            self._lista.mover_al_frente(existente)
            self.contador_actualizaciones += 1
            return True

        if len(self) >= self._capacidad:
            if not self._desalojar_si_es_posible():
                self.contador_rechazos_capacidad += 1
                return False

        entrada = _EntradaCatalogo(id_ficha, ficha)
        self._lista.insertar_al_frente(entrada)
        self.contador_inserciones += 1

        return True

    def marcar_en_uso(self, id_ficha):
        """Registra una nueva referencia activa a la ficha."""
        nodo = self._nodo(id_ficha)

        if nodo is None:
            raise KeyError(id_ficha)

        nodo.valor.en_uso += 1
        self.contador_referencias_adquiridas += 1

    def desmarcar_en_uso(self, id_ficha):
        """Libera una referencia activa, sin permitir valores negativos."""
        nodo = self._nodo(id_ficha)

        if nodo is None:
            raise KeyError(id_ficha)

        if nodo.valor.en_uso == 0:
            raise ValueError(
                "La ficha no tenía referencias activas."
            )

        nodo.valor.en_uso -= 1
        self.contador_referencias_liberadas += 1

    def _desalojar_si_es_posible(self):
        """Retira la ficha libre menos recientemente utilizada."""
        for nodo in self._lista.recorrer_desde_fondo():
            if nodo.valor.en_uso == 0:
                self._lista.eliminar_nodo(nodo)
                self.contador_desalojos += 1
                return True

        return False

    def contadores(self):
        """Consultar las métricas no cambia el orden de la caché."""
        return (
            self.contador_aciertos,
            self.contador_fallos,
            self.contador_desalojos,
        )



    def contadores_operaciones(self):
        """Detalle adicional; contadores() conserva su contrato original."""
        return (
            ("busquedas", self.contador_aciertos + self.contador_fallos),
            ("aciertos", self.contador_aciertos),
            ("fallos", self.contador_fallos),
            ("desalojos", self.contador_desalojos),
            ("inserciones", self.contador_inserciones),
            ("actualizaciones", self.contador_actualizaciones),
            ("rechazos_capacidad", self.contador_rechazos_capacidad),
            ("referencias_adquiridas", self.contador_referencias_adquiridas),
            ("referencias_liberadas", self.contador_referencias_liberadas),
            ("comparaciones", self.contador_comparaciones),
        )
