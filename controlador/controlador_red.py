"""Carga desde la red o el disco. La fuente decide si los datos vienen de HTTP o de archivos.

Bloque 1: carga inicial del esqueleto (cargar_cripta).
Bloque 2: precarga y carga de contenido y catálogo (ControladorRed).
"""
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
from estructuras.vector_dinamico import Vector
from estructuras.array_ordenado import ArrayOrdenado

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


class ControladorRed:

    MAX_LOTE = 10

    def __init__(self, fuente, cripta, carpeta_cache=None, fabrica=None,
                 version_catalogo=None):
        self._fuente = fuente
        self._cripta = cripta
        self._cache = carpeta_cache if carpeta_cache is not None else _carpeta_cache_por_defecto()
        # debe existir una sola fábrica por partida (ver FabricaObjetos).
        self._fabrica = fabrica if fabrica is not None else FabricaObjetos()
        # se pide a la fuente una sola vez y solo si hace falta consultar disco.
        self._version_catalogo = version_catalogo

        self._pendientes = Cola()
        self._encoladas = Vector()
        self._incorporadas = Vector()
        self._fichas = ArrayOrdenado()
        self._tipos_descubiertos = Vector()

        self._pers_contenido = PersistenciaContenido(self._cache, cripta.version)
        self._pers_catalogo = None

        self.ultimo_error = None

        self.contador_solicitudes_contenido = 0
        self.contador_solicitudes_catalogo = 0
        self.contador_salas_desde_disco = 0
        self.contador_fichas_desde_disco = 0
        self.contador_precargas_fallidas = 0


    def contenido_cargado(self, sala_id):
        return _contiene(self._incorporadas, sala_id)

    def pendientes(self):
        return len(self._pendientes)

    def ficha(self, tipo_id):
        """Ficha ya resuelta, o None. O(log n)."""
        return self._fichas.busqueda_binaria(tipo_id)

    def tipos_descubiertos(self):
        """tipo_ids en el orden en que aparecieron en el contenido."""
        return self._tipos_descubiertos

    def contadores(self):
        """Devuelve las métricas sin modificar los contadores."""
        return (
            ("solicitudes_contenido", self.contador_solicitudes_contenido),
            ("solicitudes_catalogo", self.contador_solicitudes_catalogo),
            ("salas_desde_disco", self.contador_salas_desde_disco),
            ("fichas_desde_disco", self.contador_fichas_desde_disco),
            ("precargas_fallidas", self.contador_precargas_fallidas),
        )


    def planificar_precarga(self, sala_actual):

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

        lote = Vector()
        self._completar_lote(lote)
        if len(lote) == 0:
            return 0
        self.ultimo_error = None
        try:
            return self.solicitar_contenido_lote(lote)
        except (RuntimeError, ValueError, OSError) as error:
            self.ultimo_error = f"Precarga de salas {self._texto_ids(lote)}: {error}"
            self.contador_precargas_fallidas += 1
            return 0


    def solicitar_contenido_lote(self, sala_ids):
        """
        Carga el contenido de hasta 10 salas y lo incorpora al modelo:
          1. Las salas ya incorporadas se omiten.
          2. Las que están en disco con la versión vigente no generan request.
          3. Las demás se piden en UNA sola solicitud.
          4. Se descubren los tipo_ids nuevos y se resuelven en lotes.
          5. Se pueblan enemigos_dormidos, objetos_suelo y trampas.
        Devuelve cuántas salas se incorporaron.
        """
        if len(sala_ids) > self.MAX_LOTE:
            raise ValueError(f"Un lote admite como máximo {self.MAX_LOTE} salas.")

        por_cargar = Vector()
        for sala_id in sala_ids:
            if type(sala_id) is not int or sala_id < 0:
                raise ValueError("El identificador de sala debe ser un entero no negativo.")
            if self._cripta.sala_por_id(sala_id) is None:
                raise ValueError(f"La sala {sala_id} no existe en la cripta.")
            if not self.contenido_cargado(sala_id) and not _contiene(por_cargar, sala_id):
                por_cargar.agregarValor(sala_id)
        if len(por_cargar) == 0:
            return 0
        try:
            return self._cargar_lote(por_cargar)
        except Exception:
            # También protege las llamadas directas, no solo la precarga.
            self._restaurar_lote(por_cargar)
            raise

    def _cargar_lote(self, por_cargar):
        datos_lote = Vector()     # pares (sala_id, datos) en el orden del lote
        faltantes = []            # list solo como parámetro del contrato de la fuente
        for sala_id in por_cargar:
            datos = self._pers_contenido.cargar(self._cripta.id, sala_id)
            if datos is not None:
                try:
                    self._validar_contenido(sala_id, datos)
                except ValueError:
                    datos = None  # Una copia dañada se recupera desde la fuente.
            if datos is None:
                faltantes.append(sala_id)
            else:
                self.contador_salas_desde_disco += 1
            datos_lote.agregarValor((sala_id, datos))

        if faltantes:
            respuesta = self._fuente.contenido_salas(self._cripta.id, faltantes)
            self.contador_solicitudes_contenido += 1
            # Completar en el orden solicitado, no en el orden de red/disco.
            for indice, (sala_id, datos) in enumerate(datos_lote):
                if datos is None:
                    datos = self._buscar_en_respuesta(respuesta, sala_id)
                    datos_lote.asignarValor(indice, (sala_id, datos))

        # Todas las fichas del lote se resuelven juntas: menos solicitudes.
        self.resolver_catalogo(self._descubrir_tipos(datos_lote))
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
        for sala, (enemigos, objetos, trampas) in preparadas:
            sala.enemigos_dormidos = enemigos
            sala.objetos_suelo = objetos
            sala.trampas = trampas
            self._incorporadas.agregarValor(sala.id)
        return len(preparadas)

    def garantizar_contenido(self, sala_id):
        if type(sala_id) is not int or sala_id < 0:
            raise ValueError("El identificador de sala debe ser un entero no negativo.")
        sala = self._cripta.sala_por_id(sala_id)
        if sala is None:
            raise ValueError(f"La sala {sala_id} no existe en la cripta.")
        if self.contenido_cargado(sala_id):
            return sala

        lote = Vector()
        lote.agregarValor(sala_id)
        self._completar_lote(lote)
        self.solicitar_contenido_lote(lote)
        return sala


    def resolver_catalogo(self, tipo_ids):

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
            respuesta = self._fuente.catalogo(lote)
            self.contador_solicitudes_catalogo += 1
            for tipo_id in lote:
                ficha = self._buscar_ficha_en_respuesta(respuesta, tipo_id)
                pers.guardar_ficha(tipo_id, ficha)
                self._fichas.insertar(tipo_id, ficha)
            inicio += self.MAX_LOTE

        return len(a_red)


    def _destino(self, salida):
        destino = salida.sala_destino
        if destino is None:
            destino = self._cripta.sala_por_id(salida.sala_destino_id)
        if destino is None:
            raise ValueError(f"La salida apunta a la sala inexistente {salida.sala_destino_id}.")
        return destino

    def _encolar(self, sala_id):
        if _contiene(self._encoladas, sala_id) or self.contenido_cargado(sala_id):
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
            if self.contenido_cargado(sala_id) or _contiene(lote, sala_id):
                continue
            lote.agregarValor(sala_id)

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

        for tipo_id in datos["objetos"]:
            ficha = self._ficha_de_clase(tipo_id, None)
            objetos.insertar_al_final(self._fabrica.crear(ficha))

        for t in datos["trampas"]:
            ficha = self._ficha_de_clase(t["tipo"], ("trampa",))
            trampas.insertar_al_final(Trampa.desde_ficha(t["instancia"], ficha))
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
