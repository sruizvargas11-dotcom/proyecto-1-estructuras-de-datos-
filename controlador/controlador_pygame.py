"""Puente entre ControladorJuego (sin modificar) y la vista Pygame.

Regla de hilos (ver también AppPygame.ejecutar):
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
import uuid
from dataclasses import dataclass, replace, field
from pathlib import Path

from controlador.controlador_juego import ControladorJuego
from controlador.estado_final import lineas_estado
from controlador.inicio_partida import nueva_partida, ruta_bitacora_por_defecto
from controlador.reporte_red import construir_reporte, motivo_error, motivo_partida, registrar_reporte
from controlador.semilla import generar_semilla
from estructuras.array_circular import ArrayCircular
from persistencia.puntajes import ErrorTablaPuntajes, TablaPuntajes
from vista_pygame.contratos import FilaPuntaje, ResumenPartida

@dataclass(frozen=True)
class PartidaGuardadaVisual:
    ruta: str
    archivo: str
    nombre_jugador: str
    cripta_id: str
    modificada: float
    error: str | None = None


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
    llave_tipo_id: str | None = None


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
    peso: int = 0
    valor: int = 0
    agotada: bool = False
    ataque_bonus: int = 0
    defensa_bonus: int = 0
    duracion: int = 0
    tiempo_restante: int | None = None


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
    es_sala_salida: bool = False
    cripta_id: str = ""
    cripta_nombre: str = ""


def _efectos_jugador(jugador, tiempo=0):
    efectos = []
    veneno = getattr(jugador, "estado_veneno", None)
    if veneno is not None:
        efectos.append(f"envenenado ({veneno.dano_por_pulso}x{veneno.pulsos_restantes})")
    velocidad = getattr(jugador, "evento_mod_velocidad", None)
    if velocidad is not None and velocidad.valido and velocidad._en_heap:
        restante = max(0, velocidad.tiempo-tiempo)
        efectos.append(f"velocidad temporal: {jugador.velocidad} ({restante} ut)")
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
            llave_tipo_id=salida.llave,
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

    def objeto_visual(o, equipado=False):
        duracion=getattr(o,'duracion',0) if o.clase=='antorcha' else 0
        restante=None
        agotada=False
        if o.clase=='antorcha':
            evento=o.evento_apagado
            pendiente=evento is not None and evento.valido and evento._en_heap
            agotada=getattr(o,'usos_restantes',1)<=0 and not pendiente
            restante=(max(0,min(duracion,evento.tiempo-partida.tiempo)) if pendiente else
                      duracion if getattr(o,'usos_restantes',1)>0 else 0)
        return ObjetoVisual(o.instancia_id,o.tipo_id,o.nombre,o.clase,equipado,
                            getattr(o,'encendida',False),peso=o.peso,valor=o.valor,agotada=agotada,
                            ataque_bonus=getattr(o,'ataque_bonus',0),
                            defensa_bonus=getattr(o,'defensa_bonus',0),
                            duracion=duracion,tiempo_restante=restante)

    objetos_suelo=[objeto_visual(o) for o in sala.objetos_suelo]
    trampas = [TrampaVisual(t.nombre, t.armada) for t in sala.trampas]
    inventario=[objeto_visual(nodo.valor,nodo.valor is jugador.arma_equipada
                             or nodo.valor is jugador.armadura_equipada)
                for nodo in jugador.inventario.recorrer_desde_frente()]

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
        inventario=inventario, efectos=_efectos_jugador(jugador, partida.tiempo),
        enemigos_derrotados=partida.enemigos_derrotados,
        acciones_jugador=partida.acciones_jugador,
        estado=partida.estado, salas_visitadas=salas_visitadas,
        cargando=cargando, proximos_turnos=proximos,
        es_sala_salida=sala.id==partida.cripta.sala_salida_id,
        cripta_id=partida.cripta_id,
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
    vida_antes: int | None = None
    vida_despues: int | None = None
    tiempo: int | None = None


@dataclass
class EventoTrampa:
    tipo: str = 'trampa'
    objetivo_id: str = ''
    dano: int = 0
    vida_antes: int | None = None
    vida_despues: int | None = None
    tiempo: int | None = None
    nombre: str = ''
    tipos: tuple = ()


class ControladorPygame:
    """Vista no interactiva para ControladorJuego + API de alto nivel para
    las escenas de menú, pausa, inventario y fin de partida."""

    def __init__(self, fuente, carpeta_cache=None, cache_size=25, partidas_dir="partidas", reportes=None):
        self._fuente = fuente
        self._fuente_usada = False
        self._carpeta_cache = carpeta_cache
        self._cache_size = cache_size
        self._partidas_dir = partidas_dir
        self._ruta_reportes = reportes

        self._lock = threading.Lock()
        self._comandos = queue.Queue()
        self._estado = None
        self._eventos_pendientes = []
        self._historial_mensajes = ArrayCircular(CAPACIDAD_MENSAJES)
        self._panel_inventario = None
        self._panel_objeto = None
        self._resumen_fin = None
        self._reporte_red = []
        # La tabla real solo la toca el hilo de modelo (ControladorJuego la
        # actualiza en _cerrar). Hacia pygame se publica una copia en filas.
        self._tabla = TablaPuntajes(str(Path(partidas_dir) / "puntajes.json"))
        self._filas_puntajes = None
        self._error = None
        self._esperando = False

        self._hilo = None
        self._controlador = None
        self.sesion = None
        self._revision_sesion = 0
        self.nombre_jugador = None
        self._topologia = None
        self._sala_inicial_id = None
        self._sala_salida_id = None
        self._criptas_disponibles = ()

    # -- arranque / cierre (API para las escenas, hilo principal) --------

    def _preparar_fuente_nueva_partida(self):
        fabrica=getattr(self._fuente,'para_nueva_partida',None)
        if self._fuente_usada and self._hilo is None and callable(fabrica):
            self._fuente=fabrica()
            self._fuente_usada=False

    def listar_criptas(self):
        self._preparar_fuente_nueva_partida()
        respuesta = self._fuente.listar_criptas()
        if not isinstance(respuesta, dict) or not isinstance(respuesta.get('criptas'), list):
            raise ValueError('GET /criptas: respuesta inválida; se esperaba una lista de criptas.')
        for indice, cripta in enumerate(respuesta['criptas'], 1):
            if (not isinstance(cripta, dict)
                    or any(not isinstance(cripta.get(campo), str) or not cripta[campo].strip()
                           for campo in ('id', 'nombre'))
                    or type(cripta.get('salas')) is not int or cripta['salas'] < 1
                    or type(cripta.get('dificultad')) is not int or cripta['dificultad'] < 0):
                raise ValueError(f'GET /criptas: cripta #{indice} con campos inválidos o ausentes.')
        criptas=list(respuesta['criptas'])
        with self._lock:self._criptas_disponibles=tuple(criptas)
        return criptas

    def nombre_cripta(self,id_cripta):
        with self._lock:
            return next((c['nombre'] for c in self._criptas_disponibles if c['id']==id_cripta),id_cripta)

    def listar_partidas_guardadas(self):
        """Lee metadatos en el hilo del menú; nunca reconstruye el modelo."""
        from persistencia.PartidaBinaria import PartidaBinaria, ErrorFormatoBinario
        from controlador.guardado import ESQUEMA_ESTADO
        from estructuras.vector_dinamico import Vector
        from estructuras.ordenamientos import ordenar
        filas=Vector()
        for ruta in Path(self._partidas_dir).glob('*.sav'):
            try:
                modificada=ruta.stat().st_mtime
                datos=PartidaBinaria(str(ruta)).cargar_global()
                if datos.get('esquema_estado')!=ESQUEMA_ESTADO:
                    raise ValueError('Versión de guardado incompatible.')
                nombre=datos.get('nombre_jugador')
                cripta=datos.get('cripta_id')
                if not isinstance(nombre,str) or not nombre.strip() or not isinstance(cripta,str) or not cripta:
                    raise ValueError('Faltan datos del jugador o de la cripta.')
                filas.agregarValor(PartidaGuardadaVisual(str(ruta.resolve()),ruta.name,nombre,cripta,modificada))
            except (OSError,ValueError,TypeError,AttributeError,ErrorFormatoBinario) as error:
                filas.agregarValor(PartidaGuardadaVisual(str(ruta.resolve()),ruta.name,'','',0,
                                                         f'No disponible: {error}'))
        def comparar(a,b):
            ka,kb=(-a.modificada,a.archivo),(-b.modificada,b.archivo)
            return (ka>kb)-(ka<kb)
        ordenar(filas,comparar)
        return list(filas)

    def cargar_partida_guardada(self,ruta):
        """Arranque desde disco, antes de iniciar el único hilo del modelo."""
        from persistencia.PartidaBinaria import PartidaBinaria, ErrorFormatoBinario
        from controlador.guardado import ESQUEMA_ESTADO
        try:
            datos=PartidaBinaria(str(ruta)).cargar_global()
        except (OSError,ValueError,ErrorFormatoBinario) as error:
            raise ValueError(f'No se pudo leer el guardado: {error}') from error
        if not isinstance(datos,dict) or datos.get('esquema_estado')!=ESQUEMA_ESTADO:
            raise ValueError('Versión de guardado incompatible.')
        if not isinstance(datos.get('cripta_id'),str):raise ValueError('Falta la cripta del guardado.')
        from controlador.semilla import validar_semilla
        semilla=validar_semilla(datos.get('semilla'))
        self.iniciar_partida(datos['cripta_id'],datos.get('nombre_jugador'),semilla,
                            ruta_carga=str(ruta))

    def iniciar_partida(self, id_cripta, nombre_jugador, semilla=None, *, ruta_carga=None):
        if not isinstance(nombre_jugador,str) or not nombre_jugador.strip():
            raise ValueError('El nombre del jugador es obligatorio.')
        nombre_jugador=nombre_jugador.strip()
        if self._hilo is not None:
            raise RuntimeError("Ya hay una partida en curso en este controlador.")
        self._preparar_fuente_nueva_partida()
        self._fuente_usada=True
        # La sesión anterior ya terminó: no reutilizar Q pendientes,
        # fotos de derrota, mensajes ni resumen al volver desde la portada.
        self._comandos = queue.Queue()
        with self._lock:
            self._estado = None
            self._resumen_fin = None
            self._error = None
            self._esperando = False
            self._eventos_pendientes = []
            self._historial_mensajes = ArrayCircular(CAPACIDAD_MENSAJES)
            self._panel_inventario = None
            self._panel_objeto = None
            self._reporte_red = []
            self._filas_puntajes = None
        self.nombre_jugador = nombre_jugador
        semilla_real = semilla if semilla is not None else generar_semilla()
        ruta_log = ruta_bitacora_por_defecto(
            id_cripta, semilla_real, str(Path(self._partidas_dir) / "bitacoras"))
        if ruta_carga is not None:
            ruta_log=str(Path(ruta_log).with_name('carga_'+uuid.uuid4().hex+'.log'))
        self.sesion = nueva_partida(
            self._fuente, id_cripta, self._carpeta_cache, semilla=semilla_real,
            ruta_bitacora=ruta_log, cache_size=self._cache_size,
            nombre_jugador=nombre_jugador)
        if ruta_carga is not None:
            from controlador.guardado import cargar
            base=self.sesion
            try:
                restaurada=cargar(ruta_carga,base)
                restaurada.bitacora=base.bitacora
                for tiempo,accion in restaurada.acciones:
                    restaurada.bitacora.registrar(tiempo,accion)
            except Exception:
                if base.bitacora is not None:base.bitacora.cerrar()
                base.red.cerrar(5)
                self.sesion=None
                raise
            base.red.cerrar(5)
            self.sesion=restaurada
            self.nombre_jugador=restaurada.nombre_jugador
            self.restaurar_mensajes(restaurada.mensajes_guardados or [])
            self.agregar_mensaje(restaurada.partida.tiempo,f'Partida cargada: {Path(ruta_carga).name}')
        self.sesion.partida.al_mover_enemigo.agregarValor(self._on_mover_enemigo)
        self.sesion.partida.al_atacar.agregarValor(self._on_atacar)
        self.sesion.partida.al_activar_trampa.agregarValor(self._on_trampa)
        self._leer_topologia()
        ruta_guardado=(ruta_carga if ruta_carga is not None else
                       str(Path(self._partidas_dir)/('partida_'+uuid.uuid4().hex[:12]+'.sav')))
        self._controlador = ControladorJuego(
            self.sesion, self, ruta_guardado, tabla_puntajes=self._tabla)
        if ruta_carga is not None and self.sesion.protegidas is not None:
            self._controlador._protegidas=self.sesion.protegidas
        self._hilo = threading.Thread(target=self._correr, name="cripta-modelo", daemon=False)
        self._hilo.start()

    def _leer_topologia(self):
        """Copia la topología al iniciar y tras cargar otra sesión.
        Al iniciar aún no corre el hilo de modelo; al cargar se ejecuta
        dentro de ese hilo. La vista recibe datos planos."""
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
        error_partida = None
        try:
            self._controlador.jugar()
        except Exception as error:
            error_partida = error
            with self._lock:
                self._error = traceback.format_exc()
                self._esperando = False
        finally:
            # Una vez por partida, en el mismo hilo que cerró la red y la bitácora.
            # También cubre victoria/derrota antes de salir de la ventana.
            sesion = self._controlador.sesion
            motivo = motivo_error(error_partida) if error_partida is not None else motivo_partida(sesion.partida.estado)
            texto = registrar_reporte(self._fuente, sesion, 'partida', motivo,
                                     ruta=self._ruta_reportes,
                                     bitacora=getattr(sesion.bitacora, 'ruta', None))
            with self._lock:
                self._reporte_red = texto.splitlines()

    def cancelar_red(self):
        """El cierre de la vista cancela esperas HTTP sin tocar el reloj virtual."""
        cancelar = getattr(self._fuente, 'cancelar_pendientes', None)
        if callable(cancelar):
            cancelar()

    def salir(self):
        """Cierre ordenado: pide salir y espera a que el hilo termine de
        verdad (cierra bitácora y red) antes de volver. Nunca lo abandona a
        medias confiando en que sea un hilo daemon."""
        self.cancelar_red()
        if self._hilo is None:
            return
        self._comandos.put("Q")
        self._hilo.join(timeout=15)
        if self._hilo.is_alive():
            raise RuntimeError('El modelo sigue cerrando una operación de red; espera antes de reiniciar.')
        self._hilo = None

    # -- guardar / cargar / pergamino: por la cola, como cualquier acción --

    def guardar(self, ruta=None):
        self.enviar_comando(f"G {ruta}" if ruta else "G")

    def cargar(self, ruta=None):
        self.enviar_comando(f"L {ruta}" if ruta else "L")

    def pergamino(self):
        self.enviar_comando("P")

    def enviar_comando(self, texto):
        """Para la escena de partida: cualquier otro comando de juego."""
        self._esperando = True
        self._comandos.put(texto)

    # -- lecturas de solo lectura (API para las escenas, hilo principal) --

    def estado(self):
        with self._lock:
            return self._estado

    def revision_sesion(self):
        """Permite descartar referencias visuales tras una carga, incluso en la misma sala."""
        with self._lock:
            return self._revision_sesion

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
        with self._lock:
            return self._resumen_fin

    def tabla_puntajes(self):
        """Lista de FilaPuntaje, de la mejor a la peor.

        Después de una partida terminada en victoria o derrota trae la tabla ya
        actualizada, con esa partida marcada (es_actual); se publica antes que
        resumen_fin(), así que cuando la escena ve el resumen la tabla ya está.
        Antes de la primera partida se lee una vez del archivo. Si el archivo no
        existe o está dañado, devuelve una lista vacía.
        """
        with self._lock:
            filas = self._filas_puntajes
        if filas is None:
            # El archivo se reemplaza de forma atómica al guardar, así que leerlo
            # desde este hilo es seguro aunque el de modelo esté escribiendo.
            try:
                leidas = self._filas_desde(TablaPuntajes(self._tabla.ruta).cargar(), None)
            except (OSError, ErrorTablaPuntajes):
                leidas = []
            with self._lock:
                if self._filas_puntajes is None:
                    self._filas_puntajes = leidas
                filas = self._filas_puntajes
        return [replace(fila) for fila in filas]

    @staticmethod
    def _filas_desde(tabla, actual):
        filas = []
        for posicion, registro in enumerate(tabla, 1):
            filas.append(FilaPuntaje(
                posicion=posicion, nombre_jugador=registro.nombre_jugador,
                id_cripta=registro.cripta_id, version_cripta=registro.version_cripta,
                acciones_jugador=registro.acciones_jugador,
                enemigos_derrotados=registro.enemigos_derrotados,
                tiempo_final=registro.tiempo_final, resultado=registro.resultado,
                es_actual=registro is actual))
        return filas

    def reporte_red(self):
        # La interfaz solo lee una copia publicada por el hilo del modelo.
        with self._lock:
            return list(self._reporte_red)

    def _sincronizar_sesion(self):
        """Tras L, renovar referencias y hooks en el hilo del modelo."""
        actual = self._controlador.sesion
        if self.sesion is not actual:
            self.sesion = actual
            self.nombre_jugador = actual.nombre_jugador
            actual.partida.al_mover_enemigo.agregarValor(self._on_mover_enemigo)
            actual.partida.al_atacar.agregarValor(self._on_atacar)
            actual.partida.al_activar_trampa.agregarValor(self._on_trampa)
            self._leer_topologia()
            with self._lock:
                self._eventos_pendientes.clear()
                self._revision_sesion += 1
        lineas = construir_reporte(self._fuente, actual, 'partida',
                                   motivo_partida(actual.partida.estado))
        with self._lock:
            self._reporte_red = list(lineas)

    # -- protocolo de VistaConsola: se ejecuta en el HILO DE FONDO --------
    # Ninguno de estos métodos puede importar ni llamar a pygame.

    def mostrar_estado(self, partida):
        self._sincronizar_sesion()
        proximos = partida.reloj.proximos_eventos(5)
        foto = construir_estado(partida, proximos_turnos=proximos)
        foto = replace(foto,cripta_nombre=self.nombre_cripta(partida.cripta_id))
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
        self._sincronizar_sesion()
        # Hilo de modelo, justo después de que ControladorJuego registró el
        # puntaje: se copia la tabla antes de publicar el resumen.
        registro = getattr(self._controlador, "registro_puntaje", None)
        if registro is not None:
            filas = self._filas_desde(self._tabla, registro)
            with self._lock:
                self._filas_puntajes = filas
        red = self.sesion.red
        cache = dict(red.estadisticas_cache())
        resumen = ResumenPartida(
            resultado=partida.estado,
            nombre_jugador=self._controlador.sesion.nombre_jugador,
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

        # El último golpe puede terminar la partida entre dos turnos del
        # jugador. Publicar también esa foto; no habrá otro mostrar_estado.
        foto = construir_estado(partida, proximos_turnos=[])
        with self._lock:
            self._estado = foto
            self._esperando = False
            self._resumen_fin = resumen

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
                dano=dano,vida_antes=objetivo.vida+dano,vida_despues=objetivo.vida,
                tiempo=self.sesion.partida.tiempo))

    def _on_trampa(self,actor,dano,nombres):
        with self._lock:
            self._eventos_pendientes.append(EventoTrampa(
                objetivo_id=actor.instancia_id,dano=dano,vida_antes=actor.vida+dano,
                vida_despues=actor.vida,tiempo=self.sesion.partida.tiempo,nombre=nombres,
                tipos=tuple(t.tipo_id for t in actor.sala_actual.trampas
                            if not t.armada and t.nombre in nombres)))
