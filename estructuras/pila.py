"""
Pila (LIFO) con capacidad máxima fija. Al superar el límite, descarta automáticamente el
elemento más antiguo (el fondo), no el que se intenta apilar. Construida sobre ListaDoble:
apilar/desapilar usan el frente, y el descarte por límite usa el fondo. Para el historial de retroceso,
cada elemento es un delta, nunca una copia completa.
"""

from lista_doble import ListaDoble

class Pila:
    def __init__(self, capacidad_maxima = None):
        self._lista = ListaDoble()
        self._capacidad_maxima = capacidad_maxima

        # contadores de operaciones

        self.contador_apilados = 0
        self.contador_desapilados = 0
        self.contador_descartes_por_limite = 0

    def __len__(self):
        return len(self._lista)
    
    def esta_vacia(self):
        return self._lista.esta_vacia()

    def apilar_elemento(self, valor):
        """O(1). Si al agregar se supera la capacidad, descarta el más antiguo (el fondo),
        no el que se acaba de apilar. """

        self._lista.insertar_al_frente(valor)
        self.contador_apilados += 1

        if self._capacidad_maxima is not None and len(self._lista) > self._capacidad_maxima:
            self._lista.eliminar_del_fondo()
            self.contador_descartes_por_limite += 1

    def desapilar_elemento(self):
        """O(1). Quita y devuelve el elemento más reciente (el frente). 
        Devuelve None si la pila está vacía."""

        nodo_head = self._lista.head()
        if nodo_head is None:
            return None

        self._lista.eliminar_nodo(nodo_head)
        self.contador_desapilados += 1
        return nodo_head.valor

    def ver_tope(self):
        """Consulta el elemento más reciente sin quitarlo. """

        nodo_head = self._lista.head()
        return nodo_head.valor if nodo_head is not None else None
    
        
