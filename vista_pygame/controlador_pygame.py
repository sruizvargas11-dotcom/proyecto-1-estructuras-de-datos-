"""Puente entre ControladorJuego (sin modificar) y la vista Pygame.

Regla de hilos (aprobada, ver ANALISIS_ARQUITECTURA.md §7):
  - El modelo (ControladorJuego.jugar(), y por lo tanto Partida/Jugador/Reloj)
    corre entero en UN hilo de fondo, lanzado por iniciar_partida(). Nada fuera
    de ese hilo llama jamás a un método del modelo.
  - Esta clase actúa como 'vista' (protocolo duck-typed de VistaConsola) para
    ese ControladorJuego: sus métodos mostrar_*/agregar_mensaje se EJECUTAN en
    el hilo de fondo. Ninguno de ellos importa ni llama a pygame: solo arman
    datos planos (EstadoPartida, eventos) y los publican bajo un lock.
  - El hilo principal (pygame) solo llama a los métodos de "API para las
    escenas" más abajo: nunca toca partida/sesion directamente, solo lee las
    fotos ya publicadas.
  - leer_comando() bloquea el hilo de fondo en una cola; cada tecla de juego
    (incluidos guardar, cargar y el pergamino) empuja un comando ahí. Una
    acción del jugador = una llamada al controlador, igual que en consola.
  - Una excepción no capturada en el hilo de fondo no lo mata en silencio: se
    guarda su texto y la escena la muestra (ver error_pendiente()).
  - salir() encola 'Q' y hace join() del hilo: cierre ordenado, nunca un
    daemon cortado a la mitad.
"""
import queue
import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from controlador.controlador_juego import ControladorJuego
from controlador.estado_final import lineas_estado
from controlador.inicio_partida import nueva_partida, ruta_bitacora_por_defecto
from controlador.reporte_red import construir_reporte, motivo_error, motivo_partida
from controlador.semilla import generar_semilla
from estructuras.array_circular import ArrayCircular
from vista_pygame.contratos import ResumenPartida

CAPACIDAD_MENSAJES = 20


# ---------------------------------------------------------------------------
# Datos planos publicados hacia el hilo de pygame (nunca referencias vivas a
# ListaSimple/ListaDoble del modelo, que el hilo de fondo sigue mutando).
# ---------------------------------------------------------------------------

@dataclass
class SalidaVisual:
    direccion: str
    sala_destino_id: int
    nombre_destino: str
    cerrada: bool
    tiene_llave: bool


@dataclass
class ActorVisual:
    instancia_id: str
    tipo_id: str
    nombre: str
    vida: int
    vida_max: int
    comportamiento: str   # "" para el jugador
    envenenado: bool


@dataclass
class ObjetoVisual:
    instancia_id: str
    tipo_id: str
    nombre: str
    clase: str
    equipado: bool
    encendida: bool


@dataclass
class TrampaVisual:
    nombre: str
    armada: bool


@dataclass
class ProximoTurnoVisual:
    tiempo: int
    etiqueta: str


@dataclass
class SalaTopologia:
    """Topología estática de una sala (id, nombre y salidas): no cambia
    durante la partida, así que se lee una sola vez, en el hilo que llama a
    iniciar_partida, antes de arrancar el hilo de fondo (sección 7: ningún
    otro momento es seguro para leer el modelo fuera de ese hilo)."""
    sala_id: int
    nombre: str
    salidas: list   # [(direccion, sala_destino_id), ...]


@dataclass
class EstadoPartida:
    tiempo: int
    sala_id: int
    sala_nombre: str
    salidas: list
    enemigos_activos: list
    enemigos_dormidos: list
    objetos_suelo: list
    trampas: list
    jugador: ActorVisual
    ataque: int
    defensa: int
    velocidad: int
    arma_equipada: str
    armadura_equipada: str
    inventario: list
    efectos: list
    enemigos_derrotados: int
    acciones_jugador: int
    estado: str
    salas_visitadas: list
    cargando: bool = False
    proximos_turnos: list = field(default_factory=list)


def _efectos_jugador(jugador):
    efectos = []
    veneno = getattr(jugador, "estado_veneno", None)
    if veneno is not None:
        efectos.append(f"envenenado ({veneno.dano_por_pulso}x{veneno.pulsos_restantes})")
    for nodo in jugador.inventario.recorrer_desde_frente():
        objeto = nodo.valor
        if objeto.clase == "antorcha" and objeto.encendida:
            efectos.append(f"{objeto.nombre} encendida")
    return efectos


def construir_estado(partida, proximos_turnos=None, cargando=False):
    """Copia de solo lectura del estado relevante. Se llama en el hilo de
    fondo (dentro de mostrar_estado); no debe tocar pygame."""
    jugador = partida.jugador
    sala = jugador.sala_actual

    salidas = []
    for salida in sala.salidas:
        destino = salida.sala_destino if salida.sala_destino is not None \
            else partida.cripta.sala_por_id(salida.sala_destino_id)
        salidas.append(SalidaVisual(
            direccion=salida.direccion,
            sala_destino_id=salida.sala_destino_id,
            nombre_destino=destino.nombre if destino is not None else "",
            cerrada=salida.cerrada,
            tiene_llave=partida.llave_para(salida) is not None if salida.cerrada else False,
        ))

    def actor_visual(actor, comportamiento=""):
        return ActorVisual(
            instancia_id=actor.instancia_id,
            tipo_id=getattr(actor, "tipo_id", ""),
            nombre=partida.nombre_enemigo(actor) if comportamiento else "",
            vida=actor.vida, vida_max=actor.vida_max,
            comportamiento=comportamiento,
            envenenado=getattr(actor, "estado_veneno", None) is not None,
        )

    enemigos_activos = [actor_visual(e, e.comportamiento) for e in sala.enemigos_activos]
    enemigos_dormidos = [actor_visual(e, e.comportamiento) for e in sala.enemigos_dormidos]

    objetos_suelo = [ObjetoVisual(o.instancia_id, o.tipo_id, o.nombre, o.clase, False,
                                  getattr(o, "encendida", False)) for o in sala.objetos_suelo]

    trampas = [TrampaVisual(t.nombre, t.armada) for t in sala.trampas]

    inventario = []
    for nodo in jugador.inventario.recorrer_desde_frente():
        o = nodo.valor
        inventario.append(ObjetoVisual(
            o.instancia_id, o.tipo_id, o.nombre, o.clase,
            equipado=(o is jugador.arma_equipada or o is jugador.armadura_equipada),
            encendida=getattr(o, "encendida", False)))

    salas_visitadas = [s.id for s in partida.cripta.recorrer_salas() if s.tiempo_rastro >= 0]

    proximos = []
    if proximos_turnos:
        for entrada in proximos_turnos:
            dueno = entrada.dato.dueno
            if dueno is jugador:
                etiqueta = "Jugador"
            elif hasattr(dueno, "comportamiento"):
                etiqueta = partida.nombre_enemigo(dueno)
            else:
                etiqueta = entrada.dato.tipo
            proximos.append(ProximoTurnoVisual(entrada.tiempo, etiqueta))

    return EstadoPartida(
        tiempo=partida.tiempo, sala_id=sala.id, sala_nombre=sala.nombre,
        salidas=salidas, enemigos_activos=enemigos_activos,
        enemigos_dormidos=enemigos_dormidos, objetos_suelo=objetos_suelo,
        trampas=trampas,
        jugador=actor_visual(jugador),
        ataque=jugador.ataque, defensa=jugador.defensa, velocidad=jugador.velocidad,
        arma_equipada=jugador.arma_equipada.nombre if jugador.arma_equipada else "",
        armadura_equipada=jugador.armadura_equipada.nombre if jugador.armadura_equipada else "",
        inventario=inventario, efectos=_efectos_jugador(jugador),
        enemigos_derrotados=partida.enemigos_derrotados,
        acciones_jugador=partida.acciones_jugador,
        estado=partida.estado, salas_visitadas=salas_visitadas,
        cargando=cargando, proximos_turnos=proximos,
    )


# ---------------------------------------------------------------------------
# Eventos para ColaAnimaciones / GestorAudio: solo identificadores y números,
# nunca referencias vivas al modelo (se resuelven contra el EstadoPartida
# publicado más reciente, en el hilo de pygame).
# ---------------------------------------------------------------------------

@dataclass
class EventoMensaje:
    tipo: str = "mensaje"
    tiempo: int = 0
    texto: str = ""


@dataclass
class EventoMovimientoEnemigo:
    tipo: str = "movimiento"
    enemigo_id: str = ""
    sala_origen_id: int = 0
    sala_destino_id: int = 0


@dataclass
class EventoAtaque:
    tipo: str = "ataque"
    atacante_id: str = ""
    objetivo_id: str = ""
    dano: int = 0


class ControladorPygame:
    """Vista no interactiva para ControladorJuego + API de alto nivel para
    las escenas de menú, pausa, inventario y fin de partida."""

    def __init__(self, fuente, carpeta_cache=None, cache_size=25, partidas_dir="partidas"):
        self._fuente = fuente
        self._carpeta_cache = carpeta_cache
        self._cache_size = cache_size
        self._partidas_dir = partidas_dir

        self._lock = threading.Lock()
        self._comandos = queue.Queue()
        self._estado = None
        self._eventos_pendientes = []
        self._historial_mensajes = ArrayCircular(CAPACIDAD_MENSAJES)
        self._panel_inventario = None
        self._panel_objeto = None
        self._resumen_fin = None
        self._error = None
        self._esperando = False

        self._hilo = None
        self._controlador = None
        self.sesion = None
        self.nombre_jugador = None
        self._topologia = None
        self._sala_inicial_id = None
        self._sala_salida_id = None

    # -- arranque / cierre (API para las escenas, hilo principal) --------

    def listar_criptas(self):
        respuesta = self._fuente.listar_criptas()
        return list(respuesta["criptas"])

    def iniciar_partida(self, id_cripta, nombre_jugador, semilla=None):
        if self._hilo is not None:
            raise RuntimeError("Ya hay una partida en curso en este controlador.")
        self.nombre_jugador = nombre_jugador
        semilla_real = semilla if semilla is not None else generar_semilla()
        ruta_log = ruta_bitacora_por_defecto(
            id_cripta, semilla_real, str(Path(self._partidas_dir) / "bitacoras"))
        self.sesion = nueva_partida(
            self._fuente, id_cripta, self._carpeta_cache, semilla=semilla_real,
            ruta_bitacora=ruta_log, cache_size=self._cache_size,
            nombre_jugador=nombre_jugador)
        self.sesion.partida.al_mover_enemigo.agregarValor(self._on_mover_enemigo)
        self.sesion.partida.al_atacar.agregarValor(self._on_atacar)
        self._leer_topologia()
        self._controlador = ControladorJuego(
            self.sesion, self, str(Path(self._partidas_dir) / "partida.sav"))
        self._hilo = threading.Thread(target=self._correr, name="cripta-modelo", daemon=True)
        self._hilo.start()

    def _leer_topologia(self):
        """Única lectura directa del modelo fuera del hilo de fondo: ocurre
        antes de lanzarlo (self._hilo aún no existe), sobre una cripta que ya
        no cambia de estructura (solo cambian puertas/rastro/contenido, no
        qué sala conecta con cuál). Se guarda como datos planos."""
        cripta = self.sesion.partida.cripta
        topologia = []
        for sala in cripta.recorrer_salas():
            salidas = [(s.direccion, s.sala_destino_id) for s in sala.salidas]
            topologia.append(SalaTopologia(sala.id, sala.nombre, salidas))
        self._topologia = topologia
        self._sala_inicial_id = cripta.sala_inicial_id
        self._sala_salida_id = cripta.sala_salida_id

    def topologia_cripta(self):
        """Lista de SalaTopologia; no cambia durante la partida."""
        return self._topologia

    def sala_inicial_id(self):
        return self._sala_inicial_id

    def sala_salida_id(self):
        return self._sala_salida_id

    def _correr(self):
        try:
            self._controlador.jugar()
        except Exception:
            with self._lock:
                self._error = traceback.format_exc()

    def salir(self):
        """Cierre ordenado: pide salir y espera a que el hilo termine de
        verdad (cierra bitácora y red) antes de volver. Nunca lo abandona a
        medias confiando en que sea un hilo daemon."""
        if self._hilo is None:
            return
        self._comandos.put("Q")
        self._hilo.join(timeout=15)
        self._hilo = None

    # -- guardar / cargar / pergamino: por la cola, como cualquier acción --

    def guardar(self, ruta=None):
        self._comandos.put(f"G {ruta}" if ruta else "G")

    def cargar(self, ruta=None):
        self._comandos.put(f"L {ruta}" if ruta else "L")

    def pergamino(self):
        self._comandos.put("P")

    def enviar_comando(self, texto):
        """Para la escena de partida: cualquier otro comando de juego."""
        self._esperando = True
        self._comandos.put(texto)

    # -- lecturas de solo lectura (API para las escenas, hilo principal) --

    def estado(self):
        with self._lock:
            return self._estado

    def esperando_red(self):
        """True entre el envío de un comando y la próxima foto publicada:
        para mostrar 'cargando...' sin congelar pygame (sección 6/7)."""
        return self._esperando

    def eventos_nuevos(self):
        """Vacía y devuelve el buffer de eventos desde la última lectura, en
        el orden del modelo. Se llama una vez por frame desde el hilo de
        pygame; el hilo de fondo solo agrega, nunca lee esta lista."""
        with self._lock:
            pendientes, self._eventos_pendientes = self._eventos_pendientes, []
        return pendientes

    def mensajes(self):
        with self._lock:
            return self._historial_mensajes.listar_en_orden()

    def panel_inventario(self):
        with self._lock:
            return self._panel_inventario

    def error_pendiente(self):
        with self._lock:
            return self._error

    def resumen_fin(self):
        return self._resumen_fin

    def tabla_puntajes(self):
        """Sin tabla persistente en esta migración (ver ANALISIS_ARQUITECTURA.md §8.1)."""
        return []

    def reporte_red(self):
        if self.sesion is None:
            return []
        lineas = construir_reporte(self._fuente, self.sesion, "partida",
                                   motivo_partida(self.sesion.partida.estado))
        return list(lineas)

    # -- protocolo de VistaConsola: se ejecuta en el HILO DE FONDO --------
    # Ninguno de estos métodos puede importar ni llamar a pygame.

    def mostrar_estado(self, partida):
        proximos = partida.reloj.proximos_eventos(5)
        foto = construir_estado(partida, proximos_turnos=proximos)
        with self._lock:
            self._estado = foto
            self._esperando = False

    def agregar_mensaje(self, tiempo, texto):
        with self._lock:
            self._historial_mensajes.agregarValor(f"[t={tiempo}] {texto}")
            self._eventos_pendientes.append(EventoMensaje(tiempo=tiempo, texto=texto))

    def restaurar_mensajes(self, mensajes):
        with self._lock:
            self._historial_mensajes = ArrayCircular(CAPACIDAD_MENSAJES)
            for mensaje in mensajes:
                self._historial_mensajes.agregarValor(mensaje)

    def mostrar_inventario(self, partida, objetos, criterio):
        panel = [ObjetoVisual(o.instancia_id, o.tipo_id, o.nombre, o.clase,
                              o is partida.jugador.arma_equipada
                              or o is partida.jugador.armadura_equipada,
                              getattr(o, "encendida", False)) for o in objetos]
        with self._lock:
            self._panel_inventario = (criterio, panel)

    def mostrar_ayuda(self):
        """La ayuda de la GUI es un overlay local (F1) que no pasa por el
        controlador; este método solo existe por el protocolo de VistaConsola
        y no debería recibir llamadas reales desde la GUI."""

    def mostrar_objeto(self, nodo):
        with self._lock:
            self._panel_objeto = None if nodo is None else nodo.valor.instancia_id

    def mostrar_fin(self, partida):
        red = self.sesion.red
        cache = dict(red.estadisticas_cache())
        self._resumen_fin = ResumenPartida(
            resultado=partida.estado,
            nombre_jugador=self.nombre_jugador or "Jugador",
            id_cripta=partida.cripta_id,
            version_cripta=partida.version_cripta,
            acciones_jugador=partida.acciones_jugador,
            enemigos_derrotados=partida.enemigos_derrotados,
            tiempo_final=partida.tiempo,
            solicitudes_realizadas=getattr(self._fuente, "requests_realizados", 0) or 0,
            presupuesto_solicitudes=partida.cripta.presupuesto_solicitudes,
            aciertos_cache=cache.get("aciertos", 0),
            fallos_cache=cache.get("fallos", 0),
        )

    def leer_comando(self):
        """Bloquea el HILO DE FONDO (no el de pygame) hasta que una escena
        encole un comando con enviar_comando/guardar/cargar/pergamino."""
        return self._comandos.get()

    # -- hooks de Partida (§8.4): hilo de fondo, solo acumulan ------------

    def _on_mover_enemigo(self, enemigo, sala_origen, sala_destino):
        with self._lock:
            self._eventos_pendientes.append(EventoMovimientoEnemigo(
                enemigo_id=enemigo.instancia_id,
                sala_origen_id=sala_origen.id, sala_destino_id=sala_destino.id))

    def _on_atacar(self, atacante, objetivo, dano):
        with self._lock:
            self._eventos_pendientes.append(EventoAtaque(
                atacante_id=atacante.instancia_id, objetivo_id=objetivo.instancia_id,
                dano=dano))
