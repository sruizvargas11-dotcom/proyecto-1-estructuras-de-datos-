"""Eventos persistibles: datos explícitos, nunca código Python en el guardado."""


class EjecutorEvento:
    def __init__(self, tipo, dueno=None, parametro=None):
        self.tipo = tipo
        self.dueno = dueno
        self.parametro = parametro

    def __call__(self, reloj):
        from modelo.deltas import DeltaAtributos, DeltaPuerta, DeltaTrampa
        from modelo import efectos
        actor = self.dueno
        if self.tipo == 'decision':
            return
        if self.tipo == 'enemigo':
            return self.parametro.turno_enemigo(actor)
        if self.tipo == 'rearme':
            reloj.registrar(DeltaTrampa(actor))
            actor.rearmar()
        elif self.tipo == 'cierre':
            reloj.registrar(DeltaPuerta(actor))
            actor.cerrada = True
        elif self.tipo == 'veneno':
            estado = actor.estado_veneno
            if estado is None or not actor.vivo:
                return
            restantes = estado.pulsos_restantes - 1
            reloj.registrar(DeltaAtributos(actor, 'estado_veneno'))
            actor.estado_veneno = (efectos.EstadoVeneno(estado.dano_por_pulso, restantes)
                                   if restantes > 0 else None)
            actor.recibir_dano(estado.dano_por_pulso)
            if restantes > 0 and actor.vivo:
                efectos._programar_pulso_veneno(reloj, actor, self.parametro)
        elif self.tipo == 'velocidad':
            if actor.vivo:
                reloj.reprogramar_por_velocidad(actor, self.parametro)
        elif self.tipo == 'antorcha':
            reloj.registrar(DeltaAtributos(actor, 'encendida'))
            actor.encendida = False
        elif self.tipo == 'regeneracion':
            if actor.vivo:
                actor.curar(actor.regeneracion)
                efectos._programar_pulso_regeneracion(reloj, actor)
        else:
            raise ValueError(f'Tipo de ejecutor desconocido: {self.tipo}')
