"""Agenda virtual determinista; no conoce HTTP, disco ni interfaz gráfica."""
import random
from estructuras.heap_minimo import HeapMinimo
from modelo.deltas import DeltaAtributos, DeltaEvento, DeltaEfecto, DeltaVelocidad


def entero(valor, nombre, minimo=0):
    if type(valor) is not int or valor < minimo:
        raise ValueError(f'{nombre} debe ser un entero >= {minimo}.')
    return valor


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
        """Compartir ESTA instancia con Enemigo.decidir_accion, no crear otra."""
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
                     campo=None, efecto=True):
        """Programa un instante absoluto >= ahora. Retorna el handle del heap."""
        entero(tiempo, 'tiempo')
        if tiempo < self.tiempo_actual:
            raise ValueError('No se puede programar en el pasado.')
        if not callable(ejecutar):
            raise TypeError('El ejecutor debe ser una función que reciba el reloj.')
        if campo is not None:
            if dueno is None or not hasattr(dueno, campo):
                raise ValueError('El campo del handle debe existir en el dueño.')
            anterior = getattr(dueno, campo)
            if anterior is not None and anterior.valido and anterior._en_heap:
                raise ValueError('Cancela el evento anterior antes de sustituirlo.')
        if dueno is not None and hasattr(dueno, '_reloj'):
            if not dueno.vivo:
                raise ValueError('No se programan eventos para actores muertos.')
            self.vincular_actor(dueno)
        evento = Evento(ejecutar, tipo, dueno, campo, efecto)
        entrada = self.agenda.insertarEntrada(tiempo, evento)
        self.registrar((DeltaEfecto if efecto else DeltaEvento)(self, entrada, nueva=True))
        if campo is not None:
            self.registrar(DeltaAtributos(dueno, campo))
            setattr(dueno, campo, entrada)
        self._sincronizar_efecto(entrada, True)
        return entrada

    def programar(self, actor, costo, ejecutar):
        """Programa la próxima acción a ahora + intervalo(costo, velocidad)."""
        tiempo = self.tiempo_actual + self.intervalo(costo, actor.velocidad)
        entrada = self.programar_en(tiempo, ejecutar, tipo='accion', dueno=actor,
                                    campo='evento_actual', efecto=False)
        self.registrar(DeltaAtributos(actor, 'tiempo_siguiente'))
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
        """Sin hasta ejecuta UN evento; con hasta, todos <= ese instante.

        Para volver a la decisión del jugador usar avanzar_hasta_turno:
        incluye el desempate por seq y cambios de velocidad durante la espera.
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

    def contadores(self):
        return (('eventos_ejecutados', self.contador_ejecutados),
                ('calculos_dano', self.contador_calculos_dano))
