"""Mapa de la cripta con consultas por identificador de sala."""

from estructuras.vector_dinamico import Vector
from estructuras.ordenamiento import merge_sort


def clave_sala(sala):
    return sala.id


class CriptaModelo:
    def __init__(
        self,
        cripta_id,
        version,
        sala_inicial_id,
        sala_salida_id,
        llave_salida,
        presupuesto_solicitudes,
        inventario_max,
    ):
        self.id = cripta_id
        self.version = version
        self.sala_inicial_id = sala_inicial_id
        self.sala_salida_id = sala_salida_id
        self.llave_salida = llave_salida
        self.presupuesto_solicitudes = presupuesto_solicitudes
        self.inventario_max = inventario_max

        self._salas = Vector()
        self._ordenadas = False

    def __len__(self):
        return len(self._salas)

    def agregar_sala(self, sala):
        self._salas.agregarValor(sala)
        self._ordenadas = False

    def finalizar_carga(self):
        """Ordena las salas y habilita las búsquedas por ID."""
        self._ordenadas = False

        datos = list(self.recorrer_salas())
        ordenadas = merge_sort(datos, clave_sala)

        for i in range(1, len(ordenadas)):
            if ordenadas[i - 1].id == ordenadas[i].id:
                raise ValueError(
                    f"ID de sala repetido: {ordenadas[i].id}"
                )

        for i in range(len(ordenadas)):
            self._salas.asignarValor(i, ordenadas[i])

        self._ordenadas = True

    def sala_por_id(self, sala_id):
        """Busca en O(log n); devuelve None si el ID no existe."""
        if not self._ordenadas:
            raise RuntimeError(
                "Debes finalizar la carga antes de buscar salas."
            )

        izquierda = 0
        derecha = len(self._salas) - 1

        while izquierda <= derecha:
            medio = (izquierda + derecha) // 2
            sala = self._salas.obtenerValor(medio)

            if sala.id == sala_id:
                return sala

            if sala.id < sala_id:
                izquierda = medio + 1
            else:
                derecha = medio - 1

        return None

    def recorrer_salas(self):
        for i in range(len(self._salas)):
            yield self._salas.obtenerValor(i)

