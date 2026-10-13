"""Eventos del rol 3: entrada a trampas y cierre automático de salidas.

El controlador valida movimiento/llave/contenido antes de llamar estos métodos.
No consumen tiempo: suceden en el instante de ejecución de la acción.
"""
from modelo.deltas import DeltaPuerta, DeltaTrampa
from modelo.reloj import entero


class Entorno:
    def __init__(self, reloj):
        self.reloj = reloj

    def activar_trampa(self, trampa, actor, aplicar_efecto=None):
        """El efecto opcional recibe (trampa, actor, reloj); por defecto, daño.

        Permite al rol 2 conectar un efecto de catálogo sin decidir aquí sus
        reglas de veneno. Registrar sus cambios mediante el historial compartido.
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

        def rearmar(reloj):
            reloj.registrar(DeltaTrampa(trampa))
            trampa.rearmar()

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
            def cerrar(reloj):
                reloj.registrar(DeltaPuerta(salida))
                salida.cerrada = True
            self.reloj.programar_en(self.reloj.tiempo_actual + intervalo,
                                    cerrar, tipo='cierre_puerta', dueno=salida,
                                    campo='evento_cierre')
        return True
