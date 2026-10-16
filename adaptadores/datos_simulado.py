"""Fuente delegada con latencias reproducibles, sin consumir el azar del juego."""
import math
import time

from adaptadores.fuente_datos import FuenteDeDatos


def suma_verificacion(texto):
    """FNV-1a de 64 bits implementado aquí; estable entre procesos de Python."""
    valor = 14695981039346656037
    for octeto in texto.encode("utf-8"):
        valor = ((valor ^ octeto) * 1099511628211) & 0xffffffffffffffff
    return f"{valor:016x}"


class DatosSimulado(FuenteDeDatos):
    """Añade una demora calculada a partir del patrón y los argumentos.

    El cálculo es independiente del orden de ejecución de los hilos. La fuente
    original conserva sus datos y validaciones, y el reloj virtual no cambia.
    Se puede sustituir esperar para probar las demoras sin detener la ejecución.
    """

    def __init__(self, fuente, patron=0, maximo=0.003, esperar=time.sleep):
        if type(patron) is not int or patron < 0:
            raise ValueError("patron debe ser un entero no negativo")
        if not math.isfinite(maximo) or maximo < 0:
            raise ValueError("maximo debe ser finito y no negativo")
        self.fuente, self.patron = fuente, patron
        self.maximo, self.esperar = maximo, esperar

    def _llamar(self, metodo, *args):
        clave = f"{self.patron}|{metodo}|{args!r}"
        demora = int(suma_verificacion(clave), 16) % 1001 / 1000 * self.maximo
        self.esperar(demora)
        return getattr(self.fuente, metodo)(*args)

    def listar_criptas(self):
        return self._llamar("listar_criptas")

    def datos_cripta(self, cripta_id):
        return self._llamar("datos_cripta", cripta_id)

    def esqueleto_cripta(self, cripta_id, pagina):
        return self._llamar("esqueleto_cripta", cripta_id, pagina)

    def contenido_salas(self, cripta_id, sala_ids):
        return self._llamar("contenido_salas", cripta_id, sala_ids)

    def catalogo(self, tipo_ids):
        return self._llamar("catalogo", tipo_ids)

    def version_cripta(self, cripta_id):
        return self._llamar("version_cripta", cripta_id)

    def version_catalogo(self):
        return self._llamar("version_catalogo")

    def modo(self):
        return "simulado"
