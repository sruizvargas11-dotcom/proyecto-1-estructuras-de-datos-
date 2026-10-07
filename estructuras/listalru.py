"""
Cache LRU de fichas de catalogo, construida sobre la Lista Doble propia.
Nunca usa dict: la busqueda por id es un recorrido lineal O(n), aceptable
porque el tamano esta acotado por capacidad (25 por defecto) y no crece
con el tamano de la cripta (Sec. 4.3, 4.4).

en_uso es un CONTADOR, no un booleano: una misma ficha puede estar
referenciada por varios actores a la vez (dos ratas gigantes comparten
la misma ficha ent_rata_gigante), asi que solo puede desalojarse cuando
el contador llega a 0.
"""

from lista_doble import ListaDoble


class _EntradaCatalogo:
    def __init__(self, id_ficha, ficha):
        self.id_ficha = id_ficha
        self.ficha = ficha
        self.en_uso = 0


class ListaLRU:
    def __init__(self, capacidad=25):
        self._capacidad = capacidad
        self._lista = ListaDoble()

        # contadores de operaciones, para el Documento de Decisiones
        self.contador_aciertos = 0
        self.contador_fallos = 0
        self.contador_desalojos = 0

    def __len__(self):
        return len(self._lista)

    def buscar(self, id_ficha):
        """O(n) en el peor caso, acotado por capacidad. Si la encuentra,
        la mueve al frente (recien usada) y devuelve la ficha. Si no,
        devuelve None sin modificar nada."""
        for nodo in self._lista.recorrer_desde_frente():
            if nodo.valor.id_ficha == id_ficha:
                self._lista.mover_al_frente(nodo)
                self.contador_aciertos += 1
                return nodo.valor.ficha

        self.contador_fallos += 1
        return None

    def insertar(self, id_ficha, ficha):
        """Agrega una ficha nueva al frente. Si no hay espacio, intenta
        desalojar primero la menos usada recientemente que no este en uso."""
        if len(self._lista) >= self._capacidad:
            self._desalojar_si_es_posible()

        entrada = _EntradaCatalogo(id_ficha, ficha)
        self._lista.insertar_al_frente(entrada)

    def marcar_en_uso(self, id_ficha):
        """Un actor u objeto nuevo empieza a referenciar esta ficha."""
        for nodo in self._lista.recorrer_desde_frente():
            if nodo.valor.id_ficha == id_ficha:
                nodo.valor.en_uso += 1
                return

    def desmarcar_en_uso(self, id_ficha):
        """Un actor u objeto deja de referenciar esta ficha (murio, se
        recogio del suelo, etc.). Solo cuando el contador llega a 0
        la ficha vuelve a ser candidata a desalojo."""
        for nodo in self._lista.recorrer_desde_frente():
            if nodo.valor.id_ficha == id_ficha:
                if nodo.valor.en_uso > 0:
                    nodo.valor.en_uso -= 1
                return

    def _desalojar_si_es_posible(self):
        """Recorre desde el fondo (menos usado recientemente) buscando
        la primera entrada con en_uso == 0. Si todas estan en uso, la
        cache crece temporalmente por encima de la capacidad - es
        preferible a perder una ficha que algun actor sigue necesitando."""
        for nodo in self._lista.recorrer_desde_fondo():
            if nodo.valor.en_uso == 0:
                # TODO (ROL 2/ROL 1): persistir nodo.valor.ficha a disco
                # antes de soltarla de memoria, para que recuperarla
                # despues sea una lectura y no una solicitud de red
                self._lista.eliminar_nodo(nodo)
                self.contador_desalojos += 1
                return