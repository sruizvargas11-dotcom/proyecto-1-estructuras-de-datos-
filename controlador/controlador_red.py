import os
from math import isfinite

from modelo.mundo.cripta_modelo import CriptaModelo
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from modelo.entidades.enemigo import Enemigo
from modelo.entidades.trampa import Trampa
from modelo.entidades.objetos.fabrica_objetos import FabricaObjetos
from persistencia.esqueleto import PersistenciaEsqueleto
from persistencia.version import PersistenciaVersiones
from persistencia.contenido import PersistenciaContenido
from persistencia.catalogo import PersistenciaCatalogo
from persistencia.cache_json import validar_identificador
from estructuras.lista_simple import ListaSimple
from estructuras.cola import Cola
from estructuras.array_ordenado import ArrayOrdenado
from estructuras.vector_dinamico import Vector
from estructuras.listalru import ListaLRU
from estructuras.ordenamientos import ordenar
from controlador.buffer_reordenamiento import BufferReordenamiento
from controlador.despacho_red import DespachoInmediato

def _exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(f"Datos de cripta inválidos: {mensaje}")


def _generales(fuente, cripta_id):
    d = fuente.datos_cripta(cripta_id)
    _exigir(isinstance(d, dict), 'datos generales deben ser un objeto')
    requeridos = ('id', 'version', 'salas_total', 'paginas', 'sala_inicial',
                  'sala_salida', 'llave_salida', 'presupuesto_solicitudes', 'inventario_max')
    _exigir(all(k in d for k in requeridos), 'faltan campos generales')
    _exigir(d['id'] == cripta_id, 'identificador distinto al solicitado')
    _exigir(isinstance(d['version'], str) and bool(d['version'].strip()), 'versión vacía')
    for campo in ('salas_total', 'paginas'):
        _exigir(type(d[campo]) is int and d[campo] > 0, f'{campo} debe ser entero positivo')
    _exigir(d['paginas'] <= d['salas_total'], 'más páginas que salas')
    for campo in ('sala_inicial', 'sala_salida'):
        _exigir(type(d[campo]) is int, f'{campo} debe ser entero')
    for campo in ('presupuesto_solicitudes', 'inventario_max'):
        _exigir(type(d[campo]) is int and d[campo] >= 0, f'{campo} inválido')
    _exigir(d['llave_salida'] is None or isinstance(d['llave_salida'], str), 'llave inválida')
    return d


def _construir(fuente, d):
    c = CriptaModelo(d['id'], d['version'], d['sala_inicial'], d['sala_salida'],
                     d['llave_salida'], d['presupuesto_solicitudes'], d['inventario_max'])
    for pagina in range(1, d['paginas'] + 1):
        respuesta = fuente.esqueleto_cripta(c.id, pagina)
        _exigir(isinstance(respuesta, dict), f'página {pagina} inválida')
        _exigir(type(respuesta.get('pagina')) is int and respuesta['pagina'] == pagina,
                'número de página inesperado')
        _exigir(type(respuesta.get('total_paginas')) is int
                and respuesta['total_paginas'] == d['paginas'], 'total de páginas cambió')
        salas = respuesta.get('salas')
        _exigir(isinstance(salas, list) and bool(salas), f'página {pagina} sin salas')
        for x in salas:
            _exigir(isinstance(x, dict), 'sala inválida')
            _exigir(type(x.get('id')) is int and isinstance(x.get('nombre'), str),
                    'ID o nombre de sala inválido')
            salidas = x.get('salidas')
            _exigir(isinstance(salidas, dict), 'salidas deben ser un objeto JSON')
            sala = Sala(x['id'], x['nombre'])
            # Orden canónico: la respuesta no determina el orden de las direcciones.
            _exigir(all(dir in ('N', 'S', 'E', 'O') for dir in salidas), 'dirección inválida')
            for direccion in ('O', 'E', 'S', 'N'):
                if direccion not in salidas:
                    continue
                s = salidas[direccion]
                _exigir(isinstance(s, dict) and type(s.get('sala')) is int, 'destino inválido')
                cerrada = s.get('cerrada', False)
                llave = s.get('llave')
                cierre = s.get('cierre_automatico')
                _exigir(type(cerrada) is bool, 'cerrada debe ser booleano')
                _exigir(llave is None or isinstance(llave, str), 'llave inválida')
                _exigir(cierre is None or (type(cierre) is int and cierre >= 0), 'cierre inválido')
                sala.salidas.insertar_al_inicio(Salida(direccion, s['sala'], cerrada, llave, cierre))
            c.agregar_sala(sala)
            _exigir(len(c) <= d['salas_total'], 'más salas que las declaradas')
    _exigir(len(c) == d['salas_total'], 'cantidad de salas incompleta')
    c.finalizar_carga()  # También rechaza IDs duplicados.
    _exigir(c.sala_por_id(c.sala_inicial_id) is not None, 'sala inicial inexistente')
    _exigir(c.sala_por_id(c.sala_salida_id) is not None, 'sala de salida inexistente')
    for sala in c.recorrer_salas():
        for salida in sala.salidas.recorrer_valores():
            _exigir(c.sala_por_id(salida.sala_destino_id) is not None, 'conexión a sala inexistente')
    version_final = fuente.version_cripta(c.id)
    _exigir(isinstance(version_final, dict) and version_final.get('version') == c.version,
            'la versión cambió durante la descarga; vuelva a intentar la carga')
    return c


def cargar_esqueleto_completo(fuente, cripta_id):
    """Devuelve un modelo completo desde la fuente, sin usar ni modificar caché."""
    return _construir(fuente, _generales(fuente, cripta_id))


def cargar_cripta(fuente, cripta_id, carpeta_cache=None):
    """Devuelve (modelo, desde_cache). Nunca publica una descarga parcial.

    Se consultan generales incluso con caché para conocer versión y presupuesto
    actuales. Con caché vigente no se piden páginas ni contenido de salas.
    """
    persistencia = PersistenciaEsqueleto(carpeta_cache)
    # Validar el identificador antes de pasarlo a la fuente o al sistema de archivos.
    validar_identificador(cripta_id)
    _exigir(isinstance(cripta_id, str) and bool(cripta_id.strip())
            and cripta_id not in ('.', '..') and not any(c in cripta_id for c in '/\\:'),
            'identificador inválido')
    versiones = PersistenciaVersiones(carpeta_cache)
    d = _generales(fuente, cripta_id)
    c = persistencia.cargar_esqueleto(cripta_id, d['version'])
    if c is not None and (
        len(c) == d['salas_total'] and c.sala_inicial_id == d['sala_inicial']
        and c.sala_salida_id == d['sala_salida'] and c.llave_salida == d['llave_salida']
        and c.presupuesto_solicitudes == d['presupuesto_solicitudes']
        and c.inventario_max == d['inventario_max']
    ):
        # Reparar el registro auxiliar si el guardado anterior terminó entre archivos.
        if versiones.version_cripta_local(c.id) != c.version:
            versiones.guardar_version_cripta(c.id, c.version)
        return c, True
    c = _construir(fuente, d)
    persistencia.guardar_esqueleto(c)
    versiones.guardar_version_cripta(c.id, c.version)
    return c, False


def _carpeta_cache_por_defecto():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(raiz, "partidas", "cache")


def _contiene(vector, valor):
    """Búsqueda lineal O(n) en un Vector propio (no se usa dict ni set)."""
    for elemento in vector:
        if elemento == valor:
            return True
    return False


def _comparar_registro(a, b):
    ka, kb = (a[0], a[1]), (b[0], b[1])
    return (ka > kb) - (ka < kb)


class _SolicitudContenido:
    """Un lote de hasta 10 salas decidido en un punto determinista del juego."""

    def __init__(self, sala_ids, origen):
        self.numero = None
        self.sala_ids = sala_ids        # Vector, en el orden del lote
        self.origen = origen            # 'precarga' | 'garantizar' | 'directa'
        self.datos_lote = Vector()      # pares (sala_id, datos | None)
        self.faltantes = []             # list solo como parámetro de la fuente
        self.error = None
        self.terminada = False
        self.incorporadas = 0

    def contiene(self, sala_id):
        return _contiene(self.sala_ids, sala_id)


class ControladorRed:
    """Coordina la carga de salas y fichas en un orden reproducible.

    El hilo principal decide qué salas necesita y reúne un lote de hasta 10.
    Cada lote recibe un número, incluso si su contenido está en disco, para
    que la caché no cambie el orden de incorporación. El despachador consulta
    la fuente y entrega el resultado al buffer.

    Las respuestas se incorporan por número de solicitud. En ese momento se
    resuelve el catálogo y se construyen las entidades, sin activar enemigos
    ni programar sus eventos. El catálogo de cada lote usa subsolicitudes
    como n.1 y n.2.

    La incorporación ocurre antes de una decisión del jugador, al garantizar
    la entrada a una sala y al terminar de procesar la cola. Así, la velocidad
    de la red no determina cuándo una respuesta cambia el modelo.
    """

    MAX_LOTE = 10
    REINTENTOS_CONTENIDO = 1          # reintentos extra al garantizar una sala
    ESPERA_MAXIMA_SEGUNDOS = 120.0    # tiempo real máximo esperando una respuesta

    def __init__(self, fuente, cripta, carpeta_cache=None, fabrica=None,
                 version_catalogo=None, cache_size = 25, despachador=None, completar_lotes=False):
        self._fuente = fuente
        self._completar_lotes = completar_lotes
        self._cripta = cripta
        self._cache = carpeta_cache if carpeta_cache is not None else _carpeta_cache_por_defecto()
        # Una fábrica propia para el contenido: sus ids dependen solo del orden de
        # número de las solicitudes (el botín de Partida usa otra fábrica).
        self._fabrica = fabrica if fabrica is not None else FabricaObjetos()
        # se pide a la fuente una sola vez y solo si hace falta consultar disco.
        self._version_catalogo = version_catalogo
        self._despachador = despachador if despachador is not None else DespachoInmediato()

        self._pendientes = Cola()
        self._encoladas = Vector()
        self._incorporadas = Vector()
        self._solicitadas = Vector()      # en vuelo o incorporadas: no se piden otra vez
        self._buffer = BufferReordenamiento()
        self._registro = Vector()         # (numero, sub, clase, ids, en_red)
        self._numero_en_curso = None      # solicitud de contenido que se incorpora
        self._sub_catalogo = 0
        self._fichas = ListaLRU(capacidad = cache_size)
        self._tipos_descubiertos = Vector()

        self._pers_contenido = PersistenciaContenido(self._cache, cripta.version)
        self._pers_catalogo = None

        self.ultimo_error = None

        self.contador_solicitudes_contenido = 0
        self.contador_solicitudes_catalogo = 0
        self.contador_salas_desde_disco = 0
        self.contador_salas_desde_red = 0
        self.contador_fichas_desde_disco = 0
        self.contador_fichas_desde_red = 0
        self.contador_precargas_fallidas = 0
        self.contador_esperas_bloqueantes = 0


    def contenido_cargado(self, sala_id):
        return _contiene(self._incorporadas, sala_id)

    def contenido_solicitado(self, sala_id):
        """True si la sala ya fue pedida o incorporada."""
        return _contiene(self._solicitadas, sala_id)

    def pendientes(self):
        return len(self._pendientes)

    def solicitudes_en_vuelo(self):
        return self._buffer.en_vuelo()

    def registro_solicitudes(self):
        """Copia ordenada por (numero, sub) de (numero, sub, clase, ids, en_red)."""
        copia = Vector()
        for entrada in self._registro:
            copia.agregarValor(entrada)
        ordenar(copia, _comparar_registro)
        return copia

    def ficha(self, tipo_id):
        """Ficha ya resuelta, o None. O(k) acotado por cache_size: busca en
        la ListaLRU sin recorrer todo el catálogo, solo lo que está en memoria."""
        return self._fichas.buscar(tipo_id)
    
    def notificar_muerte_enemigo(self, enemigo):
        self._fichas.desmarcar_en_uso(enemigo.tipo_id)

    def proteger_fichas(self, tipo_ids):
        """Marca en_uso las fichas de objetos/trampas de la sala actual e inventario."""
        self.resolver_catalogo(tipo_ids)
        for tipo_id in tipo_ids:
            try:
                self._fichas.marcar_en_uso(tipo_id)
            except KeyError:
                pass

    def liberar_fichas(self, tipo_ids):
        """Inverso de proteger_fichas; tolera fichas ya liberadas o desalojadas."""
        for tipo_id in tipo_ids:
            try:
                self._fichas.desmarcar_en_uso(tipo_id)
            except (KeyError, ValueError):
                pass

    def version_catalogo(self):
        """Versión vigente del catálogo como texto (bitácora y guardado)."""
        version = self._persistencia_catalogo().version
        if isinstance(version, dict):
            version = version.get("version")
        return version

    def tipos_descubiertos(self):
        """tipo_ids en el orden en que aparecieron en el contenido."""
        return self._tipos_descubiertos

    def contadores(self):
        """Devuelve las métricas sin modificar los contadores."""
        return (
            ("solicitudes_contenido", self.contador_solicitudes_contenido),
            ("solicitudes_catalogo", self.contador_solicitudes_catalogo),
            ("salas_desde_disco", self.contador_salas_desde_disco),
            ("salas_desde_red", self.contador_salas_desde_red),
            ("fichas_desde_disco", self.contador_fichas_desde_disco),
            ("fichas_desde_red", self.contador_fichas_desde_red),
            ("precargas_fallidas", self.contador_precargas_fallidas),
            ("esperas_bloqueantes", self.contador_esperas_bloqueantes),
        ) + self._buffer.contadores()

    def estadisticas_cache(self):
        """Cifras de la LRU de fichas para el reporte de red (no alteran su orden)."""
        lru = self._fichas
        return (("aciertos", lru.contador_aciertos),
                ("fallos", lru.contador_fallos),
                ("desalojos", lru.contador_desalojos),
                ("capacidad", lru._capacidad),
                ("en_memoria", len(lru)),
                ("salas_incorporadas", len(self._incorporadas)))

    def cerrar(self, tiempo_maximo=None):
        """Espera los hilos de red pendientes (al terminar la sesión)."""
        self._despachador.cerrar(tiempo_maximo)


    def planificar_precarga(self, sala_actual):
        """Encola vecinas directas y vecinas de vecinas no solicitadas. No envía."""
        nuevas = 0
        directas = Vector()

        for salida in sala_actual.salidas.recorrer_valores():
            vecina = self._destino(salida)
            directas.agregarValor(vecina)
            if self._encolar(vecina.id):
                nuevas += 1

        for vecina in directas:
            for salida in vecina.salidas.recorrer_valores():
                lejana = self._destino(salida)
                if lejana.id == sala_actual.id:
                    continue
                if self._encolar(lejana.id):
                    nuevas += 1

        return nuevas

    def procesar_cola(self):
        """Envía un lote (máx. 10) de la cola e incorpora lo que ya esté listo.

        Con DespachoInmediato devuelve las salas incorporadas de ese lote; con hilos
        puede devolver 0 y la incorporación ocurre en un punto fijo posterior.
        Un fallo de precarga no detiene el juego: queda en ultimo_error.
        """
        lote = Vector()
        self._completar_lote(lote)
        if len(lote) == 0:
            return 0
        self.ultimo_error = None
        try:
            self._enviar_lote(lote, "precarga")
        except (RuntimeError, ValueError, OSError) as error:
            self._fallo(lote, error)
            return 0
        return self.incorporar_listas()

    def solicitar_contenido_lote(self, sala_ids):
        """Carga hasta 10 salas y espera a que se incorporen.

        Devuelve cuántas salas de este lote se incorporaron.
        """
        if len(sala_ids) > self.MAX_LOTE:
            raise ValueError(f"Un lote admite como máximo {self.MAX_LOTE} salas.")

        # 1. Clasificar las salas pedidas:
        por_cargar = Vector()
        espera_hasta = 0
        for sala_id in sala_ids:
            self._validar_sala(sala_id)
            en_vuelo = self._solicitud_de(sala_id)
            if en_vuelo is not None:
                espera_hasta = max(espera_hasta, en_vuelo.numero)
            elif not self.contenido_solicitado(sala_id) and not _contiene(por_cargar, sala_id):
                por_cargar.agregarValor(sala_id)

        # Envía el lote con un único número de solicitud.
        propia = None
        if len(por_cargar) > 0:
            try:
                propia = self._enviar_lote(por_cargar, "directa")
            except (RuntimeError, ValueError, OSError) as error:
                self._fallo(por_cargar, error)
                raise
            espera_hasta = max(espera_hasta, propia.numero)

        # 4. Esperar (tiempo real) hasta el mayor número involucrado e incorporar
        #    en orden de número, incluidas las solicitudes anteriores pendientes.
        if espera_hasta:
            self._esperar_e_incorporar(espera_hasta)

        # 5. Resultado: 0 si todo ya estaba pedido o cargado
        if propia is None:
            return 0
        if propia.error is not None:
            raise propia.error
        return propia.incorporadas

    def garantizar_contenido(self, sala_id):
        """Bloqueante: devuelve la sala con su contenido ya incorporado.

        Si la sala está en vuelo espera esa respuesta (y las anteriores); si no fue
        pedida arma un lote con ella primero y lo completa con la cola. Reintenta
        dentro del presupuesto; si aun así falla re-lanza el error original.
        Esperar es tiempo real: el reloj virtual no se toca aquí.
        """
        sala = self._validar_sala(sala_id)
        self.incorporar_listas()
        intentos = 0
        while not self.contenido_cargado(sala_id):
            solicitud = self._solicitud_de(sala_id)
            if solicitud is None:
                lote = Vector()
                lote.agregarValor(sala_id)
                self._completar_lote(lote)
                try:
                    solicitud = self._enviar_lote(lote, "garantizar")
                except (RuntimeError, ValueError, OSError) as error:
                    self._fallo(lote, error)
                    raise
            else:
                self.contador_esperas_bloqueantes += 1
            self._esperar_e_incorporar(solicitud.numero)
            if self.contenido_cargado(sala_id):
                break
            error = solicitud.error
            if error is None:
                continue  # la sala viajaba en otra solicitud ya resuelta
            if not self._puede_reintentar(error, intentos):
                raise error
            intentos += 1
        return sala

    def asegurar_entrada(self, sala_id):
        """Para el movimiento del jugador hacia una sala."""
        try:
            self.garantizar_contenido(sala_id)
            return None #devuelve None si el contenido quedó disponible
        except (RuntimeError, ValueError, OSError) as error:
            return f"No se puede entrar a la sala {sala_id}: su contenido no está disponible ({error})."

    def incorporar_listas(self):
        """Incorpora las respuestas disponibles respetando el orden de solicitud."""
        total = 0
        while True:
            tomada = self._buffer.tomar_siguiente()
            if tomada is None:
                return total
            solicitud, respuesta, error = tomada
            if solicitud is None:      # ranura de un catálogo ya resuelto
                continue
            try:
                if error is not None:
                    raise error
                total += self._completar_solicitud(solicitud, respuesta)
            except (RuntimeError, ValueError, OSError) as fallo:
                self._fallo(solicitud.sala_ids, fallo, solicitud)
            solicitud.terminada = True

    def esperar_todas(self):
        """Espera e incorpora todo lo que está en vuelo (replay, bench, guardar).
        Devuelve cuántas salas incorporó. Tiempo real; el reloj virtual no cambia.
        """
        if self._buffer.en_vuelo() == 0:
            return self.incorporar_listas()
        antes = len(self._incorporadas)
        self._esperar_e_incorporar(self._buffer.proximo_numero - 1)
        return len(self._incorporadas) - antes

    def resolver_catalogo(self, tipo_ids):
        """Asegura en memoria las fichas: LRU -> disco -> red (lotes de 10)"""
        sin_memoria = Vector()
        for tipo_id in tipo_ids:
            validar_identificador(tipo_id)
            if self.ficha(tipo_id) is None and not _contiene(sin_memoria, tipo_id):
                sin_memoria.agregarValor(tipo_id)
        if len(sin_memoria) == 0:
            return 0

        pers = self._persistencia_catalogo()
        a_red = [] # list solo como parámetro del contrato de la fuente
        for tipo_id in sin_memoria:
            ficha = pers.cargar_ficha(tipo_id)
            if ficha is not None:
                try:
                    self._validar_ficha(tipo_id, ficha)
                except ValueError:
                    ficha = None
            if ficha is not None:
                self.contador_fichas_desde_disco += 1
                self._fichas.insertar(tipo_id, ficha)
            else:
                a_red.append(tipo_id)

        inicio = 0
        while inicio < len(a_red):
            lote = a_red[inicio:inicio + self.MAX_LOTE]
            self._anotar_catalogo(lote)
            respuesta = self._fuente.catalogo(lote)
            self.contador_solicitudes_catalogo += 1
            self.contador_fichas_desde_red += len(lote)
            for tipo_id in lote:
                ficha = self._buscar_ficha_en_respuesta(respuesta, tipo_id)
                pers.guardar_ficha(tipo_id, ficha)
                self._fichas.insertar(tipo_id, ficha)
            inicio += self.MAX_LOTE

        return len(a_red)


    def _validar_sala(self, sala_id):
        if type(sala_id) is not int or sala_id < 0:
            raise ValueError("El identificador de sala debe ser un entero no negativo.")
        sala = self._cripta.sala_por_id(sala_id)
        if sala is None:
            raise ValueError(f"La sala {sala_id} no existe en la cripta.")
        return sala

    def _solicitud_de(self, sala_id):
        """Solicitud en vuelo que contiene la sala, o None."""
        for solicitud in self._buffer.pendientes():
            if solicitud.contiene(sala_id):
                return solicitud
        return None

    def _enviar_lote(self, sala_ids, origen):
        """Pasos 1-3: lee disco, numera, anota y envía. Devuelve la solicitud."""
        solicitud = _SolicitudContenido(sala_ids, origen)
        for sala_id in sala_ids:
            datos = self._pers_contenido.cargar(self._cripta.id, sala_id)
            if datos is not None:
                try:
                    self._validar_contenido(sala_id, datos)
                except ValueError:
                    datos = None  # Una copia dañada se recupera desde la fuente.
            if datos is None:
                solicitud.faltantes.append(sala_id)
            solicitud.datos_lote.agregarValor((sala_id, datos))

        numero = self._buffer.reservar(solicitud)
        solicitud.numero = numero
        for sala_id in sala_ids:
            if not _contiene(self._solicitadas, sala_id):
                self._solicitadas.agregarValor(sala_id)
        en_red = len(solicitud.faltantes) > 0
        self._registro.agregarValor((numero, 0, "contenido", tuple(sala_ids), en_red))

        if not en_red:
            self._buffer.entregar(numero)
            return solicitud
        self.contador_solicitudes_contenido += 1
        faltantes = list(solicitud.faltantes)
        cripta_id = self._cripta.id
        fuente = self._fuente
        buffer = self._buffer
        self._despachador.enviar(
            lambda: fuente.contenido_salas(cripta_id, faltantes),
            lambda respuesta, error: buffer.entregar(numero, respuesta, error))
        return solicitud

    def _esperar_e_incorporar(self, numero):
        """Espera en tiempo real a que lleguen todas las respuestas <= numero."""
        if not self._buffer.esperar(numero, self.ESPERA_MAXIMA_SEGUNDOS):
            self._buffer.abandonar_hasta(numero, RuntimeError(
                "La fuente de datos no respondió a tiempo."))
        self.incorporar_listas()

    def _completar_solicitud(self, solicitud, respuesta):
        """Incorpora una solicitud completa cuando le corresponde su turno."""
        datos_lote = solicitud.datos_lote
        for indice, (sala_id, datos) in enumerate(datos_lote):
            if datos is None:
                datos_lote.asignarValor(indice, (sala_id, self._buscar_en_respuesta(respuesta, sala_id)))
                self.contador_salas_desde_red += 1
            else:
                self.contador_salas_desde_disco += 1

        self._numero_en_curso, self._sub_catalogo = solicitud.numero, 0
        try:
            # Todas las fichas del lote se resuelven juntas: menos solicitudes.
            self.resolver_catalogo(self._descubrir_tipos(datos_lote))
            preparadas = self._preparar(datos_lote, solicitud.faltantes)
            for sala, (enemigos, objetos, trampas) in preparadas:
                sala.enemigos_dormidos = enemigos
                sala.objetos_suelo = objetos
                sala.trampas = trampas
                self._incorporadas.agregarValor(sala.id)
                self._marcar_enemigos_en_uso(enemigos)
            solicitud.incorporadas = len(preparadas)
            self._resolver_botin(preparadas)
        finally:
            self._numero_en_curso = None
        return solicitud.incorporadas

    def _preparar(self, datos_lote, faltantes):
        """Construye las entidades del lote sin publicarlas; si algo falla, no gasta ids."""
        preparadas = Vector()
        siguiente_id = self._fabrica.siguiente_id
        try:
            for sala_id, datos in datos_lote:
                sala = self._cripta.sala_por_id(sala_id)
                try:
                    preparadas.agregarValor((sala, self._incorporar(sala, datos)))
                except ValueError:
                    if sala_id not in faltantes:
                        self._pers_contenido.invalidar(self._cripta.id, sala_id)
                    raise
            # Solo se persisten contenidos que pudieron construirse por completo.
            for sala_id, datos in datos_lote:
                if sala_id in faltantes:
                    self._pers_contenido.guardar(self._cripta.id, sala_id, datos)
        except Exception:
            self._fabrica.siguiente_id = siguiente_id
            raise
        return preparadas

    def _marcar_enemigos_en_uso(self, enemigos):
        # Un enemigo vivo protege su ficha sin importar la sala
        for enemigo in enemigos:
            self._fichas.marcar_en_uso(enemigo.tipo_id)

    def _resolver_botin(self, preparadas):
        """Deja en memoria/disco las fichas de 'suelta' de los enemigos del lote."""
        tipos = Vector()
        for _, (enemigos, _, _) in preparadas:
            for enemigo in enemigos:
                for tipo_id in enemigo.suelta:
                    if not _contiene(tipos, tipo_id):
                        tipos.agregarValor(tipo_id)
        if len(tipos) == 0:
            return
        try:
            self.resolver_catalogo(tipos)
        except (RuntimeError, ValueError, OSError) as error:
            self.ultimo_error = f"Botín {self._texto_ids(tipos)}: {error}"

    def _anotar_catalogo(self, lote):
        if self._numero_en_curso is not None:
            self._sub_catalogo += 1
            numero, sub = self._numero_en_curso, self._sub_catalogo
        else:
            # Catálogo fuera de una incorporación (p. ej. botín): número propio. Se
            # resuelve en el acto; su ranura vacía solo conserva la numeración.
            numero, sub = self._buffer.reservar(None), 0
            self._buffer.entregar(numero)
        self._registro.agregarValor((numero, sub, "catalogo", tuple(lote), True))

    def _fallo(self, sala_ids, error, solicitud=None):
        """Reencola las salas afectadas y conserva el error para informar del fallo."""
        for sala_id in sala_ids:
            for indice, solicitada in enumerate(self._solicitadas):
                if solicitada == sala_id:
                    self._solicitadas.eliminar(indice)
                    break
        self._restaurar_lote(sala_ids)
        if solicitud is not None:
            solicitud.error = error
            if solicitud.origen == "precarga":
                self.contador_precargas_fallidas += 1
        self.ultimo_error = f"Salas {self._texto_ids(sala_ids)}: {error}"

    def _puede_reintentar(self, error, intentos):
        if intentos >= self.REINTENTOS_CONTENIDO or isinstance(error, ValueError):
            return False
        dentro = getattr(self._fuente, "dentro_del_presupuesto", None)
        return dentro is None or dentro()

    def _destino(self, salida):
        destino = salida.sala_destino
        if destino is None:
            destino = self._cripta.sala_por_id(salida.sala_destino_id)
        if destino is None:
            raise ValueError(f"La salida apunta a la sala inexistente {salida.sala_destino_id}.")
        return destino

    def _encolar(self, sala_id):
        if _contiene(self._encoladas, sala_id) or self.contenido_solicitado(sala_id):
            return False
        self._pendientes.encolar(sala_id)
        self._encoladas.agregarValor(sala_id)
        return True

    def _restaurar_lote(self, lote):
        """Reencola solamente salas pendientes que no estaban ya en la cola."""
        for sala_id in lote:
            self._encolar(sala_id)

    def _completar_lote(self, lote):
        """Saca de la cola hasta llenar el lote; salta las ya cargadas."""
        while len(lote) < self.MAX_LOTE and not self._pendientes.esta_vacia():
            sala_id = self._pendientes.desencolar()
            for indice, encolada in enumerate(self._encoladas):
                if encolada == sala_id:
                    self._encoladas.eliminar(indice)
                    break
            if self.contenido_solicitado(sala_id) or _contiene(lote, sala_id):
                continue
            lote.agregarValor(sala_id)
        if self._completar_lotes and 0 < len(lote) < self.MAX_LOTE:
            self._rellenar_cercanas(lote)

    def _rellenar_cercanas(self, lote):
        """Aprovecha el mismo envío con salas cercanas, hasta MAX_LOTE.

        BFS conserva el orden de las salidas; nunca depende del orden HTTP.
        La opción se activa al montar una partida. Desactivada permite medir
        la estrategia anterior de solo dos niveles con el mismo controlador.
        """
        frontera = Cola()
        vistas = ArrayOrdenado()
        for sala_id in lote:
            vistas.insertar(sala_id, True)
            frontera.encolar(self._cripta.sala_por_id(sala_id))
        while not frontera.esta_vacia() and len(lote) < self.MAX_LOTE:
            sala = frontera.desencolar()
            for salida in sala.salidas.recorrer_valores():
                destino = self._destino(salida)
                if vistas.busqueda_binaria(destino.id) is not None:
                    continue
                vistas.insertar(destino.id, True)
                frontera.encolar(destino)
                if not self.contenido_solicitado(destino.id):
                    lote.agregarValor(destino.id)
                    if len(lote) == self.MAX_LOTE:
                        break

    def _persistencia_catalogo(self):
        if self._pers_catalogo is None:
            if self._version_catalogo is None:
                # una sola solicitud por partida, y solo si hay fichas que buscar.
                self._version_catalogo = self._fuente.version_catalogo()
            self._pers_catalogo = PersistenciaCatalogo(self._cache, self._version_catalogo)
        return self._pers_catalogo

    def _descubrir_tipos(self, datos_lote):
        """tipo_ids que aparecen en el lote, sin repetir, en orden de aparición."""
        tipos = Vector()
        for _, datos in datos_lote:
            for enemigo in datos["enemigos"]:
                self._anotar_tipo(tipos, enemigo["tipo"])
            for tipo_id in datos["objetos"]:
                self._anotar_tipo(tipos, tipo_id)
            for trampa in datos["trampas"]:
                self._anotar_tipo(tipos, trampa["tipo"])
        return tipos

    def _anotar_tipo(self, tipos, tipo_id):
        if not isinstance(tipo_id, str) or not tipo_id:
            raise ValueError("Contenido inválido: tipo de entidad vacío.")
        if not _contiene(tipos, tipo_id):
            tipos.agregarValor(tipo_id)
        if not _contiene(self._tipos_descubiertos, tipo_id):
            self._tipos_descubiertos.agregarValor(tipo_id)

    def _incorporar(self, sala, datos):
        """Prepara las entidades sin publicar cambios ni activar eventos."""
        enemigos = ListaSimple()
        objetos = ListaSimple()
        trampas = ListaSimple()
        for e in datos["enemigos"]:
            ficha = self._ficha_de_clase(e["tipo"], ("enemigo",))
            enemigo = Enemigo.desde_ficha(e["instancia"], ficha, sala, e.get("vida"))
            enemigos.insertar_al_final(enemigo)
            # en_uso se marca al publicar el lote (_marcar_enemigos_en_uso), así un
            # lote que falla a medias no deja fichas protegidas para siempre.

        for tipo_id in datos["objetos"]:
            ficha = self._ficha_de_clase(tipo_id, None)
            objetos.insertar_al_final(self._fabrica.crear(ficha))
            # Los objetos quedan protegidos al estar en el inventario o en el suelo de
            # la sala actual. ControladorJuego actualiza esas referencias al moverse.

        for t in datos["trampas"]:
            ficha = self._ficha_de_clase(t["tipo"], ("trampa",))
            trampas.insertar_al_final(Trampa.desde_ficha(t["instancia"], ficha))
            # Misma razón que los objetos: solo protege si es la sala actual.
        return enemigos, objetos, trampas

    def _ficha_de_clase(self, tipo_id, clases):
        ficha = self.ficha(tipo_id)
        if ficha is None:
            raise RuntimeError(f"La ficha {tipo_id} no se resolvió antes de incorporar.")
        clase = ficha.get("clase")
        if clases is None:
            if clase in ("enemigo", "trampa"):
                raise ValueError(f"{tipo_id} es '{clase}', no un objeto.")
        elif clase not in clases:
            raise ValueError(f"{tipo_id} es '{clase}', se esperaba {clases[0]}.")
        return ficha

    def _buscar_en_respuesta(self, respuesta, sala_id):
        contenido = respuesta.get("contenido") if isinstance(respuesta, dict) else None
        if not isinstance(contenido, list):
            raise ValueError("Respuesta de contenido inválida.")
        encontrada = None
        for datos in contenido:
            if isinstance(datos, dict) and datos.get("sala") == sala_id:
                if encontrada is not None:
                    raise ValueError(f"La respuesta repite la sala {sala_id}.")
                self._validar_contenido(sala_id, datos)
                encontrada = datos
        if encontrada is None:
            raise ValueError(f"La respuesta no trajo el contenido de la sala {sala_id}.")
        return encontrada

    @staticmethod
    def _validar_contenido(sala_id, datos):
        if (not isinstance(datos, dict) or type(datos.get('sala')) is not int
                or datos['sala'] != sala_id):
            raise ValueError(f"Contenido de la sala {sala_id} inválido.")
        for campo in ("enemigos", "objetos", "trampas"):
            if not isinstance(datos.get(campo), list):
                raise ValueError(f"Contenido de la sala {sala_id}: '{campo}' inválido.")
        instancias = Vector()
        for entidad in datos["enemigos"] + datos["trampas"]:
            if (not isinstance(entidad, dict)
                    or not isinstance(entidad.get("instancia"), str)
                    or not entidad['instancia'].strip()):
                raise ValueError(f"Contenido de la sala {sala_id}: instancia inválida.")
            if _contiene(instancias, entidad['instancia']):
                raise ValueError('Instancia repetida en el contenido de una sala.')
            instancias.agregarValor(entidad['instancia'])
            validar_identificador(entidad.get('tipo'))
            vida = entidad.get('vida')
            if vida is not None and (type(vida) not in (int, float)
                                     or not isfinite(vida) or vida < 0):
                raise ValueError('Vida de instancia inválida.')
        for tipo_id in datos['objetos']:
            validar_identificador(tipo_id)

    def _validar_ficha(self, tipo_id, ficha):
        if not isinstance(ficha, dict) or ficha.get('id') != tipo_id:
            raise ValueError(f'Ficha {tipo_id} inválida.')
        if not isinstance(ficha.get('nombre'), str) or not ficha['nombre'].strip():
            raise ValueError(f'Ficha {tipo_id}: nombre inválido.')
        siguiente_id = self._fabrica.siguiente_id
        try:
            clase = ficha.get('clase')
            if clase == 'enemigo':
                Enemigo.desde_ficha('validacion', ficha)
                suelta = ficha.get('suelta', [])
                if not isinstance(suelta, list):
                    raise ValueError('suelta debe ser una lista de tipos.')
                for tipo in suelta:
                    validar_identificador(tipo)
                regeneracion = ficha.get('regeneracion', 0)
                if (type(regeneracion) not in (int, float)
                        or not isfinite(regeneracion) or regeneracion < 0):
                    raise ValueError('Regeneración inválida.')
            elif clase == 'trampa':
                Trampa.desde_ficha('validacion', ficha)
            else:
                self._fabrica.crear(ficha)
        except (KeyError, TypeError) as error:
            raise ValueError(f'Ficha {tipo_id} incompleta o inválida: {error}') from error
        finally:
            # Validar una ficha no consume identificadores de la partida.
            self._fabrica.siguiente_id = siguiente_id

    def _buscar_ficha_en_respuesta(self, respuesta, tipo_id):
        entidades = respuesta.get("entidades") if isinstance(respuesta, dict) else None
        if not isinstance(entidades, list):
            raise ValueError("Respuesta de catálogo inválida.")
        encontrada = None
        for ficha in entidades:
            if isinstance(ficha, dict) and ficha.get("id") == tipo_id:
                if encontrada is not None:
                    raise ValueError(f'El catálogo repite la ficha {tipo_id}.')
                self._validar_ficha(tipo_id, ficha)
                encontrada = ficha
        if encontrada is None:
            raise ValueError(f"El catálogo no trajo la ficha {tipo_id}.")
        return encontrada

    @staticmethod
    def _texto_ids(ids):
        return ", ".join(str(i) for i in ids)
