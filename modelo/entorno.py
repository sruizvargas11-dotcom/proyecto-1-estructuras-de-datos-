"""Activación de trampas y cierre automático de puertas.

El controlador valida el movimiento, la llave y el contenido de la sala
antes de llamar a estos métodos. Sus efectos ocurren en el instante
de la acción y no añaden un costo de tiempo por separado.
"""
from modelo.deltas import DeltaPuerta, DeltaTrampa
from modelo.reloj import entero
from modelo.ejecutor_evento import EjecutorEvento


class Entorno:
    def __init__(self, reloj):
        self.reloj = reloj

    def activar_trampa(self, trampa, actor, aplicar_efecto=None):
        """Activa la trampa y aplica su daño o el efecto recibido.

        El efecto opcional recibe (trampa, actor, reloj) y debe registrar sus
        cambios en el historial compartido para permitir el retroceso.
        """
        if not trampa.armada or not actor.vivo:
            return False
        entero(trampa.rearme, 'rearme', 1)
        if aplicar_efecto is not None and not callable(aplicar_efecto):
            raise TypeError('El aplicador de efecto debe ser una función.')
        self.reloj.vincular_actor(actor)
        self.reloj.registrar(DeltaTrampa(trampa))
        self.reloj.cancelar(trampa.evento_rearme)
        if aplicar_efecto is None:
            trampa.activar(actor)
        else:
            aplicar_efecto(trampa, actor, self.reloj)
            trampa.armada = False

        rearmar = EjecutorEvento('rearme', trampa)

        self.reloj.programar_en(self.reloj.tiempo_actual + trampa.rearme,
                                rearmar, tipo='rearme_trampa', dueno=trampa,
                                campo='evento_rearme')
        return True

    def al_entrar(self, jugador, sala, aplicar_efecto=None):
        """Llamar inmediatamente tras mover al jugador, antes de otro evento."""
        if jugador.sala_actual is not sala:
            raise ValueError('El jugador debe estar ya en la sala destino.')
        activadas = 0
        for trampa in sala.trampas:
            if not jugador.vivo:
                break
            if self.activar_trampa(trampa, jugador, aplicar_efecto):
                activadas += 1
        return activadas

    def abrir(self, salida):
        """Precondición del controlador: llave válida. Abrir no atraviesa."""
        if not salida.cerrada:
            return False
        intervalo = salida.cierre_automatico
        if intervalo is not None:
            entero(intervalo, 'cierre automático')
        self.reloj.registrar(DeltaPuerta(salida))
        self.reloj.cancelar(salida.evento_cierre)
        salida.cerrada = False
        if intervalo is not None:
            cerrar = EjecutorEvento('cierre', salida)
            self.reloj.programar_en(self.reloj.tiempo_actual + intervalo,
                                    cerrar, tipo='cierre_puerta', dueno=salida,
                                    campo='evento_cierre')
        return True
