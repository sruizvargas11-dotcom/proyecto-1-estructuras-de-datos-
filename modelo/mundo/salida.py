"""Salida de una sala a otra."""


class Salida:
    def __init__(
        self,
        direccion,
        sala_destino_id,
        cerrada=False,
        llave=None,
        cierre_automatico=None,
    ):
        self.direccion = direccion
        self.sala_destino_id = sala_destino_id
        self.cerrada = cerrada
        self.llave = llave
        self.cierre_automatico = cierre_automatico
