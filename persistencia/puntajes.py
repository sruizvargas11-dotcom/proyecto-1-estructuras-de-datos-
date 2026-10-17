"""Adaptador de puntajes para consola y Pygame; un único núcleo y formato.

Lee también el JSON anterior del PR24 a través de utilidades.puntajes.
Escribe siempre el formato del PR25, con clasificación por cripta y versión.
"""
from utilidades import puntajes as nucleo
from utilidades.puntajes import comparar_puntajes

ErrorTablaPuntajes = ValueError
RESULTADOS = nucleo.RESULTADOS


class RegistroPuntaje(nucleo.Puntaje):
    def __init__(self, nombre_jugador, cripta_id, version_cripta, acciones_jugador,
                 enemigos_derrotados, tiempo_final, resultado):
        if type(version_cripta) is int:
            version_cripta = str(version_cripta)
        super().__init__(nombre_jugador, cripta_id, version_cripta, acciones_jugador,
                         enemigos_derrotados, tiempo_final, resultado)

    @classmethod
    def desde_sesion(cls, sesion):
        p = sesion.partida
        return cls(sesion.nombre_jugador, p.cripta_id, p.version_cripta,
                   p.acciones_jugador, p.enemigos_derrotados, p.tiempo, p.estado)

    @classmethod
    def desde_json(cls, datos):
        campos = ('nombre_jugador', 'cripta_id', 'version_cripta',
                  'acciones_jugador', 'enemigos_derrotados', 'tiempo_final', 'resultado')
        if (not isinstance(datos, dict) or len(datos) != len(campos)
                or any(campo not in datos for campo in campos)):
            raise ValueError('Campos de puntaje inválidos.')
        return cls(**datos)

    def a_json(self):
        datos = self.a_datos()
        datos['nombre_jugador'] = datos.pop('nombre')
        return datos


class TablaPuntajes:
    def __init__(self, ruta):
        self.ruta = ruta
        self._tabla = nucleo.TablaPuntajes()

    @property
    def registros(self):
        return self._tabla._puntajes

    def __len__(self):
        return len(self._tabla)

    def __iter__(self):
        return iter(self.registros)

    def obtener(self, indice):
        return self._tabla.obtener(indice)

    def cargar(self):
        self._tabla = nucleo.TablaPuntajes.cargar(self.ruta)
        return self

    def agregar(self, registro):
        return self._tabla.agregar(registro)

    def posicion(self, registro):
        for numero, actual in enumerate(self, 1):
            if actual is registro:
                return numero
        return None

    def guardar(self):
        self._tabla.guardar(self.ruta)

    def registrar(self, sesion):
        registro = RegistroPuntaje.desde_sesion(sesion)
        self._tabla = nucleo.registrar_puntaje(self.ruta, registro)
        # La inserción estable deja el duplicado recién llegado después de los
        # anteriores. Devolver su referencia permite marcar es_actual en GUI.
        actual = None
        datos = registro.a_datos()
        for fila in self:
            if fila.a_datos() == datos:
                actual = fila
        return actual
