
from controlador.estado_final import lineas_estado
from modelo.efectos import apagar_antorcha
from controlador.narrador_eventos import describir_evento
from estructuras.vector_dinamico import Vector
from modelo.entidades.enemigo import Enemigo
from modelo.entidades.objetos.arma import Arma
from modelo.entidades.objetos.armadura import Armadura

COSTO_MOVER = 100
COSTO_ATACAR = 100
COSTO_ESPERAR = 100
COSTO_USAR = 50
COSTO_EQUIPAR = 50
COSTO_ABRIR = 50
COSTO_RECOGER = 25
COSTO_SOLTAR = 25

DIRECCIONES = ("N", "S", "E", "O")
CRITERIOS_INVENTARIO = ("peso", "valor", "nombre")

# Comando del usuario -> nombre interno. Se aceptan letras y palabras completas
# (las palabras son las que se escriben en la bitácora, útiles para el replay).
_ALIAS = (
    ("N", "mover"), ("S", "mover"), ("E", "mover"), ("O", "mover"),
    ("MOVER", "mover"),
    ("A", "atacar"), ("ATACAR", "atacar"),
    ("W", "esperar"), ("ESPERAR", "esperar"),
    ("R", "recoger"), ("RECOGER", "recoger"),
    ("T", "soltar"), ("SOLTAR", "soltar"),
    ("EQ", "equipar"), ("EQUIPAR", "equipar"),
    ("DEQ", "desequipar"), ("DESEQUIPAR", "desequipar"),
    ("AP", "apagar"), ("APAGAR", "apagar"),
    ("U", "usar"), ("USAR", "usar"),
    ("AB", "abrir"), ("ABRIR", "abrir"),
    ("P", "pergamino"), ("PERGAMINO", "pergamino"),
    ("I", "inventario"), ("INVENTARIO", "inventario"),
    ("H", "ayuda"), ("?", "ayuda"), ("AYUDA", "ayuda"),
    ("Q", "salir"), ("SALIR", "salir"),
    ("G", "guardar"), ("GUARDAR", "guardar"),
    ("L", "cargar"), ("CARGAR", "cargar"),
    ("IS", "siguiente"), ("IA", "anterior"), ("IC", "consultar"),
)


class Comando:
    """Comando ya interpretado: nombre interno y argumento (dirección o índice)."""

    def __init__(self, nombre, argumento=None):
        self.nombre = nombre
        self.argumento = argumento

    def texto(self):
        """Forma normalizada que se guarda en la bitácora."""
        if self.argumento is None:
            return self.nombre
        return f"{self.nombre} {self.argumento}"


def interpretar(texto):
    """Traduce la entrada del usuario a un Comando. Devuelve (comando, error)."""
    partes = texto.strip().split()
    if not partes:
        return None, "Escribe un comando (H para ayuda)."
    clave = partes[0].upper()
    nombre = None
    for alias, interno in _ALIAS:
        if alias == clave:
            nombre = interno
            break
    if nombre is None:
        return None, f"Comando desconocido: {partes[0]}. Escribe H para ver la ayuda."
    resto = partes[1:]

    if nombre in ("guardar", "cargar"):
        ruta = texto.strip().partition(' ')[2].strip().strip('"') or None
        return Comando(nombre, ruta), None
    maximo = 0 if nombre in ('esperar', 'pergamino', 'ayuda', 'salir',
                            'siguiente', 'anterior', 'consultar') or clave in DIRECCIONES else 1
    if len(resto) > maximo:
        return None, 'Sobran argumentos. Escribe H para ver la ayuda.'

    if nombre == "mover":
        # 'N' sola, o 'mover N'.
        direccion = clave if clave in DIRECCIONES else (resto[0].upper() if resto else None)
        if direccion not in DIRECCIONES:
            return None, "Indica la dirección: N, S, E u O."
        return Comando("mover", direccion), None
    if nombre == "abrir":
        if not resto or resto[0].upper() not in DIRECCIONES:
            return None, "Indica qué puerta abrir: AB N, AB S, AB E o AB O."
        return Comando("abrir", resto[0].upper()), None
    if nombre in ("atacar", "recoger", "soltar", "equipar", "desequipar", "apagar", "usar"):
        if not resto:
            return Comando(nombre, 1), None
        try:
            numero = int(resto[0])
        except ValueError:
            numero = 0
        if not resto[0].isdigit() or numero < 1:
            return None, "El número debe ser un entero positivo (1, 2, ...)."
        return Comando(nombre, numero), None
    if nombre == "inventario":
        criterio = resto[0].lower() if resto else None
        if criterio is not None and criterio not in CRITERIOS_INVENTARIO:
            return None, "Vistas del inventario: I peso, I valor o I nombre."
        return Comando("inventario", criterio), None
    return Comando(nombre), None


def _elemento(iterable, numero):
    """Elemento 'numero' (desde 1) de una lista propia, o None."""
    indice = 1
    for valor in iterable:
        if indice == numero:
            return valor
        indice += 1
    return None


def _nodo_inventario(jugador, numero):
    indice = 1
    for nodo in jugador.inventario.recorrer_desde_frente():
        if indice == numero:
            return nodo
        indice += 1
    return None


class ControladorJuego:
    def __init__(self, sesion, vista, ruta_guardado=None, tabla_puntajes=None):
        """tabla_puntajes: TablaPuntajes donde registrar la partida al terminar en
        victoria o derrota; None (pruebas, replay) no registra nada."""
        self.sesion = sesion
        self.partida = sesion.partida
        self.red = sesion.red
        self.bitacora = sesion.bitacora
        self.vista = vista
        self.reloj = self.partida.reloj
        self.historial = self.partida.historial
        self.jugador = self.partida.jugador
        self._salir = False
        self.ruta_guardado = ruta_guardado or 'partidas/partida.sav'
        self.tabla_puntajes = tabla_puntajes
        self.error_puntaje = None
        self._puntaje_intentado = False
        self.registro_puntaje = None    # RegistroPuntaje de esta partida, si se registró
        self._protegidas = Vector()     # tipo_ids marcados en_uso por el controlador

        self.contador_ciclos = 0
        self.contador_turnos_jugador = 0
        self.contador_turnos_enemigo = 0
        self.contador_efectos = 0
        self.contador_rechazos = 0

        # Los mensajes del modelo van a la bitácora en pantalla de la vista.
        self.partida.al_mensaje.agregarValor(self.vista.agregar_mensaje)


    def jugar(self):
        """Bucle principal: ciclos de 4 pasos mientras la partida siga activa."""
        completa = False
        try:
            while not self.partida.terminada and not self._salir:
                self.ciclo()
            completa = True
        finally:
            self._cerrar(completa)
        return self.partida.estado

    def ciclo(self):
        """Un ciclo del bucle principal. Devuelve la entrada procesada."""
        self.contador_ciclos += 1

        # 1. Consultar el mínimo; el turno del jugador se retira dentro de su delta.
        entrada = self.reloj.proximo()
        if entrada is None:
            raise RuntimeError("La agenda quedó vacía con la partida en curso.")
        evento = entrada.dato
        actor = None   # quién actuó, para el paso 4
        costo = None

        # 2. Turno del jugador
        if evento.tipo == "accion" and evento.dueno is self.jugador:
            self.reloj.tiempo_actual = entrada.tiempo
            self.contador_turnos_jugador += 1
            costo = self._turno_jugador()
            if costo is not None:
                actor = self.jugador

        # 3. Turno de un enemigo
        elif evento.tipo == "accion" and isinstance(evento.dueno, Enemigo):
            self.reloj.extraer_siguiente(entrada)
            self.contador_turnos_enemigo += 1
            self.partida.ejecutar_accion_enemigo(evento.dueno)
            actor = evento.dueno

        # Efecto del entorno: rearme, cierre, veneno... 
        else:
            # No es la acción de un actor: su callback ya contiene la regla y,
            # si es recurrente, se reprograma solo.
            self.contador_efectos += 1
            self.reloj.extraer_siguiente(entrada)
            vida_antes = getattr(evento.dueno, "vida", None)
            self.reloj.ejecutar_evento(entrada)
            texto = describir_evento(self.partida, evento, vida_antes)
            if texto is not None:
                self.vista.agregar_mensaje(self.reloj.tiempo_actual, texto)
            self.partida.verificar_fin()

        # 4. Programar la siguiente acción
        if actor is not None:
            self._programar_siguiente(actor, costo)
        return entrada

    def _programar_siguiente(self, actor, costo):
        if self.partida.terminada or not actor.vivo:
            return
        if actor is self.jugador:
            self.partida.programar_siguiente_jugador(costo)
        else:
            self.partida.programar_siguiente_enemigo(actor)


    def _turno_jugador(self):
        """Paso 2. Devuelve el costo de la acción ejecutada, o None si se sale."""
        # Llegó la siguiente decisión: se cierra el intervalo anterior.
        if self.historial.registrando:
            self.historial.confirmar_accion()
        # Punto fijo de red: incorporar respuestas en orden de número.
        self.red.incorporar_listas()

        while True:
            if self.partida.terminada:
                return None
            # Fichas protegidas según la sala actual y el inventario (4.4).
            self._sincronizar_protegidas()
            # Mostrar estado y pedir un comando.
            self.vista.mostrar_estado(self.partida)
            comando, error = interpretar(self.vista.leer_comando())
            if error is not None:
                self._rechazar(error)
                continue
            # Comandos sin costo de tiempo.
            if comando.nombre == "salir":
                self._salir = True
                return None
            if comando.nombre == "ayuda":
                self.vista.mostrar_ayuda()
                continue
            if comando.nombre == "inventario":
                self._mostrar_inventario(comando.argumento)
                continue
            if comando.nombre in ('siguiente', 'anterior', 'consultar'):
                if comando.nombre == 'siguiente':
                    self.jugador.siguiente()
                elif comando.nombre == 'anterior':
                    self.jugador.anterior()
                self.vista.mostrar_objeto(self.jugador.cursor)
                continue
            if comando.nombre in ("guardar", "cargar"):
                self._persistir(comando)
                continue
            if comando.nombre == "pergamino":
                self._usar_pergamino()
                continue
            # Validar sin tocar el modelo: un rechazo no consume tiempo.
            rechazo = self._validar(comando)
            if rechazo is not None:
                self._rechazar(rechazo)
                continue
            # Ejecutar dentro de un intervalo nuevo del historial.
            costo = self._ejecutar(comando)
            if costo is not None:
                return costo

    def _rechazar(self, mensaje):
        self.contador_rechazos += 1
        self.vista.agregar_mensaje(self.reloj.tiempo_actual, mensaje)

    def _validar(self, comando):
        """Devuelve un mensaje de rechazo, o None si la acción puede ejecutarse."""
        sala = self.jugador.sala_actual
        nombre, arg = comando.nombre, comando.argumento

        if nombre == "mover":
            salida = sala.salida_hacia(arg)
            if salida is None:
                return f"No hay salida hacia {arg}."
            if salida.cerrada:
                return f"La puerta hacia {arg} está cerrada. Ábrela con AB {arg} si tienes la llave."
            # Sala pendiente: espera en tiempo real; el reloj virtual no avanza
            # y no se registra nada hasta confirmar.
            return self.red.asegurar_entrada(salida.sala_destino_id)

        if nombre == "abrir":
            salida = sala.salida_hacia(arg)
            if salida is None:
                return f"No hay puerta hacia {arg}."
            if not salida.cerrada:
                return f"La puerta hacia {arg} ya está abierta."
            if self.partida.llave_para(salida) is None:
                return "No tienes la llave correcta para esa puerta."
            return None

        if nombre == "atacar":
            if len(sala.enemigos_activos) == 0:
                return "No hay enemigos en esta sala."
            if _elemento(sala.enemigos_activos, arg) is None:
                return f"No existe el enemigo {arg}."
            return None

        if nombre == "recoger":
            if len(sala.objetos_suelo) == 0:
                return "No hay objetos en el suelo."
            if _elemento(sala.objetos_suelo, arg) is None:
                return f"No existe el objeto {arg} en el suelo."
            if len(self.jugador.inventario) >= self.jugador.inventario_max:
                return "Inventario lleno: suelta un objeto primero (T <n>)."
            return None

        if nombre in ("soltar", "equipar", "desequipar", "apagar", "usar"):
            nodo = _nodo_inventario(self.jugador, arg)
            if nodo is None:
                return f"No existe el objeto {arg} en el inventario."
            objeto = nodo.valor
            if nombre == "equipar" and not isinstance(objeto, (Arma, Armadura)):
                return "Solo se pueden equipar armas o armaduras."
            if nombre == "desequipar" and objeto not in (self.jugador.arma_equipada, self.jugador.armadura_equipada):
                return "Ese objeto no está equipado."
            if nombre == "apagar":
                if objeto.clase != "antorcha":return "Solo se pueden apagar antorchas."
                if not objeto.encendida:return "Esa antorcha ya está apagada."
            if nombre == "usar":
                return self._validar_uso(objeto)
            return None

        return None   # esperar

    def _validar_uso(self, objeto):
        if objeto.clase == "pocion":
            entrada = self.jugador.evento_mod_velocidad
            if objeto.modificador_velocidad and entrada is not None and entrada.valido:
                return "Ya hay un modificador de velocidad activo."
            nueva = self.jugador.velocidad + objeto.modificador_velocidad
            if objeto.modificador_velocidad and (type(nueva) is not int or nueva < 1):
                return "La poción no produce una velocidad entera positiva válida."
            return None
        if objeto.clase == "antorcha":
            if objeto.encendida:return "Esa antorcha ya está encendida."
            entrada = objeto.evento_apagado
            pendiente = entrada is not None and entrada.valido and entrada._en_heap
            if not pendiente and getattr(objeto, 'usos_restantes', 1) <= 0:
                return "Esa antorcha está agotada."
        if objeto.clase == "pergamino_retroceso":
            return "El pergamino se usa con P."
        if objeto.clase == "llave":
            return "Las llaves se usan al abrir una puerta (AB <dir>)."
        if objeto.clase in ("arma", "armadura"):
            return "Las armas y armaduras se equipan (EQ <n>)."
        if self.partida.aplicar_efecto is None:
            return f"El efecto de {objeto.nombre} todavía no está disponible."
        return None

    def _ejecutar(self, comando):
        """Aplica una acción ya validada. Devuelve su costo, o None si se anuló."""
        self.historial.iniciar_accion(self.reloj)
        try:
            self.reloj.tomar_turno(self.jugador)
            costo = self._aplicar(comando)
        except Exception:
            # Fallo inesperado: el modelo vuelve al estado previo a la acción.
            self.historial.abortar_accion()
            raise
        if costo is None:
            self.historial.abortar_accion()
            return None
        self.partida.contar_accion_jugador()
        if comando.nombre != "mover":
            # El rastro de la sala actual se refresca en cada acción.
            self.partida.refrescar_rastro()
        self._registrar_en_bitacora(comando.texto())
        return costo

    def _aplicar(self, comando):
        sala = self.jugador.sala_actual
        nombre, arg = comando.nombre, comando.argumento

        if nombre == "mover":
            destino = self.partida.cripta.sala_por_id(sala.salida_hacia(arg).sala_destino_id)
            self.partida.entrar_a_sala(destino)
            # Precarga desde la nueva posición (vecinas y vecinas de vecinas).
            self.red.planificar_precarga(destino)
            self.red.procesar_cola()
            return COSTO_MOVER

        if nombre == "atacar":
            self.partida.atacar(_elemento(sala.enemigos_activos, arg))
            return COSTO_ATACAR

        if nombre == "esperar":
            self.vista.agregar_mensaje(self.reloj.tiempo_actual, "Esperas.")
            return COSTO_ESPERAR

        if nombre == "recoger":
            objeto = _elemento(sala.objetos_suelo, arg)
            if not self.jugador.recoger(objeto):
                return None
            self.vista.agregar_mensaje(self.reloj.tiempo_actual, f"Recoges {objeto.nombre}.")
            return COSTO_RECOGER

        if nombre == "soltar":
            objeto = self.jugador.soltar_nodo(_nodo_inventario(self.jugador, arg))
            self.vista.agregar_mensaje(self.reloj.tiempo_actual, f"Sueltas {objeto.nombre}.")
            return COSTO_SOLTAR

        if nombre == "equipar":
            nodo = _nodo_inventario(self.jugador, arg)
            if not self.jugador.equipar_nodo(nodo):
                return None
            self.vista.agregar_mensaje(self.reloj.tiempo_actual, f"Equipas {nodo.valor.nombre}.")
            return COSTO_EQUIPAR

        if nombre == "desequipar":
            nodo = _nodo_inventario(self.jugador, arg)
            if not self.jugador.desequipar_nodo(nodo):return None
            self.vista.agregar_mensaje(self.reloj.tiempo_actual, f"Desequipas {nodo.valor.nombre}.")
            # Decisión de interfaz: quitar equipo tiene el mismo coste que ponerlo.
            return COSTO_EQUIPAR

        if nombre == "apagar":
            objeto = _nodo_inventario(self.jugador, arg).valor
            if not apagar_antorcha(self.reloj, objeto):return None
            self.vista.agregar_mensaje(self.reloj.tiempo_actual, f"Apagas {objeto.nombre}.")
            return COSTO_USAR

        if nombre == "usar":
            nodo = _nodo_inventario(self.jugador, arg)
            if not self.partida.usar_objeto(nodo):
                self._rechazar(f"No se pudo usar {nodo.valor.nombre}.")
                return None
            return COSTO_USAR

        if nombre == "abrir":
            self.partida.abrir(sala.salida_hacia(arg))
            return COSTO_ABRIR

        raise ValueError(f"Acción sin implementar: {nombre}")


    def _usar_pergamino(self):
        """Revierte la última acción: sin tiempo, sin registro en el historial.

        Se registra en la bitácora de partida porque cambia el estado (replay).
        """
        if self.partida.terminada:
            self._rechazar("No puedes usar un pergamino: la partida terminó.")
            return False
        nodo = None
        for actual in self.jugador.inventario.recorrer_desde_frente():
            if actual.valor.clase == "pergamino_retroceso":
                nodo = actual
                break
        if nodo is None:
            self._rechazar("No tienes pergaminos de retroceso.")
            return False
        momento = self.reloj.tiempo_actual   # la bitácora guarda cuándo se usó
        vivos_antes = self.red.ids_enemigos_vivos()
        if not self.historial.usar_pergamino(self.jugador, nodo):
            self._rechazar("No hay acciones que deshacer.")
            return False
        self.red.reconciliar_enemigos_revividos(vivos_antes)
        if self.bitacora is not None:
            self.bitacora.registrar(momento, "pergamino")
        self.sesion.acciones.agregarValor((momento, "pergamino"))
        self.vista.agregar_mensaje(
            self.reloj.tiempo_actual,
            "Lees el pergamino: el tiempo retrocede a antes de tu última acción.")
        return True

    def _mostrar_inventario(self, criterio):
        if criterio is None:
            objetos = Vector()
            for nodo in self.jugador.inventario.recorrer_desde_frente():
                objetos.agregarValor(nodo.valor)
        else:
            objetos = self.jugador.inventario_ordenado(criterio)
        self.vista.mostrar_inventario(self.partida, objetos, criterio)


    def _sincronizar_protegidas(self):
        """Actualiza las fichas protegidas según la posición y el inventario del jugador."""
        nuevas = Vector()
        for nodo in self.jugador.inventario.recorrer_desde_frente():
            nuevas.agregarValor(nodo.valor.tipo_id)
        for objeto in self.jugador.sala_actual.objetos_suelo:
            nuevas.agregarValor(objeto.tipo_id)
        for trampa in self.jugador.sala_actual.trampas:
            nuevas.agregarValor(trampa.tipo_id)
        # Primero se marcan las nuevas y luego se liberan las viejas: así una
        # ficha que sigue en uso nunca queda momentáneamente desprotegida.
        self.red.proteger_fichas(nuevas)
        self.red.liberar_fichas(self._protegidas)
        self._protegidas = nuevas

    def _registrar_en_bitacora(self, texto):
        self.sesion.acciones.agregarValor((self.reloj.tiempo_actual, texto))
        if self.bitacora is not None:
            self.bitacora.registrar(self.reloj.tiempo_actual, texto)

    def _persistir(self, comando):
        from controlador.guardado import guardar, cargar
        from bitacora_partida import BitacoraPartida
        from pathlib import Path
        import uuid
        ruta = comando.argumento or self.ruta_guardado
        try:
            if comando.nombre == 'guardar':
                leer_mensajes = getattr(self.vista, 'mensajes', None)
                mensajes = leer_mensajes() if callable(leer_mensajes) else None
                guardar(self.sesion, ruta, self._protegidas, mensajes)
                self.vista.agregar_mensaje(self.partida.tiempo, f'Partida guardada: {ruta}')
                return
            nueva = cargar(ruta, self.sesion)
            # Una carga abre otra rama de bitácora: nunca trunca el log anterior.
            if self.bitacora is not None:
                destino = Path(self.bitacora.ruta).with_name('carga_' + uuid.uuid4().hex + '.log')
                cabecera = dict(nueva.partida.encabezado())
                nueva.bitacora = BitacoraPartida.partida_nueva(str(destino), **cabecera)
                for tiempo, accion in nueva.acciones:
                    nueva.bitacora.registrar(tiempo, accion)
                self.bitacora.cerrar()
            self.red.cerrar(5)
            self.sesion, self.partida, self.red = nueva, nueva.partida, nueva.red
            self.bitacora = nueva.bitacora
            self.reloj, self.historial, self.jugador = (self.partida.reloj,
                                                       self.partida.historial,
                                                       self.partida.jugador)
            # El guardado incluye las referencias LRU protegidas de este punto.
            self._protegidas = nueva.protegidas if nueva.protegidas is not None else Vector()
            self.partida.al_mensaje.agregarValor(self.vista.agregar_mensaje)
            if nueva.mensajes_guardados is not None and hasattr(self.vista, 'restaurar_mensajes'):
                self.vista.restaurar_mensajes(nueva.mensajes_guardados)
            self.vista.agregar_mensaje(self.partida.tiempo, f'Partida cargada: {ruta}')
        except (OSError, ValueError, RuntimeError) as error:
            self._rechazar(f'No se pudo {comando.nombre}: {error}')

    def _cerrar(self, completa=True):
        """Fin de sesión: cierra el intervalo abierto, la bitácora y la red."""
        if self.historial.registrando:
            self.historial.confirmar_accion()
        if self.bitacora is not None and completa:
            self.bitacora.registrar_cierre(self.partida.tiempo, self.partida.estado,
                                           lineas_estado(self.partida))
        if self.bitacora is not None:
            self.bitacora.cerrar()
        self.red.cerrar(5)
        # Antes de mostrar_fin: la vista ya encuentra la tabla actualizada.
        if completa:
            self._registrar_puntaje()
        self.vista.mostrar_fin(self.partida)

    def _registrar_puntaje(self):
        """Agrega la partida terminada a la tabla. Un fallo de disco o un archivo
        dañado se informa sin interrumpir el cierre."""
        if self.tabla_puntajes is None or self._puntaje_intentado:
            return
        self._puntaje_intentado = True
        try:
            # self.sesion y no la del arranque: después de L es la sesión cargada.
            self.registro_puntaje = self.tabla_puntajes.registrar(self.sesion)
        except (OSError, ValueError) as error:
            self.error_puntaje = error
            self.vista.agregar_mensaje(self.partida.tiempo,
                                       f'No se pudo registrar el puntaje: {error}')
            return
        posicion = self.tabla_puntajes.posicion(self.registro_puntaje)
        self.vista.agregar_mensaje(
            self.partida.tiempo,
            f'Puntaje registrado: posición {posicion} de {len(self.tabla_puntajes)}')

    def contadores(self):
        return (("ciclos", self.contador_ciclos),
                ("turnos_jugador", self.contador_turnos_jugador),
                ("turnos_enemigo", self.contador_turnos_enemigo),
                ("efectos", self.contador_efectos),
                ("rechazos", self.contador_rechazos))
