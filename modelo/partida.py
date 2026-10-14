"""Estado completo de una partida (plan v4, B3: partida.py).

Reúne en un solo objeto lo que el resto del juego comparte: cripta, jugador, reloj,
historial, rastro, entorno, fábrica de objetos, semilla y versiones. Además contiene
las reglas del modelo que no son acciones del jugador:

- inicializar(): rastro en t=0, primera acción del jugador en t=0 y activación de los
  enemigos de la sala inicial (§2.4).
- entrar_a_sala(): lo que ocurre al completar un movimiento (rastro, trampas,
  activación de dormidos en orden ascendente de instancia_id).
- turno de cada enemigo: decidir_accion + ejecutar + reprogramar con costo 100.
- daño y muerte de enemigos (botín de 'suelta', contador de derrotados).
- victoria / derrota.

MVC: este módulo NO conoce HTTP, disco ni la vista. Lo que necesita de afuera llega
por parámetros:
- resolver_ficha(tipo_id) -> dict | None: para crear el botín de 'suelta'. El
  controlador lo implementa con ControladorRed (memoria -> disco -> red).
- al_morir_enemigo / al_entrar_sala / al_mensaje: Vectores de funciones que la
  partida invoca. El controlador conecta ahí notificar_muerte_enemigo, el en_uso de
  fichas de la sala actual y la bitácora de pantalla.

La construcción con red (esqueleto, primer lote, catálogo, semilla, bitácora) está
en controlador/inicio_partida.py.
"""
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar
from modelo.deltas import DeltaAtributos, DeltaListaSimple
from modelo.entorno import Entorno
from modelo.historial import Historial
from modelo.rastro import Rastro
from modelo.reloj import Reloj

COSTO_ACCION_ENEMIGO = 100

EN_CURSO = "en_curso"
VICTORIA = "victoria"
DERROTA = "derrota"
CREADA = "creada"


def _clave_natural(texto):
    """'e-9' < 'e-10': compara los tramos numéricos como números.

    Los ids de instancia del API son texto ('e-201'). Con comparación de texto pura
    'e-1000' quedaría antes que 'e-201'. Se usa orden natural, que coincide con el
    texto cuando los números tienen la misma cantidad de dígitos.
    """
    texto = str(texto)
    partes = []
    actual = ""
    es_numero = None
    for caracter in texto:
        digito = caracter.isdigit()
        if es_numero is None or digito == es_numero:
            actual += caracter
        else:
            partes.append((0, int(actual)) if es_numero else (1, actual))
            actual = caracter
        es_numero = digito
    if actual:
        partes.append((0, int(actual)) if es_numero else (1, actual))
    return tuple(partes)


def comparar_instancias(a, b):
    """Comparador para ordenamientos.ordenar: orden ascendente de instancia_id."""
    ka, kb = _clave_natural(a.instancia_id), _clave_natural(b.instancia_id)
    return (ka > kb) - (ka < kb)


def _decision_jugador(reloj):
    """Marcador del turno del jugador.

    Nunca se ejecuta: Reloj.avanzar_hasta_turno se detiene en él y el controlador lo
    retira con Reloj.tomar_turno. Existe porque el heap guarda eventos ejecutables.
    """
    return None


class Partida:
    def __init__(self, cripta, jugador, semilla, version_catalogo=None,
                 fabrica=None, resolver_ficha=None):
        if jugador.sala_actual is None:
            raise ValueError("El jugador debe empezar en una sala.")
        self.cripta = cripta
        self.cripta_id = cripta.id
        self.version_cripta = cripta.version
        self.version_catalogo = version_catalogo
        self.jugador = jugador
        self.fabrica = fabrica
        self._resolver_ficha = resolver_ficha

        # Un solo historial compartido por Reloj y Rastro; un solo PRNG (en Reloj).
        self.historial = Historial()
        self.reloj = Reloj(semilla, self.historial)   # valida que sea entero >= 0
        self.semilla = semilla
        self.rastro = Rastro(cripta, self.historial)
        self.entorno = Entorno(self.reloj)

        self.estado = CREADA
        self.acciones_jugador = 0
        self.enemigos_derrotados = 0

        # Observadores (Vector de funciones). Ver docstring del módulo.
        self.al_morir_enemigo = Vector()   # f(enemigo)
        self.al_entrar_sala = Vector()     # f(sala_anterior, sala_nueva)
        self.al_mensaje = Vector()         # f(tiempo, texto)

        self.reloj.vincular_actor(jugador)

    # ------------------------------------------------------------------ consulta

    @property
    def tiempo(self):
        return self.reloj.tiempo_actual

    @property
    def terminada(self):
        return self.estado in (VICTORIA, DERROTA)

    @property
    def sala_actual(self):
        return self.jugador.sala_actual

    def encabezado(self):
        """Datos para la bitácora y el guardado binario."""
        return (("cripta_id", self.cripta_id),
                ("version_cripta", self.version_cripta),
                ("version_catalogo", self.version_catalogo),
                ("semilla", self.semilla))

    def resumen_puntaje(self):
        """Campos de §2.12 (el nombre del jugador lo pide la vista)."""
        return (("cripta_id", self.cripta_id),
                ("version_cripta", self.version_cripta),
                ("acciones_jugador", self.acciones_jugador),
                ("enemigos_derrotados", self.enemigos_derrotados),
                ("tiempo_final", self.reloj.tiempo_actual),
                ("resultado", self.estado))

    # ------------------------------------------------------------------ inicio

    def inicializar(self):
        """t=0: rastro, primera acción del jugador y enemigos de la sala inicial.

        Precondición (la garantiza el controlador): el contenido de la sala inicial
        ya está incorporado. No se registra en el historial: no hay acción previa a
        la que retroceder.
        """
        if self.estado != CREADA:
            raise RuntimeError("La partida ya fue inicializada.")
        if self.reloj.tiempo_actual != 0:
            raise RuntimeError("La partida debe iniciar con el reloj en 0.")
        sala = self.jugador.sala_actual
        self.rastro.registrar(sala.id, 0)
        self.reloj.programar_inicial(self.jugador, _decision_jugador)
        self.estado = EN_CURSO
        self.activar_enemigos(sala)
        self._emitir(f"Entras a {sala.nombre}.")
        self._notificar_entrada(None, sala)
        return self

    def programar_siguiente_jugador(self, costo):
        """El controlador lo llama tras aplicar una acción del jugador."""
        return self.reloj.programar(self.jugador, costo, _decision_jugador)

    def contar_accion_jugador(self):
        """Una acción que consumió tiempo (§2.12). Reversible con el pergamino."""
        self.historial.registrar(DeltaAtributos(self, "acciones_jugador"))
        self.acciones_jugador += 1

    def refrescar_rastro(self):
        """Apéndice B: el rastro de la sala actual se refresca en cada acción."""
        self.rastro.registrar(self.jugador.sala_actual.id, self.reloj.tiempo_actual)

    # ------------------------------------------------------------------ salas

    def activar_enemigos(self, sala):
        """Pasa los dormidos a activos en orden ascendente de instancia_id (§2.4).

        Cada uno queda programado a ahora + intervalo(100, velocidad), con números de
        secuencia en ese mismo orden. Devuelve cuántos activó.
        """
        if len(sala.enemigos_dormidos) == 0:
            return 0
        orden = Vector()
        for enemigo in sala.enemigos_dormidos:
            orden.agregarValor(enemigo)
        ordenar(orden, comparar_instancias)
        activados = 0
        for enemigo in orden:
            for lista in (sala.enemigos_dormidos, sala.enemigos_activos):
                self.historial.registrar(DeltaListaSimple(lista, enemigo))
            sala.enemigos_dormidos.eliminar_valor(enemigo)
            if not enemigo.vivo:
                continue
            sala.enemigos_activos.insertar_al_final(enemigo)
            self.historial.registrar(DeltaAtributos(enemigo, "sala_actual"))
            enemigo.sala_actual = sala
            self.reloj.programar(enemigo, COSTO_ACCION_ENEMIGO,
                                 self.ejecutor_enemigo(enemigo))
            activados += 1
        return activados

    def entrar_a_sala(self, sala):
        """Efectos de completar un movimiento del jugador hacia 'sala'.

        Precondiciones (las valida el controlador ANTES de abrir el intervalo):
        salida existente y abierta, y contenido de la sala ya incorporado.
        Debe llamarse dentro del intervalo del historial (después de tomar_turno),
        para que el pergamino pueda revertir el movimiento.
        """
        anterior = self.jugador.sala_actual
        self.historial.registrar(DeltaAtributos(self.jugador, "sala_actual"))
        self.jugador.sala_actual = sala
        self.refrescar_rastro()
        self._emitir(f"Entras a {sala.nombre}.")
        # §2.10: la trampa se activa justo después del movimiento.
        self.entorno.al_entrar(self.jugador, sala)
        if self.jugador.vivo:
            self.activar_enemigos(sala)
        self._notificar_entrada(anterior, sala)
        self.verificar_fin()
        return sala

    # ------------------------------------------------------------------ enemigos

    def ejecutor_enemigo(self, enemigo):
        """Callback del heap para la acción de 'enemigo'.

        Al cargar una partida guardada se reconstruye con este mismo método a partir
        del dueño del evento (no se serializan funciones).
        """
        def ejecutar(reloj):
            self.turno_enemigo(enemigo)
        return ejecutar

    def turno_enemigo(self, enemigo):
        """Decide y ejecuta una acción del enemigo; luego la reprograma (costo 100)."""
        if not enemigo.vivo or self.terminada:
            return None
        accion, objetivo = enemigo.decidir_accion(
            self.jugador, self.reloj.tiempo_actual, self.reloj.azar)
        if accion == "atacar":
            dano = self.reloj.calcular_dano(enemigo.ataque, self.jugador.defensa)
            perdida = self.jugador.recibir_dano(dano)
            self._emitir(f"{self.nombre_enemigo(enemigo)} te ataca: -{perdida} de vida.")
        elif accion == "mover":
            self._mover_enemigo(enemigo, objetivo)
        if enemigo.vivo and not self.terminada:
            self.verificar_fin()
            if not self.terminada:
                self.reloj.programar(enemigo, COSTO_ACCION_ENEMIGO,
                                     self.ejecutor_enemigo(enemigo))
        return accion

    def _mover_enemigo(self, enemigo, destino):
        origen = enemigo.sala_actual
        for lista in (origen.enemigos_activos, destino.enemigos_activos):
            self.historial.registrar(DeltaListaSimple(lista, enemigo))
        origen.enemigos_activos.eliminar_valor(enemigo)
        destino.enemigos_activos.insertar_al_final(enemigo)
        self.historial.registrar(DeltaAtributos(enemigo, "sala_actual"))
        enemigo.sala_actual = destino
        if destino is self.jugador.sala_actual:
            self._emitir(f"{self.nombre_enemigo(enemigo)} entra en la sala.")
        elif origen is self.jugador.sala_actual:
            self._emitir(f"{self.nombre_enemigo(enemigo)} sale de la sala.")

    def danar_enemigo(self, enemigo, cantidad):
        """Aplica daño ya calculado. Si muere, procesa la muerte. Devuelve la pérdida."""
        perdida = enemigo.recibir_dano(cantidad)
        if not enemigo.vivo:
            self.registrar_muerte_enemigo(enemigo)
        return perdida

    def registrar_muerte_enemigo(self, enemigo):
        """Quita al enemigo de la sala, deja su botín y avisa a los observadores.

        Actor.morir ya canceló su acción y sus efectos (sin recorrer la agenda).
        """
        sala = enemigo.sala_actual
        if sala is not None and sala.enemigos_activos.contiene_valor(enemigo):
            self.historial.registrar(DeltaListaSimple(sala.enemigos_activos, enemigo))
            sala.enemigos_activos.eliminar_valor(enemigo)
        self.historial.registrar(DeltaAtributos(self, "enemigos_derrotados"))
        self.enemigos_derrotados += 1
        self._emitir(f"{self.nombre_enemigo(enemigo)} muere.")
        if sala is not None:
            self._soltar_botin(enemigo, sala)
        for funcion in self.al_morir_enemigo:
            funcion(enemigo)

    def _soltar_botin(self, enemigo, sala):
        if len(enemigo.suelta) == 0:
            return
        if self.fabrica is None or self._resolver_ficha is None:
            raise RuntimeError("La partida necesita fábrica y resolver_ficha para el botín.")
        # El contador de la fábrica también se revierte: ids reproducibles.
        self.historial.registrar(DeltaAtributos(self.fabrica, "siguiente_id"))
        for tipo_id in enemigo.suelta:
            ficha = self._resolver_ficha(tipo_id)
            if ficha is None:
                raise RuntimeError(f"No se pudo resolver la ficha del botín {tipo_id}.")
            objeto = self.fabrica.crear(ficha)
            self.historial.registrar(DeltaListaSimple(sala.objetos_suelo, objeto))
            sala.objetos_suelo.insertar_al_final(objeto)
            self._emitir(f"Cae al suelo: {objeto.nombre}.")

    @staticmethod
    def nombre_enemigo(enemigo):
        """Identificador visible y único (§2.6): 'Rata gigante #e-201'."""
        return f"{enemigo.nombre} #{enemigo.instancia_id}"

    # ------------------------------------------------------------------ fin

    def verificar_fin(self):
        """Derrota si la vida llegó a 0; victoria al estar en la sala de salida."""
        if self.terminada:
            return self.estado
        if not self.jugador.vivo:
            self._cambiar_estado(DERROTA)
            self._emitir("Has muerto.")
        elif self.jugador.sala_actual.id == self.cripta.sala_salida_id:
            self._cambiar_estado(VICTORIA)
            self._emitir("¡Escapaste de la cripta!")
        return self.estado

    def _cambiar_estado(self, nuevo):
        self.historial.registrar(DeltaAtributos(self, "estado"))
        self.estado = nuevo

    # ------------------------------------------------------------------ avisos

    def _emitir(self, texto):
        for funcion in self.al_mensaje:
            funcion(self.reloj.tiempo_actual, texto)

    def _notificar_entrada(self, anterior, nueva):
        for funcion in self.al_entrar_sala:
            funcion(anterior, nueva)
