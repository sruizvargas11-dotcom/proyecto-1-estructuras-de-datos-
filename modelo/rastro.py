"""Rastro sobre las salas del Vector de CriptaModelo, sin duplicar su estado."""
from modelo.deltas import DeltaRastro
from modelo.reloj import entero


class Rastro:
    def __init__(self, cripta, historial=None):
        self._cripta = cripta
        self.historial = historial
        self.contador_registros = 0
        self.contador_consultas = 0

    def _sala(self, sala_id):
        entero(sala_id, 'ID de sala')
        sala = self._cripta.sala_por_id(sala_id)
        if sala is None:
            raise ValueError('La sala no existe.')
        return sala

    def registrar(self, sala_id, tiempo):
        entero(tiempo, 'tiempo')
        sala = self._sala(sala_id)
        if self.historial is not None:
            self.historial.registrar(DeltaRastro(sala))
        anterior = sala.tiempo_rastro
        sala.tiempo_rastro = tiempo
        self.contador_registros += 1
        return anterior

    def consultar(self, sala_id):
        self.contador_consultas += 1
        return self._sala(sala_id).tiempo_rastro

    def es_fresco(self, sala_id, tiempo_actual):
        entero(tiempo_actual, 'tiempo actual')
        marca = self.consultar(sala_id)
        return marca >= 0 and 0 <= tiempo_actual - marca < 400

    def revertir(self, sala_id, tiempo_anterior):
        """Restauración puntual; -1 significa nunca visitada."""
        entero(tiempo_anterior, 'tiempo anterior', -1)
        self._sala(sala_id).tiempo_rastro = tiempo_anterior

    def contadores(self):
        return (('registros', self.contador_registros),
                ('consultas', self.contador_consultas))
