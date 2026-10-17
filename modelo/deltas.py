"""Cambios reversibles puntuales. No se copia la partida ni su caché."""


class DeltaAtributos:
    def __init__(self, objeto, *campos):
        self.objeto = objeto
        if len(campos) == 1:
            campo = campos[0]
            self.anteriores = ((campo, getattr(objeto, campo)),)
        else:
            self.anteriores = tuple([(campo, getattr(objeto, campo)) for campo in campos])

    def revertir(self):
        for campo, valor in self.anteriores:
            setattr(self.objeto, campo, valor)


class DeltaVida(DeltaAtributos):
    def __init__(self, actor):
        super().__init__(actor, 'vida', 'vivo')


class DeltaPuerta(DeltaAtributos):
    def __init__(self, salida):
        super().__init__(salida, 'cerrada')


class DeltaTrampa(DeltaAtributos):
    def __init__(self, trampa):
        super().__init__(trampa, 'armada')


class DeltaRastro(DeltaAtributos):
    def __init__(self, sala):
        super().__init__(sala, 'tiempo_rastro')


class DeltaVelocidad(DeltaAtributos):
    def __init__(self, actor):
        super().__init__(actor, 'velocidad', 'tiempo_siguiente')


class DeltaEvento:
    """Conserva una referencia; no reconstruye ni copia toda la agenda."""
    def __init__(self, reloj, entrada, nueva=False):
        self.reloj = reloj
        self.entrada = entrada
        self.estaba_pendiente = not nueva and entrada.valido and entrada._en_heap

    def revertir(self):
        if self.estaba_pendiente:
            self.reloj.agenda.restaurarEntrada(self.entrada)
        else:
            self.reloj.agenda.invalidarEntrada(self.entrada)
        self.reloj._sincronizar_efecto(self.entrada, self.estaba_pendiente)


class DeltaEfecto(DeltaEvento):
    """Un efecto usa las mismas reglas de agenda que una acción."""


class DeltaReloj:
    def __init__(self, reloj):
        self.reloj = reloj
        self.tiempo = reloj.tiempo_actual
        self.secuencia = reloj.agenda.siguiente_secuencia
        # Estado de un único generador, tamaño fijo; no es una copia del juego.
        self.estado_azar = reloj.azar.getstate()

    def revertir(self):
        self.reloj.tiempo_actual = self.tiempo
        self.reloj.agenda.restaurar_secuencia(self.secuencia)
        self.reloj.azar.setstate(self.estado_azar)


class DeltaActivacion:
    """Activación de los dormidos de una sala, como un solo cambio.

    Guarda el orden de la lista de dormidos de esa sala y cuántos activos había;
    nada más. Se registra antes de tocar las listas, así se revierte después de
    los cambios de cada enemigo: en ese momento los activados son justo la cola
    de la lista de activos.
    """
    def __init__(self, sala):
        self.sala = sala
        self.dormidos = tuple(sala.enemigos_dormidos)
        self.activos_antes = len(sala.enemigos_activos)

    def revertir(self):
        self.sala.enemigos_activos.conservar_primeros(self.activos_antes)
        self.sala.enemigos_dormidos.conservar_primeros(0)
        self.sala.enemigos_dormidos.insertar_varios_al_final(self.dormidos)


class DeltaListaSimple:
    """Pertenencia/posición de UN actor u objeto en una lista de sala.

    Para movimientos, registrar un delta por cada lista afectada y un
    DeltaAtributos(actor, 'sala_actual'). No duplica los restantes elementos.
    """
    def __init__(self, lista, valor):
        self.lista, self.valor = lista, valor
        self.excluido = getattr(valor, 'clase', None) == 'pergamino_retroceso'
        self.indice = None
        if not self.excluido:
            for indice, actual in enumerate(lista):
                if actual is valor:
                    self.indice = indice
                    break

    def revertir(self):
        if self.excluido:
            return
        self.lista.eliminar_valor(self.valor)
        if self.indice is not None:
            self.lista.insertar_en(min(self.indice, len(self.lista)), self.valor)


class DeltaRetiro:
    """Un valor que ya se quitó de una ListaSimple en la posición 'indice'
    (None si no estaba). Revertir lo vuelve a poner ahí sin buscarlo."""
    def __init__(self, lista, valor, indice):
        self.lista, self.valor, self.indice = lista, valor, indice

    def revertir(self):
        if self.indice is not None:
            self.lista.insertar_en(min(self.indice, len(self.lista)), self.valor)


class DeltaAgregadoAlFinal:
    """Un valor agregado al final de una ListaSimple.

    Al deshacer en orden inverso la lista vuelve a estar como justo después de
    agregarlo, así que se quita en O(1) con el nodo previo guardado. Si alguien
    la cambió sin delta, se recurre a buscar el valor.
    """
    def __init__(self, lista, nodo, anterior):
        self.lista, self.nodo, self.anterior = lista, nodo, anterior

    def revertir(self):
        if not self.lista.quitar_cola(self.nodo, self.anterior):
            self.lista.eliminar_valor(self.nodo.valor)


class DeltaObjeto:
    """Un objeto y su posición, equipo y cursor; nunca el inventario completo.

    Crear ANTES de recoger, soltar, equipar o consumir un objeto. Los pergaminos
    quedan excluidos tanto al recoger como al soltar o consumir.
    """
    def __init__(self, jugador, objeto, nodo=None):
        self.excluido = objeto.clase == 'pergamino_retroceso'
        if self.excluido:
            return
        self.jugador, self.objeto = jugador, objeto
        self.suelo = jugador.sala_actual.objetos_suelo if jugador.sala_actual else None
        self.nodo = nodo if nodo is not None else jugador.buscar_nodo(objeto.instancia_id)
        self.anterior = self.nodo.anterior if self.nodo else None
        self.siguiente = self.nodo.siguiente if self.nodo else None
        self.indice_suelo = None
        if self.nodo is None and self.suelo is not None:
            for indice, actual in enumerate(self.suelo):
                if actual is objeto:
                    self.indice_suelo = indice
                    break
        self.cursor = jugador.cursor
        self.equipo = DeltaAtributos(jugador, 'arma_equipada', 'armadura_equipada',
                                    'ataque', 'defensa')

    def revertir(self):
        if self.excluido:
            return
        jugador = self.jugador
        actual = jugador.buscar_nodo(self.objeto.instancia_id)
        if actual is not None:
            jugador.inventario.eliminar_nodo(actual)
        if self.suelo is not None:
            self.suelo.eliminar_valor(self.objeto)
        if self.nodo is not None:
            jugador.inventario.restaurar_nodo(self.nodo, self.anterior, self.siguiente)
        elif self.indice_suelo is not None:
            self.suelo.insertar_en(min(self.indice_suelo, len(self.suelo)), self.objeto)
        self.equipo.revertir()
        # No apuntar a un pergamino consumido de forma irreversible.
        jugador.cursor = (self.cursor if jugador.inventario.pertenece(self.cursor)
                          else jugador.inventario.head())
