"""Hasta cinco intervalos entre decisiones del jugador, usando deltas."""
from estructuras.pila import Pila
from estructuras.vector_dinamico import Vector
from modelo.deltas import DeltaReloj


class GrupoDeltas:
    def __init__(self):
        self._deltas = Vector()

    def __len__(self):
        return len(self._deltas)

    def agregar(self, delta):
        if not callable(getattr(delta, 'revertir', None)):
            raise TypeError('El delta debe implementar revertir().')
        if not getattr(delta, 'excluido', False):
            self._deltas.agregarValor(delta)

    def revertir_todo(self):
        while len(self._deltas):
            # Si un delta falla, sigue disponible para diagnosticar el fallo.
            self._deltas.obtenerValor(len(self._deltas) - 1).revertir()
            self._deltas.eliminarUltimo()


class Historial:
    def __init__(self):
        self._grupos = Pila(capacidad_maxima=5)
        self._actual = None
        self._revirtiendo = False
        self.contador_acciones = 0
        self.contador_reversiones = 0
        self.contador_deltas = 0

    def __len__(self):
        return len(self._grupos)

    @property
    def registrando(self):
        return self._actual is not None and not self._revirtiendo

    def iniciar_accion(self, reloj):
        if self._actual is not None:
            raise RuntimeError('Ya hay un intervalo abierto.')
        if reloj.historial is not self:
            raise ValueError('El reloj debe compartir este historial.')
        self._actual = GrupoDeltas()
        self.registrar(DeltaReloj(reloj))

    def registrar(self, delta):
        if not self.registrando or getattr(delta, 'excluido', False):
            return False
        self._actual.agregar(delta)
        self.contador_deltas += 1
        return True

    def confirmar_accion(self):
        """Confirma el intervalo al llegar a la siguiente decisión del jugador.

        Incluye las acciones de enemigos y los efectos ocurridos durante la espera.
        """
        if not self.registrando:
            raise RuntimeError('No hay intervalo abierto para confirmar.')
        self._grupos.apilar_elemento(self._actual)
        self._actual = None
        self.contador_acciones += 1

    def _revertir_grupo(self, grupo):
        self._revirtiendo = True
        try:
            grupo.revertir_todo()
        finally:
            self._revirtiendo = False

    def abortar_accion(self):
        """Deshace un intervalo rechazado; no lo agrega a las cinco acciones."""
        if not self.registrando:
            raise RuntimeError('No hay intervalo abierto.')
        self._revertir_grupo(self._actual)
        self._actual = None

    def revertir(self):
        """Operación del motor; el controlador usa usar_pergamino para el juego."""
        if self._actual is not None:
            raise RuntimeError('Confirma o aborta el intervalo antes de retroceder.')
        grupo = self._grupos.ver_tope()
        if grupo is None:
            return False
        self._revertir_grupo(grupo)
        self._grupos.desapilar_elemento()
        self.contador_reversiones += 1
        return True

    def usar_pergamino(self, jugador, nodo):
        """Consume exactamente uno, sin avanzar reloj ni crear otra acción."""
        if self._actual is not None:
            raise RuntimeError('El pergamino se usa entre decisiones.')
        if not jugador.inventario.pertenece(nodo):
            raise ValueError('El pergamino no pertenece al inventario.')
        if nodo.valor.clase != 'pergamino_retroceso':
            raise ValueError('El objeto no es un pergamino de retroceso.')
        if len(self) == 0 or not jugador.vivo:
            return False
        if jugador.cursor is nodo:
            jugador.cursor = nodo.siguiente or nodo.anterior
        jugador.inventario.eliminar_nodo(nodo)
        return self.revertir()

    def contadores(self):
        return (('acciones', self.contador_acciones),
                ('reversiones', self.contador_reversiones),
                ('deltas', self.contador_deltas),
                ('descartes_por_limite', self._grupos.contador_descartes_por_limite))
