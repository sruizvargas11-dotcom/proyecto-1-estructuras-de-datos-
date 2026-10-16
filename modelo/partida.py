from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar
from modelo.deltas import DeltaAtributos, DeltaListaSimple, DeltaObjeto
from modelo.entorno import Entorno
from modelo.historial import Historial
from modelo.rastro import Rastro
from modelo.reloj import Reloj
from modelo.efectos import iniciar_regeneracion
from modelo.ejecutor_evento import EjecutorEvento

COSTO_ACCION_ENEMIGO = 100

EN_CURSO = "en_curso"
VICTORIA = "victoria"
DERROTA = "derrota"
CREADA = "creada"


def _clave_natural(texto):
    """'e-9' < 'e-10': compara los tramos numéricos como números."""
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

        # Funciones que reciben avisos de muerte, movimiento y mensajes del modelo.
        self.al_morir_enemigo = Vector()   # f(enemigo)
        self.al_entrar_sala = Vector()     # f(sala_anterior, sala_nueva)
        self.al_mensaje = Vector()         # f(tiempo, texto)

        # Función que aplica el efecto de un objeto: f(partida, objeto) -> bool.
        self.aplicar_efecto = None

        self.reloj.vincular_actor(jugador)


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
        """Resumen de acciones, enemigos derrotados, tiempo y resultado de la partida."""
        return (("cripta_id", self.cripta_id),
                ("version_cripta", self.version_cripta),
                ("acciones_jugador", self.acciones_jugador),
                ("enemigos_derrotados", self.enemigos_derrotados),
                ("tiempo_final", self.reloj.tiempo_actual),
                ("resultado", self.estado))


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
        self.reloj.programar_inicial(self.jugador, EjecutorEvento('decision'))
        self.estado = EN_CURSO
        self.activar_enemigos(sala)
        self._emitir(f"Entras a {sala.nombre}.")
        self._notificar_entrada(None, sala)
        return self

    def programar_siguiente_jugador(self, costo):
        """El controlador lo llama tras aplicar una acción del jugador."""
        return self.reloj.programar(self.jugador, costo, EjecutorEvento('decision'))

    def contar_accion_jugador(self):
        """Una acción que consumió tiempo (§2.12). Reversible con el pergamino."""
        self.historial.registrar(DeltaAtributos(self, "acciones_jugador"))
        self.acciones_jugador += 1

    def refrescar_rastro(self):
        """Apéndice B: el rastro de la sala actual se refresca en cada acción."""
        self.rastro.registrar(self.jugador.sala_actual.id, self.reloj.tiempo_actual)


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
            iniciar_regeneracion(self.reloj, enemigo)
            activados += 1
        return activados

    def entrar_a_sala(self, sala):
        """Efectos de completar un movimiento del jugador hacia 'sala'."""
        anterior = self.jugador.sala_actual
        self.historial.registrar(DeltaAtributos(self.jugador, "sala_actual"))
        self.jugador.sala_actual = sala
        self.refrescar_rastro()
        self._emitir(f"Entras a {sala.nombre}.")
        # la trampa se activa justo después del movimiento.
        vida_antes = self.jugador.vida
        if self.entorno.al_entrar(self.jugador, sala):
            self._emitir(f"¡Una trampa se activa! -{vida_antes - self.jugador.vida} de vida.")
        if self.jugador.vivo:
            self.activar_enemigos(sala)
        self._notificar_entrada(anterior, sala)
        self.verificar_fin()
        return sala


    def ejecutor_enemigo(self, enemigo):
        """Callback del heap para la acción de 'enemigo'.

        Al cargar una partida guardada se reconstruye con este mismo método a partir
        del dueño del evento (no se serializan funciones).
        """
        return EjecutorEvento('enemigo', enemigo, self)

    def turno_enemigo(self, enemigo):
        """Callback del heap"""
        accion = self.ejecutar_accion_enemigo(enemigo)
        self.programar_siguiente_enemigo(enemigo)
        return accion

    def ejecutar_accion_enemigo(self, enemigo):
        """Paso 3 del bucle"""
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
        self.verificar_fin()
        return accion

    def programar_siguiente_enemigo(self, enemigo):
        """Paso para un enemigo: próxima acción a ahora + intervalo(100, vel)"""
        if not enemigo.vivo or self.terminada:
            return None
        return self.reloj.programar(enemigo, COSTO_ACCION_ENEMIGO,
                                    self.ejecutor_enemigo(enemigo))

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
        """Quita al enemigo de la sala, deja su botín y avisa a los observadores"""
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


    def atacar(self, enemigo):
        """Ataque del jugador a un enemigo de su sala. Devuelve la vida quitada."""
        if enemigo.sala_actual is not self.jugador.sala_actual or not enemigo.vivo:
            raise ValueError("El enemigo no está en la sala del jugador.")
        dano = self.reloj.calcular_dano(self.jugador.ataque, enemigo.defensa)
        perdida = enemigo.recibir_dano(dano)
        self._emitir(f"Atacas a {self.nombre_enemigo(enemigo)}: -{perdida} de vida.")
        if not enemigo.vivo:
            self.registrar_muerte_enemigo(enemigo)
        return perdida

    def llave_para(self, salida):
        """Llave del inventario que abre la salida (por tipo_id), o None."""
        if salida.llave is None:
            return None
        for nodo in self.jugador.inventario.recorrer_desde_frente():
            objeto = nodo.valor
            if objeto.clase == "llave" and objeto.tipo_id == salida.llave:
                return objeto
        return None

    def abrir(self, salida):
        """Abre con la llave ya validada; la llave no se consume."""
        abierta = self.entorno.abrir(salida)
        if abierta:
            self._emitir(f"Abres la puerta {salida.direccion}.")
        return abierta

    def consumir(self, nodo):
        """Quita del inventario un objeto gastado (reversible con el pergamino)."""
        jugador = self.jugador
        self.historial.registrar(DeltaObjeto(jugador, nodo.valor, nodo))
        if jugador.cursor is nodo:
            jugador.cursor = nodo.siguiente or nodo.anterior
        jugador.inventario.eliminar_nodo(nodo)

    def usar_objeto(self, nodo):
        """Usa un objeto del inventario. Devuelve True si tuvo efecto."""
        objeto = nodo.valor
        if objeto.clase == "pocion":
            if objeto.cura > 0:
                curado = self.jugador.curar(objeto.cura)
                self._emitir(f"Usas {objeto.nombre}: +{curado} de vida.")
            if objeto.modificador_velocidad and self.aplicar_efecto is not None:
                self.aplicar_efecto(self, objeto)
                self._emitir(f"Usas {objeto.nombre}: velocidad {self.jugador.velocidad}.")
            self.consumir(nodo)
            return True
        if self.aplicar_efecto is not None and objeto.clase in ("antidoto", "antorcha"):
            if self.aplicar_efecto(self, objeto):
                if objeto.clase == "antidoto":
                    self.consumir(nodo)
                self._emitir(f"Usas {objeto.nombre}.")
                return True
        return False


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


    def _emitir(self, texto):
        for funcion in self.al_mensaje:
            funcion(self.reloj.tiempo_actual, texto)

    def _notificar_entrada(self, anterior, nueva):
        for funcion in self.al_entrar_sala:
            funcion(anterior, nueva)
