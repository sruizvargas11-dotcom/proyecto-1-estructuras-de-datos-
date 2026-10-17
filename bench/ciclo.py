"""Mide intervalos completos del motor con mapa precargado, sin red ni render.

python -m bench.ciclo --salida resultados.json
Los datos sintéticos no cambian ninguna cripta oficial.
"""
import argparse
import cProfile
import json
import math
import platform
import tempfile
from pathlib import Path
from time import perf_counter_ns

from bitacora_partida import BitacoraPartida
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import SesionPartida
from estructuras.array_circular import ArrayCircular
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar
from modelo.mundo.cripta_modelo import CriptaModelo
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from modelo.entidades.jugador import Jugador
from modelo.entidades.enemigo import Enemigo
from modelo.partida import Partida


class RedPrecargada:
    """Puerto de ensayo: todo el mapa está en memoria, no hace HTTP ni disco."""
    def incorporar_listas(self):
        pass

    def proteger_fichas(self, tipos):
        pass

    def liberar_fichas(self, tipos):
        pass

    def asegurar_entrada(self, sala_id):
        return None

    def planificar_precarga(self, sala):
        pass

    def procesar_cola(self):
        pass

    def cerrar(self, tiempo=None):
        pass


class PuertoMedicion:
    """Sin interfaz: alterna movimientos y conserva solo 20 mensajes."""
    def __init__(self):
        self.mensajes = ArrayCircular(20)
        self.direccion = 'E'

    def mostrar_estado(self, partida):
        pass

    def leer_comando(self):
        direccion = self.direccion
        self.direccion = 'O' if direccion == 'E' else 'E'
        return direccion

    def agregar_mensaje(self, tiempo, texto):
        self.mensajes.agregarValor((tiempo, texto))

    def mostrar_fin(self, partida):
        pass


def crear_escenario(salas=200, semilla=42, ruta_log=None):
    if type(salas) is not int or salas < 4:
        raise ValueError('El escenario necesita al menos cuatro salas.')
    cripta = CriptaModelo('sintetica-ciclo', '1', 1, salas, None, 0, 10)
    for i in range(1, salas + 1):
        sala = Sala(i, f'Sala sintética {i}')
        if i > 1:
            sala.salidas.insertar_al_final(Salida('O', i - 1))
        if i < salas:
            sala.salidas.insertar_al_final(Salida('E', i + 1))
        cripta.agregar_sala(sala)
    cripta.finalizar_carga()
    jugador = Jugador('jugador', 10**9, 10, 5, 100, 10, cripta.sala_por_id(1))
    partida = Partida(cripta, jugador, semilla, 'sintetico-1')
    for sala in cripta.recorrer_salas():
        # Un actor por sala: evita concentrar artificialmente todo en una lista.
        comportamiento = ('guardián', 'errante', 'rastreador')[(sala.id - 1) % 3]
        enemigo = Enemigo(f'e-{sala.id}', 'sintetico', 'Enemigo de ensayo',
                          100, 1, 0, 100, comportamiento, sala, vida=50)
        enemigo.regeneracion = 1
        sala.enemigos_dormidos.insertar_al_final(enemigo)
    partida.inicializar()
    for sala in cripta.recorrer_salas():
        partida.activar_enemigos(sala)
    bitacora = None
    if ruta_log is not None:
        bitacora = BitacoraPartida.partida_nueva(str(ruta_log), **dict(partida.encabezado()))
    sesion = SesionPartida(partida, RedPrecargada(), None, bitacora)
    return ControladorJuego(sesion, PuertoMedicion())


def ejecutar_intervalo(controlador):
    """Desde la decisión actual hasta dejar lista la siguiente, sin extraerla."""
    partida = controlador.partida
    entrada = partida.reloj.proximo()
    if entrada is None or entrada.dato.dueno is not partida.jugador:
        raise RuntimeError('El intervalo debe empezar en una decisión del jugador.')
    controlador.ciclo()  # valida/aplica la acción, deltas, log con flush y agenda
    while not partida.terminada:
        entrada = partida.reloj.proximo()
        if entrada is None:
            raise RuntimeError('Agenda vacía durante el ensayo.')
        if entrada.dato.dueno is partida.jugador and entrada.dato.tipo == 'accion':
            partida.reloj.tiempo_actual = entrada.tiempo
            if partida.historial.registrando:
                partida.historial.confirmar_accion()
            # Preparación del siguiente punto de decisión; puerto de red sin E/S.
            controlador.red.incorporar_listas()
            controlador._sincronizar_protegidas()
            return
        controlador.ciclo()
    raise RuntimeError('El escenario terminó antes de completar la medición.')


def comparar_numeros(a, b):
    return (a > b) - (a < b)


def resumen(tiempos):
    if not len(tiempos):
        raise ValueError('Se necesita al menos una muestra.')
    ordenados = Vector()
    for tiempo in tiempos:
        ordenados.agregarValor(tiempo)
    ordenar(ordenados, comparar_numeros)
    n = len(ordenados)
    mediana = ordenados.obtenerValor(n // 2)
    if n % 2 == 0:
        mediana = (mediana + ordenados.obtenerValor(n // 2 - 1)) / 2
    return {'min_ms': ordenados.obtenerValor(0), 'mediana_ms': mediana,
            'p95_ms': ordenados.obtenerValor(math.ceil(n * .95) - 1),
            'max_ms': ordenados.obtenerValor(n - 1),
            'cumple_max_20_ms': ordenados.obtenerValor(n - 1) < 20}


def medir_escala(escala=1, ciclos=1000, repeticiones=5, salas_base=200, semilla=42,
                  carpeta=None, calentamiento=5, perfil=False):
    if ciclos < 1 or repeticiones < 1 or ciclos % repeticiones:
        raise ValueError('Ciclos positivos y divisibles entre repeticiones.')
    if escala < 1:
        raise ValueError('La escala debe ser positiva.')
    carpeta = Path(carpeta or tempfile.mkdtemp(prefix='cripta-ciclos-'))
    carpeta.mkdir(parents=True, exist_ok=True)
    muestras = Vector()
    corridas = []
    for repeticion in range(repeticiones):
        c = crear_escenario(salas_base * escala, semilla, carpeta / f'escala-{escala}-{repeticion}.log')
        try:
            for _ in range(calentamiento):
                ejecutar_intervalo(c)
            antes = dict(c.contadores())
            tiempos = Vector()
            for _ in range(ciclos // repeticiones):
                inicio = perf_counter_ns()
                ejecutar_intervalo(c)
                ms = (perf_counter_ns() - inicio) / 1_000_000
                tiempos.agregarValor(ms)
                muestras.agregarValor(ms)
            despues = dict(c.contadores())
            corridas.append({'repeticion': repeticion, 'muestras_ms': list(tiempos),
                             'resumen': resumen(tiempos),
                             'eventos_medidos': {k: despues[k] - antes[k] for k in antes},
                             'heap': dict(c.reloj.agenda.contadores()),
                             'historial': dict(c.historial.contadores())})
        finally:
            c._cerrar(False)
    ruta_perfil = None
    if perfil:
        c = crear_escenario(salas_base * escala, semilla, carpeta / f'perfil-{escala}.log')
        try:
            for _ in range(calentamiento):
                ejecutar_intervalo(c)
            prof = cProfile.Profile()
            prof.enable()
            for _ in range(10):
                ejecutar_intervalo(c)
            prof.disable()
            ruta_perfil = str(carpeta / f'perfil-{escala}.prof')
            prof.dump_stats(ruta_perfil)
        finally:
            c._cerrar(False)
    return {'escala': escala, 'salas': salas_base * escala, 'enemigos_activos_iniciales': salas_base * escala,
            'efectos_recurrentes_iniciales': salas_base * escala, 'ciclos_medidos': len(muestras),
            'repeticiones': repeticiones, 'calentamiento_por_repeticion': calentamiento,
            'resumen': resumen(muestras), 'corridas': corridas, 'perfil': ruta_perfil}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', required=True)
    parser.add_argument('--escalas', nargs='+', type=int, default=[1, 10, 50])
    parser.add_argument('--ciclos', type=int, default=1000, help='Total por escala, repartido entre repeticiones')
    parser.add_argument('--repeticiones', type=int, default=5)
    parser.add_argument('--salas-base', type=int, default=200)
    parser.add_argument('--perfil', action='store_true', help='Perfil aparte, fuera de los tiempos publicados')
    opciones = parser.parse_args()
    destino = Path(opciones.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    filas = []
    for escala in opciones.escalas:
        fila = medir_escala(escala, opciones.ciclos, opciones.repeticiones, opciones.salas_base,
                             carpeta=destino.parent / 'ciclos-datos', perfil=opciones.perfil)
        filas.append(fila)
        print(f"x{escala}: {fila['resumen']}", flush=True)
        evidencia = {'python': platform.python_version(), 'sistema': platform.platform(),
                     'semilla': 42, 'red_y_render': False, 'bitacora_con_flush': True,
                     'gc': 'configuración normal, no desactivado', 'filas': filas}
        destino.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
