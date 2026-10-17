"""Une la sesión de juego con el formato binario, fuera de la vista/modelo."""
import os
import tempfile

from controlador.inicio_partida import SesionPartida, _resolvedor_fichas
from controlador.controlador_red import ControladorRed
from controlador.despacho_red import DespachoEnHilos
from modelo import efectos
from persistencia.PartidaBinaria import PartidaBinaria, ErrorFormatoBinario
from persistencia.estado_partida import codificar, decodificar
from estructuras.array_ordenado import ArrayOrdenado
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar

CAMPOS_RED = ('_incorporadas', '_solicitadas', '_pendientes', '_encoladas',
              '_fabrica', '_fichas', '_tipos_descubiertos', '_registro')

# 1: esquema original. 2: agrega 'nombre_jugador' (§2.12, §4.10) — un guardado
# con esquema 1 ya no es compatible, para no cargar una partida sin ese dato.
ESQUEMA_ESTADO = 2


def _comparar_registros(a, b):
    return (a['id'] > b['id']) - (a['id'] < b['id'])


def _datos_entidad(entidad):
    """Datos de una entidad y sus eventos, sin recorrer el resto del mundo."""
    datos = {k: v for k, v in vars(entidad).items()
             if v is None or type(v) in (str, int, float, bool)}
    for campo in ('evento_actual', 'evento_veneno', 'evento_mod_velocidad',
                  'evento_regeneracion', 'evento_rearme', 'evento_apagado', 'evento_cierre'):
        entrada = getattr(entidad, campo, None)
        if entrada is not None and entrada.valido:
            datos[campo] = {'tiempo': entrada.tiempo, 'secuencia': entrada.secuencia}
    veneno = getattr(entidad, 'estado_veneno', None)
    if veneno is not None:
        datos['estado_veneno'] = {'dano_por_pulso': veneno.dano_por_pulso,
                                  'pulsos_restantes': veneno.pulsos_restantes}
    if hasattr(entidad, 'suelta'):
        datos['suelta'] = list(entidad.suelta)
    return datos


def _estado_sala(sala):
    return {'salidas': [_datos_entidad(x) for x in sala.salidas],
            'enemigos_activos': [_datos_entidad(x) for x in sala.enemigos_activos],
            'enemigos_dormidos': [_datos_entidad(x) for x in sala.enemigos_dormidos],
            'objetos_suelo': [_datos_entidad(x) for x in sala.objetos_suelo],
            'trampas': [_datos_entidad(x) for x in sala.trampas]}


def guardar(sesion, ruta, protegidas=None, mensajes=None):
    sesion.red.esperar_todas()
    if sesion.red.solicitudes_en_vuelo():
        raise ValueError('Todavía hay solicitudes pendientes; reintenta guardar.')
    partida = sesion.partida
    if partida.historial.registrando:
        raise ValueError('Solo se guarda entre decisiones del jugador.')
    referencia, registros = codificar({
        'partida': partida,
        'red': {k: getattr(sesion.red, k) for k in CAMPOS_RED},
        'numero_solicitud': sesion.red._buffer.proximo_numero,
        'acciones': sesion.acciones,
        'protegidas': protegidas,
        'mensajes': mensajes,
    })
    globales = dict(partida.encabezado())
    globales.update(esquema_estado=ESQUEMA_ESTADO, nombre_jugador=sesion.nombre_jugador,
                    raiz=referencia, registros=[], salas=[])
    grupos = ArrayOrdenado()
    for registro in registros:
        grupo = registro['grupo']
        if grupo is None:
            globales['registros'].append(registro)
        else:
            bloque = grupos.busqueda_binaria(grupo)
            if bloque is None:
                bloque = []
                grupos.insertar(grupo, bloque)
            bloque.append(registro)
    salas = []
    for sala in partida.cripta.recorrer_salas():
        globales['salas'].append(sala.id)
        salas.append((sala.id, {'id': sala.id, 'nombre': sala.nombre,
                                'tiempo_rastro': sala.tiempo_rastro,
                                'estado': _estado_sala(sala),
                                'registros': grupos.busqueda_binaria(sala.id) or []}))
    carpeta = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(carpeta, exist_ok=True)
    fd, temporal = tempfile.mkstemp(prefix='.cripta-', suffix='.tmp', dir=carpeta)
    os.close(fd)
    try:
        PartidaBinaria(temporal).guardar(globales, salas)
        os.replace(temporal, ruta)
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)


def cargar(ruta, sesion_actual):
    """Construye y valida una sesión nueva antes de sustituir la sesión en curso."""
    try:
        archivo = PartidaBinaria(ruta)
        datos = archivo.cargar_global()
        if datos.get('esquema_estado') != ESQUEMA_ESTADO:
            raise ValueError(
                f"Guardado incompatible: esquema de estado {datos.get('esquema_estado')!r}, "
                f"se esperaba {ESQUEMA_ESTADO}. Un guardado de una versión anterior del "
                "programa no se puede cargar.")
        actual = dict(sesion_actual.partida.encabezado())
        for campo in ('cripta_id', 'version_cripta', 'version_catalogo'):
            if datos.get(campo) != actual[campo]:
                raise ValueError(f'Guardado incompatible: {campo}.')
        registros = datos['registros']
        for sala_id in datos['salas']:
            sala = archivo.cargar_sala_binaria(sala_id)
            if sala is None or sala['id'] != sala_id:
                raise ValueError('Falta una sala del guardado.')
            registros.extend(sala['registros'])
        ordenados = Vector()
        for registro in registros:
            ordenados.agregarValor(registro)
        ordenar(ordenados, _comparar_registros)
        registros = list(ordenados)
        estado = decodificar(datos['raiz'], registros)
        partida = estado['partida']
        if dict(partida.encabezado()) != {k: datos[k] for k in actual}:
            raise ValueError('Encabezado y estado no coinciden.')
        if (partida.historial.registrando or partida.terminada
                or partida.jugador.evento_actual is None
                or partida.jugador.evento_actual is not partida.reloj.proximo()
                or partida.jugador.evento_actual.tiempo != partida.tiempo):
            raise ValueError('El guardado no está en una decisión válida del jugador.')
        red = ControladorRed(sesion_actual.fuente, partida.cripta,
                             sesion_actual.red._cache,
                             version_catalogo={'version': partida.version_catalogo},
                             completar_lotes=getattr(sesion_actual.red, '_completar_lotes', True),
                             despachador=DespachoEnHilos() if isinstance(
                                 sesion_actual.red._despachador, DespachoEnHilos) else None)
        for campo in CAMPOS_RED:
            setattr(red, campo, estado['red'][campo])
        numero = estado['numero_solicitud']
        red._buffer._base = red._buffer._siguiente = red._buffer._proximo_numero = numero
        partida._resolver_ficha = _resolvedor_fichas(red)
        partida.aplicar_efecto = efectos.aplicar_efecto_objeto
        partida.al_morir_enemigo.agregarValor(red.notificar_muerte_enemigo)
        for campo, valor in vars(sesion_actual.red).items():
            if campo.startswith('contador_'):
                setattr(red, campo, valor)
        for campo in ('contador_aciertos', 'contador_fallos', 'contador_desalojos'):
            setattr(red._fichas, campo, getattr(sesion_actual.red._fichas, campo))
        sesion = SesionPartida(partida, red, sesion_actual.fuente,
                               esqueleto_desde_cache=sesion_actual.esqueleto_desde_cache,
                               nombre_jugador=datos.get('nombre_jugador'))
        sesion.acciones = estado['acciones']
        sesion.protegidas = estado['protegidas']
        sesion.mensajes_guardados = estado.get('mensajes')
        return sesion
    except (KeyError, IndexError, TypeError, AttributeError, RecursionError,
            ErrorFormatoBinario) as error:
        raise ValueError(f'Guardado dañado o incompatible: {error}') from error
