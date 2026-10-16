from bitacora_partida import BitacoraPartida, ErrorVersionIncompatible
from controlador.controlador_juego import ControladorJuego
from controlador.estado_final import lineas_estado, primera_diferencia
from controlador.inicio_partida import nueva_partida


class ErrorReplayDivergente(ValueError):
    """La reproducción dejó de coincidir con lo que dice la bitácora."""


class _GrabadoraBitacora:
    """Ocupa el lugar de la bitácora durante el replay: no escribe archivo,
    guarda en memoria lo que el controlador registra para compararlo."""

    def __init__(self):
        self.acciones = []
        self.cierre = None

    def registrar(self, tiempo, accion):
        self.acciones.append((tiempo, accion))

    def registrar_cierre(self, tiempo, estado, lineas):
        self.cierre = (tiempo, estado, lineas)

    def cerrar(self):
        pass


class GuionReplay:
    """Vista no interactiva: entrega las acciones del log y verifica, antes de
    cada una, que la anterior se ejecutó y que el turno llegó en el mismo t."""

    def __init__(self, acciones, grabadora, escribir=None):
        self._acciones = acciones
        self._grabadora = grabadora
        self._escribir = escribir
        self._siguiente = 0
        self._tiempo_decision = None
        self.mensajes = []          # (t, texto) en orden: la secuencia completa
        self.ultimo_mensaje = None

    def agregar_mensaje(self, tiempo, texto):
        self.mensajes.append((tiempo, texto))
        self.ultimo_mensaje = texto
        if self._escribir is not None:
            self._escribir(f"  [t={tiempo}] {texto}")

    def mostrar_estado(self, partida):
        self._tiempo_decision = partida.tiempo

    def mostrar_inventario(self, partida, objetos, criterio):
        pass

    def mostrar_ayuda(self):
        pass

    def mostrar_fin(self, partida):
        pass

    def _verificar_anterior(self):
        ejecutadas = len(self._grabadora.acciones)
        if ejecutadas < self._siguiente:
            tiempo, accion = self._acciones[self._siguiente - 1]
            raise ErrorReplayDivergente(
                f"La acción #{self._siguiente} 't={tiempo} {accion}' fue rechazada al "
                f"reproducirla: {self.ultimo_mensaje}")

    def leer_comando(self):
        self._verificar_anterior()
        if self._siguiente == len(self._acciones):
            return "Q"
        tiempo, accion = self._acciones[self._siguiente]
        if tiempo != self._tiempo_decision:
            raise ErrorReplayDivergente(
                f"La acción #{self._siguiente + 1} '{accion}' se registró en t={tiempo}, "
                f"pero al reproducir el turno del jugador llegó en t={self._tiempo_decision}.")
        self._siguiente += 1
        self.ultimo_mensaje = None
        if self._escribir is not None:
            self._escribir(f"t={tiempo} > {accion}")
        return accion

    def pendientes(self):
        return len(self._acciones) - self._siguiente


class ResultadoReplay:
    def __init__(self, sesion, guion, grabadora, cierre_original):
        self.sesion = sesion
        self.partida = sesion.partida
        self.mensajes = guion.mensajes
        self.acciones = grabadora.acciones
        self.cierre = grabadora.cierre
        self.cierre_original = cierre_original

    @property
    def lineas_estado(self):
        return self.cierre[2] if self.cierre else lineas_estado(self.partida)

    @property
    def diferencia(self):
        """None si el estado final coincide con el del log; si no, (línea, log, replay)."""
        if not self.comparable:
            return None
        return primera_diferencia(self.cierre_original[2], self.lineas_estado)

    @property
    def comparable(self):
        return self.cierre_original is not None and len(self.cierre_original[2]) > 0

    @property
    def verificado(self):
        """True si el estado final es idéntico al del log; None si no hay con qué comparar."""
        if not self.comparable:
            return None
        return self.diferencia is None


def reproducir(ruta_log, fuente, carpeta_cache=None, escribir=None, cache_size=25):
    """Reproduce la bitácora. Lanza ErrorVersionIncompatible antes de ejecutar
    cualquier acción si los datos actuales no son los del log, y
    ErrorReplayDivergente si la reproducción se separa de lo registrado."""
    bitacora = BitacoraPartida.abrir(ruta_log)
    acciones = bitacora.leer_acciones()
    cierre_original = bitacora.leer_cierre()
    permitidas = ('mover', 'atacar', 'esperar', 'recoger', 'soltar',
                 'equipar', 'usar', 'abrir', 'pergamino')
    for tiempo, accion in acciones:
        if accion.split(' ')[0] not in permitidas:
            raise ErrorReplayDivergente('Bitácora con acción no reproducible.')

    # Cargar la cripta y el catálogo no ejecuta acciones; da las versiones
    # vigentes sin gastar solicitudes extra.
    sesion = nueva_partida(fuente, bitacora.cripta_id, carpeta_cache,
                           semilla=bitacora.semilla, ruta_bitacora=None, cache_size=cache_size)
    try:
        return _reproducir_sesion(sesion, bitacora, acciones, cierre_original, escribir)
    except (ErrorVersionIncompatible, ErrorReplayDivergente) as error:
        error.sesion = sesion        # el reporte de red la necesita
        raise
    finally:
        sesion.red.cerrar(5)


def _reproducir_sesion(sesion, bitacora, acciones, cierre_original, escribir):
    try:
        bitacora.verificar_compatibilidad(str(sesion.partida.version_cripta),
                                          str(sesion.partida.version_catalogo))
    except ErrorVersionIncompatible:
        sesion.red.cerrar(5)
        raise

    grabadora = _GrabadoraBitacora()
    sesion.bitacora = grabadora
    guion = GuionReplay(acciones, grabadora, escribir)
    ControladorJuego(sesion, guion).jugar()

    # Una acción rechazada ya se detectó en leer_comando: tras un rechazo el
    # controlador vuelve a pedir comando antes de que la partida pueda terminar.
    if guion.pendientes():
        tiempo, accion = acciones[len(acciones) - guion.pendientes()]
        raise ErrorReplayDivergente(
            f"La partida terminó ({sesion.partida.estado}, t={sesion.partida.tiempo}) con "
            f"{guion.pendientes()} acciones sin reproducir; la primera es "
            f"'t={tiempo} {accion}'.")
    if grabadora.acciones != acciones:
        raise ErrorReplayDivergente("Las acciones reproducidas no coinciden con la bitácora.")

    if cierre_original is not None and cierre_original[:2] != grabadora.cierre[:2]:
        raise ErrorReplayDivergente("El tiempo o resultado del cierre no coincide con la bitácora.")
    resultado = ResultadoReplay(sesion, guion, grabadora, cierre_original)
    if resultado.verificado is False:
        linea, esperada, obtenida = resultado.diferencia
        raise ErrorReplayDivergente(
            f"El estado final no coincide en la línea {linea}:\n"
            f"  log:    {esperada}\n  replay: {obtenida}")
    return resultado
