"""Agenda virtual determinista; no conoce HTTP, disco ni interfaz gráfica."""
import random
from estructuras.heap_minimo import HeapMinimo
from estructuras.vector_dinamico import Vector
from modelo.deltas import DeltaAtributos, DeltaEvento, DeltaEfecto, DeltaVelocidad


def entero(valor, nombre, minimo=0):
    if type(valor) is not int or valor < minimo:
        raise ValueError(f'{nombre} debe ser un entero >= {minimo}.')
    return valor


_FALTA = object()   # distingue "atributo ausente" de un atributo que vale None


class Evento:
    """La función ejecutar recibe el reloj; tipo/dueno identifican el evento.

    El guardado binario debe reconstruir ejecutores por tipo, no serializar
    funciones Python. El dueño guarda el handle que devuelve programar.
    """
    def __init__(self, ejecutar, tipo, dueno, campo, efecto):
        self.ejecutar = ejecutar
        self.tipo = tipo
        self.dueno = dueno
        self.campo = campo
        self.efecto = efecto
        self.nodo_dueno = None


class Reloj:
    def __init__(self, semilla, historial=None):
        entero(semilla, 'semilla')
        self.semilla = semilla
        self._azar = random.Random(semilla)
        self.tiempo_actual = 0
        self.agenda = HeapMinimo()
        self.historial = historial
        self._ejecutando = False
        self.contador_ejecutados = 0
        self.contador_calculos_dano = 0

    @property
    def azar(self):
        """Generador compartido por las decisiones y el combate de esta partida."""
        return self._azar

    @staticmethod
    def intervalo(costo, velocidad):
        entero(costo, 'costo')
        entero(velocidad, 'velocidad', 1)
        return max(1, costo * 100 // velocidad)

    def registrar(self, delta):
        return self.historial is not None and self.historial.registrar(delta)

    def vincular_actor(self, actor):
        if actor._reloj is not None and actor._reloj is not self:
            raise ValueError('Un actor no puede pertenecer a dos relojes.')
        actor._reloj = self

    def programar_en(self, tiempo, ejecutar, *, tipo='efecto', dueno=None,
                     campo=None, efecto=True, _campos_extra=()):
        """Programa un instante absoluto >= ahora. Retorna el handle del heap.

        _campos_extra (uso interno de programar): otros atributos del dueño que
        se guardan en el mismo delta que el handle, porque se cambian juntos.
        """
        if type(tiempo) is not int or tiempo < 0:
            entero(tiempo, 'tiempo')
        if tiempo < self.tiempo_actual:
            raise ValueError('No se puede programar en el pasado.')
        if not callable(ejecutar):
            raise TypeError('El ejecutor debe ser una función que reciba el reloj.')
        if campo is not None:
            anterior = _FALTA if dueno is None else getattr(dueno, campo, _FALTA)
            if anterior is _FALTA:
                raise ValueError('El campo del handle debe existir en el dueño.')
            if anterior is not None and anterior.valido and anterior._en_heap:
                raise ValueError('Cancela el evento anterior antes de sustituirlo.')
        if dueno is not None:
            reloj_dueno = getattr(dueno, '_reloj', _FALTA)
            if reloj_dueno is not _FALTA:
                if not dueno.vivo:
                    raise ValueError('No se programan eventos para actores muertos.')
                if reloj_dueno is not self:
                    self.vincular_actor(dueno)
        evento = Evento(ejecutar, tipo, dueno, campo, efecto)
        entrada = self.agenda.insertarEntrada(tiempo, evento)
        self.registrar((DeltaEfecto if efecto else DeltaEvento)(self, entrada, nueva=True))
        if campo is not None:
            self.registrar(DeltaAtributos(dueno, campo, *_campos_extra))
            setattr(dueno, campo, entrada)
        if efecto:
            self._sincronizar_efecto(entrada, True)
        return entrada

    def programar(self, actor, costo, ejecutar):
        """Programa la próxima acción a ahora + intervalo(costo, velocidad)."""
        tiempo = self.tiempo_actual + self.intervalo(costo, actor.velocidad)
        # Un solo delta guarda handle y tiempo_siguiente: se cambian juntos.
        entrada = self.programar_en(tiempo, ejecutar, tipo='accion', dueno=actor,
                                    campo='evento_actual', efecto=False,
                                    _campos_extra=('tiempo_siguiente',))
        actor.tiempo_siguiente = tiempo
        return entrada

    def programar_inicial(self, actor, ejecutar):
        """Primera acción del jugador en t=0. Enemigos usan programar(costo=100)."""
        if self.tiempo_actual != 0:
            raise ValueError('La primera acción se programa al iniciar la partida.')
        entrada = self.programar_en(0, ejecutar, tipo='accion', dueno=actor,
                                    campo='evento_actual', efecto=False)
        self.registrar(DeltaAtributos(actor, 'tiempo_siguiente'))
        actor.tiempo_siguiente = 0
        return entrada

    def _validar_entrada(self, entrada):
        if getattr(entrada, '_propietario', None) is not self.agenda:
            raise ValueError('El evento pertenece a otra agenda.')

    def _sincronizar_efecto(self, entrada, pendiente):
        evento = entrada.dato
        dueno = evento.dueno
        if not evento.efecto or dueno is None or not hasattr(dueno, 'eventos_efectos'):
            return
        lista = dueno.eventos_efectos
        presente = lista.pertenece(evento.nodo_dueno)
        if pendiente and not presente:
            evento.nodo_dueno = lista.insertar_al_final(entrada)
        elif not pendiente and presente:
            lista.eliminar_nodo(evento.nodo_dueno)
            evento.nodo_dueno = None

    def cancelar(self, entrada):
        if entrada is None:
            return False
        self._validar_entrada(entrada)
        if not entrada.valido or not entrada._en_heap:
            return False
        evento = entrada.dato
        self.registrar((DeltaEfecto if evento.efecto else DeltaEvento)(self, entrada))
        self.agenda.invalidarEntrada(entrada)
        self._sincronizar_efecto(entrada, False)
        if evento.campo and getattr(evento.dueno, evento.campo) is entrada:
            self.registrar(DeltaAtributos(evento.dueno, evento.campo))
            setattr(evento.dueno, evento.campo, None)
        return True

    def cancelar_actor(self, actor):
        """Visita solo los efectos del actor, nunca toda la agenda."""
        self.cancelar(actor.evento_actual)
        while not actor.eventos_efectos.esta_vacia():
            nodo = actor.eventos_efectos.head()
            if not self.cancelar(nodo.valor):
                actor.eventos_efectos.eliminar_nodo(nodo)

    def reprogramar_por_velocidad(self, actor, nueva_velocidad):
        entero(nueva_velocidad, 'velocidad nueva', 1)
        entero(actor.velocidad, 'velocidad anterior', 1)
        if not actor.vivo:
            raise ValueError('No se cambia la velocidad de un actor muerto.')
        self.vincular_actor(actor)
        anterior = actor.evento_actual
        pendiente = anterior is not None and anterior.valido and anterior._en_heap
        if pendiente:
            self._validar_entrada(anterior)
            restante = max(1, (anterior.tiempo - self.tiempo_actual)
                           * actor.velocidad // nueva_velocidad)
        self.registrar(DeltaVelocidad(actor))
        actor.velocidad = nueva_velocidad
        if not pendiente:
            return None
        evento = anterior.dato
        self.cancelar(anterior)
        tiempo = self.tiempo_actual + restante
        nueva = self.programar_en(tiempo, evento.ejecutar, tipo=evento.tipo,
                                  dueno=actor, campo='evento_actual', efecto=False)
        actor.tiempo_siguiente = tiempo
        return nueva

    def calcular_dano(self, ataque, defensa):
        entero(ataque, 'ataque')
        entero(defensa, 'defensa')
        self.contador_calculos_dano += 1
        return max(1, ataque + self._azar.randint(0, 4) - defensa)

    def proximos_eventos(self, n):
        """Lectura de solo lectura de los próximos n eventos pendientes (para un
        panel informativo tipo 'próximos turnos'); no muta la agenda. Delega en
        HeapMinimo.vista_ordenada, que ya omite las entradas canceladas, y aquí
        se descartan además las de un dueño ya muerto. En la práctica esto casi
        nunca filtra nada, porque Actor.morir() ya cancela los eventos
        pendientes del actor al llamar a reloj.cancelar_actor(); el filtro es
        defensivo, no depende de esa garantía para no exponer un actor muerto.
        """
        resultado = Vector()
        for entrada in self.agenda.vista_ordenada(n):
            if getattr(entrada.dato.dueno, 'vivo', True):
                resultado.agregarValor(entrada)
        return resultado

    def proximo(self):
        """Limpia cancelados; la consulta posterior del heap es O(1)."""
        self.agenda.descartar_cancelados()
        return self.agenda.minimo()

    def _retirar(self, entrada):
        evento = entrada.dato
        self.registrar((DeltaEfecto if evento.efecto else DeltaEvento)(self, entrada))
        extraida = self.agenda.extraer_entrada()
        if extraida is not entrada:
            raise RuntimeError('Se intentó retirar un evento fuera de orden.')
        entrada.valido = False
        if evento.efecto:
            self._sincronizar_efecto(entrada, False)
        if evento.campo and getattr(evento.dueno, evento.campo) is entrada:
            self.registrar(DeltaAtributos(evento.dueno, evento.campo))
            setattr(evento.dueno, evento.campo, None)
        self.tiempo_actual = entrada.tiempo

    def _ejecutar(self, entrada):
        self._retirar(entrada)
        self._ejecutando = True
        try:
            entrada.dato.ejecutar(self)
            self.contador_ejecutados += 1
        finally:
            self._ejecutando = False

    def avanzar_y_ejecutar(self, hasta=None):
        """Ejecuta un evento o todos los que vencen hasta el instante indicado.

        Para detenerse en una decisión del jugador se usa avanzar_hasta_turno,
        que respeta los desempates y los cambios de velocidad durante la espera.
        """
        if self._ejecutando:
            raise RuntimeError('Un ejecutor no puede avanzar recursivamente el reloj.')
        if hasta is not None:
            entero(hasta, 'tiempo límite')
            if hasta < self.tiempo_actual:
                raise ValueError('El reloj solo retrocede mediante el historial.')
        cantidad = 0
        while True:
            entrada = self.proximo()
            if entrada is None or (hasta is not None and entrada.tiempo > hasta):
                break
            self._ejecutar(entrada)
            cantidad += 1
            if hasta is None:
                return cantidad
        if hasta is not None:
            self.tiempo_actual = hasta
        return cantidad

    def avanzar_hasta_turno(self, actor):
        """Deja pendiente la acción del actor al llegar a su decisión."""
        if self._ejecutando:
            raise RuntimeError('No se puede avanzar dentro de otro evento.')
        self.vincular_actor(actor)
        while actor.vivo:
            turno = actor.evento_actual
            if turno is None or not turno.valido or not turno._en_heap:
                raise RuntimeError('El actor no tiene un turno pendiente.')
            entrada = self.proximo()
            if entrada is turno:
                self.tiempo_actual = entrada.tiempo
                return entrada
            if entrada is None:
                raise RuntimeError('La agenda no contiene el turno del actor.')
            self._ejecutar(entrada)
        return None

    def tomar_turno(self, actor):
        """Tras validar la acción e iniciar historial, retira el turno del jugador."""
        entrada = self.proximo()
        if (entrada is None or entrada is not actor.evento_actual
                or entrada.tiempo != self.tiempo_actual or not actor.vivo):
            raise RuntimeError('Todavía no corresponde la decisión del actor.')
        self._retirar(entrada)

    def extraer_siguiente(self):
        """Paso 1 del bucle principal: retira el evento válido mínimo.

        Orden (tiempo, seq); los cancelados se descartan antes (lazy). Avanza el
        reloj al instante del evento, desvincula el handle de su dueño y registra
        el delta si hay un intervalo abierto. NO ejecuta el callback: el bucle
        decide qué hacer según el dueño (jugador, enemigo o efecto).
        Devuelve la entrada retirada, o None si la agenda está vacía.
        """
        if self._ejecutando:
            raise RuntimeError('No se puede extraer dentro de otro evento.')
        entrada = self.proximo()
        if entrada is None:
            return None
        self._retirar(entrada)
        return entrada

    def ejecutar_evento(self, entrada):
        """Ejecuta el callback de una entrada ya retirada con extraer_siguiente.

        Se usa para efectos del entorno (rearme, cierre, veneno...). Un efecto
        recurrente se reprograma dentro de su propio callback.
        """
        if entrada._en_heap:
            raise RuntimeError('Primero se retira el evento con extraer_siguiente.')
        self._ejecutando = True
        try:
            entrada.dato.ejecutar(self)
            self.contador_ejecutados += 1
        finally:
            self._ejecutando = False

    def contadores(self):
        return (('eventos_ejecutados', self.contador_ejecutados),
                ('calculos_dano', self.contador_calculos_dano))
