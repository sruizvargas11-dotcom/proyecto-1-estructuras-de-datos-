"""Benchmark 4.2 — Precarga de contenido.

Ejecutar directo, sin pytest, desde la raíz del proyecto:
    python bench/bench_precarga.py
    python bench/bench_precarga.py --salida docs/evidencia/bench_precarga.txt

Mide con time.perf_counter(), 5 repeticiones por medición, reporta la mediana.
Las criptas grandes son sintéticas (grillas lado x lado) y responden con latencia 0:
la columna "ms" mide solo el costo de CPU del cliente. El costo de red se estima como
esperas x ~400 ms (enunciado §3.4). Nada se escribe en partidas/: la caché va a una
carpeta temporal que se borra al terminar.

Secciones (documento 4.02):
  A. Frecuencia de operaciones en una partida simulada        -> punto 1
  B. Estrategias de precarga (implementada y alternativas)    -> punto 5
  C. Estructuras: cola de pendientes y pertenencia            -> punto 5
  D. Presupuesto de solicitudes en cripta-01 (guardia activa) -> punto 6
"""

import argparse
import contextlib
import io
import os
import platform
import random
import sys
import tempfile
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import controlador.controlador_red as modulo_red
from adaptadores.datos_offline import DatosOffline
from controlador.controlador_red import ControladorRed, cargar_esqueleto_completo, _contiene
from controlador.inicio_partida import nueva_partida
from estructuras.array_ordenado import ArrayOrdenado
from estructuras.cola import Cola
from estructuras.vector_dinamico import Vector

REPETICIONES = 5
GRILLAS = ((5, 60), (10, 200), (20, 600))      # (lado, movimientos): n = lado*lado salas
LATENCIA_MS = 400                               # §3.4: ~400 ms por solicitud


# ─────────────────────────────────────────────────────────────────────
# Medición
# ─────────────────────────────────────────────────────────────────────

def mediana(valores):
    """Mediana con inserción propia (sin sorted ni .sort, §7)."""
    orden = []
    for v in valores:
        i = len(orden)
        orden.append(v)
        while i > 0 and orden[i - 1] > v:
            orden[i] = orden[i - 1]
            i -= 1
        orden[i] = v
    if not orden:
        raise ValueError('No hay muestras.')
    medio = len(orden) // 2
    return orden[medio] if len(orden) % 2 else (orden[medio - 1] + orden[medio]) / 2


def medir(accion, repeticiones=REPETICIONES):
    """Mediana en ms de `repeticiones` ejecuciones de accion()."""
    if type(repeticiones) is not int or repeticiones < 1:
        raise ValueError('Las repeticiones deben ser positivas.')
    accion()  # calentamiento fuera del cronómetro
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        accion()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    return mediana(tiempos)


# ─────────────────────────────────────────────────────────────────────
# Fuentes de datos para el bench
# ─────────────────────────────────────────────────────────────────────

class FuenteGrilla:
    """Cripta sintética lado x lado; cada sala trae 1 enemigo, 1 objeto y 1 trampa."""

    FICHAS = {
        'ent_a': {'id': 'ent_a', 'clase': 'enemigo', 'nombre': 'A', 'vida_max': 5, 'ataque': 1,
                  'defensa': 0, 'velocidad': 100, 'comportamiento': 'errante'},
        'itm_b': {'id': 'itm_b', 'clase': 'arma', 'nombre': 'B', 'peso': 1, 'valor': 1,
                  'ataque_bonus': 1},
        'trp_c': {'id': 'trp_c', 'clase': 'trampa', 'nombre': 'C', 'daño': 1, 'rearme': 300},
    }

    def __init__(self, lado):
        self.lado = lado

    def _id(self, fila, col):
        return fila * self.lado + col + 1

    def datos_cripta(self, cripta_id):
        total = self.lado * self.lado
        return {'id': cripta_id, 'version': 'g1', 'salas_total': total, 'paginas': 1,
                'sala_inicial': 1, 'sala_salida': total, 'llave_salida': None,
                'presupuesto_solicitudes': 10 ** 6, 'inventario_max': 10}

    def esqueleto_cripta(self, cripta_id, pagina):
        salas = []
        for f in range(self.lado):
            for c in range(self.lado):
                s = {}
                if f > 0:
                    s['N'] = {'sala': self._id(f - 1, c)}
                if f < self.lado - 1:
                    s['S'] = {'sala': self._id(f + 1, c)}
                if c < self.lado - 1:
                    s['E'] = {'sala': self._id(f, c + 1)}
                if c > 0:
                    s['O'] = {'sala': self._id(f, c - 1)}
                salas.append({'id': self._id(f, c), 'nombre': 'S', 'salidas': s})
        return {'pagina': 1, 'total_paginas': 1, 'salas': salas}

    def version_cripta(self, cripta_id):
        return {'id': cripta_id, 'version': 'g1'}

    def contenido_salas(self, cripta_id, sala_ids):
        assert 1 <= len(sala_ids) <= 10
        return {'contenido': [
            {'sala': s, 'enemigos': [{'instancia': f'e{s}', 'tipo': 'ent_a'}],
             'objetos': ['itm_b'], 'trampas': [{'instancia': f't{s}', 'tipo': 'trp_c'}]}
            for s in sala_ids]}

    def catalogo(self, tipo_ids):
        return {'entidades': [self.FICHAS[t] for t in tipo_ids]}

    def version_catalogo(self):
        return {'version': 'c1'}


class FuenteConGuardia:
    """Envuelve una fuente e imita la guardia de DatosHTTP: cuenta cada solicitud de
    red y se niega a enviar al alcanzar presupuesto_solicitudes."""

    RED = ('listar_criptas', 'datos_cripta', 'esqueleto_cripta', 'contenido_salas',
           'catalogo', 'version_cripta', 'version_catalogo')

    def __init__(self, fuente):
        self._fuente = fuente
        self.solicitudes = 0
        self._presupuesto = None

    def dentro_del_presupuesto(self):
        return self._presupuesto is None or self.solicitudes < self._presupuesto

    def __getattr__(self, nombre):
        metodo = getattr(self._fuente, nombre)
        if nombre not in self.RED:
            return metodo

        def envuelto(*argumentos):
            if self._presupuesto is not None and self.solicitudes >= self._presupuesto:
                raise RuntimeError(f"Presupuesto de solicitudes agotado ({nombre}).")
            self.solicitudes += 1
            respuesta = metodo(*argumentos)
            if nombre == 'datos_cripta':
                self._presupuesto = respuesta['presupuesto_solicitudes']
            return respuesta
        return envuelto


# ─────────────────────────────────────────────────────────────────────
# Estrategias de precarga
# ─────────────────────────────────────────────────────────────────────

class RedUnNivel(ControladorRed):
    """Alternativa: solo vecinas directas."""

    def planificar_precarga(self, sala_actual):
        nuevas = 0
        for salida in sala_actual.salidas.recorrer_valores():
            if self._encolar(self._destino(salida).id):
                nuevas += 1
        return nuevas


class RedLoteLleno(ControladorRed):
    """Alternativa: si alguna vecina directa aún no fue pedida, rellena el lote hasta 10
    con las salas no pedidas más cercanas (BFS). Si todas ya fueron pedidas, no hace nada."""

    def planificar_precarga(self, sala_actual):
        urgente = False
        for salida in sala_actual.salidas.recorrer_valores():
            if not self.contenido_solicitado(salida.sala_destino_id):
                urgente = True
        if not urgente:
            return 0
        vistas = ArrayOrdenado()
        vistas.insertar(sala_actual.id, True)
        frontera = Cola()
        frontera.encolar(sala_actual)
        nuevas = 0
        while not frontera.esta_vacia() and self.pendientes() < self.MAX_LOTE:
            sala = frontera.desencolar()
            for salida in sala.salidas.recorrer_valores():
                destino = self._destino(salida)
                if vistas.busqueda_binaria(destino.id) is not None:
                    continue
                vistas.insertar(destino.id, True)
                frontera.encolar(destino)
                if self.pendientes() < self.MAX_LOTE and self._encolar(destino.id):
                    nuevas += 1
        return nuevas


class RedCompletaLotes(ControladorRed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, completar_lotes=True, **kwargs)


ESTRATEGIAS = (
    ('sin_precarga', ControladorRed),
    ('vecinas_1_nivel', RedUnNivel),
    ('vecinas_2_niveles', ControladorRed),
    ('vecinas_lote_lleno*', RedCompletaLotes),   # * = implementada en el juego
    ('mapa_completo', ControladorRed),
    ('lote_lleno_bfs', RedLoteLleno),
)


def recorrido(cripta, pasos, semilla=42):
    """Camino aleatorio reproducible (ids de sala visitados tras la inicial)."""
    azar = random.Random(semilla)
    sala = cripta.sala_por_id(cripta.sala_inicial_id)
    camino = []
    for _ in range(pasos):
        salidas = list(sala.salidas.recorrer_valores())
        sala = salidas[azar.randrange(len(salidas))].sala_destino
        camino.append(sala.id)
    return camino


def jugar(fuente, cripta, camino, estrategia, clase, carpeta):
    """Mismo flujo que el juego: al entrar se garantiza la sala; tras moverse se
    planifica y se envía un lote. Devuelve (controlador, esperas, visitadas)."""
    red = clase(fuente, cripta, carpeta)
    inicial = cripta.sala_por_id(cripta.sala_inicial_id)
    precarga = estrategia not in ('sin_precarga', 'mapa_completo')
    if estrategia == 'mapa_completo':
        for sala in cripta.recorrer_salas():
            red._encolar(sala.id)
        red.garantizar_contenido(inicial.id)
        while red.pendientes():
            red.procesar_cola()
    else:
        if precarga:
            red.planificar_precarga(inicial)
        red.garantizar_contenido(inicial.id)
    esperas = 0
    visitadas = Vector()
    visitadas.agregarValor(inicial.id)
    for sala_id in camino:
        if not red.contenido_cargado(sala_id):
            esperas += 1                     # el jugador tendría que esperar la red
        red.garantizar_contenido(sala_id)
        if not _contiene(visitadas, sala_id):
            visitadas.agregarValor(sala_id)
        if precarga:
            red.planificar_precarga(cripta.sala_por_id(sala_id))
            red.procesar_cola()
    return red, esperas, len(visitadas)


def lotes_de_contenido(red):
    tamanos = Vector()
    for numero, sub, clase, ids, en_red in red.registro_solicitudes():
        if clase == 'contenido' and en_red:
            tamanos.agregarValor(len(ids))
    return tamanos


# ─────────────────────────────────────────────────────────────────────
# Secciones
# ─────────────────────────────────────────────────────────────────────

def seccion_frecuencias(out):
    out("A. FRECUENCIA DE OPERACIONES (estrategia implementada, vecinas y lote lleno)")
    out("   Partida simulada: camino aleatorio reproducible (semilla 42) en grillas.")
    out(f"   {'n':>5} {'movs':>5} {'garantizar':>10} {'planificar':>10} {'procesar':>9} "
        f"{'encoladas':>9} {'cola_max':>8} {'lotes':>6} {'salas/lote':>10} "
        f"{'pertenencia':>11} {'elem/cons':>9}")
    original = modulo_red._contiene
    cuenta = {'consultas': 0, 'elementos': 0}

    def contar(vector, valor):
        cuenta['consultas'] += 1
        revisados = 0
        for elemento in vector:
            revisados += 1
            if elemento == valor:
                cuenta['elementos'] += revisados
                return True
        cuenta['elementos'] += revisados
        return False

    modulo_red._contiene = contar
    try:
        for lado, pasos in GRILLAS:
            cuenta['consultas'] = cuenta['elementos'] = 0
            fuente = FuenteGrilla(lado)
            cripta = cargar_esqueleto_completo(fuente, 'grilla')
            camino = recorrido(cripta, pasos)
            with tempfile.TemporaryDirectory() as carpeta:
                red = RedCompletaLotes(fuente, cripta, carpeta)
                inicial = cripta.sala_por_id(1)
                encoladas = red.planificar_precarga(inicial)
                red.garantizar_contenido(1)
                cola_max = red.pendientes()
                for sala_id in camino:
                    red.garantizar_contenido(sala_id)
                    encoladas += red.planificar_precarga(cripta.sala_por_id(sala_id))
                    cola_max = max(cola_max, red.pendientes())
                    red.procesar_cola()
                lotes = lotes_de_contenido(red)
                promedio = sum(lotes) / len(lotes) if len(lotes) else 0
                out(f"   {lado * lado:>5} {pasos:>5} {pasos + 1:>10} {pasos + 1:>10} {pasos:>9} "
                    f"{encoladas:>9} {cola_max:>8} {len(lotes):>6} {promedio:>10.1f} "
                    f"{cuenta['consultas']:>11} {cuenta['elementos'] / cuenta['consultas']:>9.1f}")
    finally:
        modulo_red._contiene = original
    out("   pertenencia = consultas '¿ya está pedida/cargada/encolada?' (búsqueda lineal en Vector)")
    out("   elem/cons   = elementos revisados en promedio por consulta")


def seccion_estrategias(out):
    out("B. ESTRATEGIAS DE PRECARGA (* = implementada)")
    out("   esperas = veces que el jugador entra a una sala aún no cargada (cada una ~400 ms de red)")
    encabezado = (f"   {'n':>5} {'estrategia':<20} {'ms(med)':>9} {'solicitudes':>11} {'esperas':>8} "
                  f"{'espera_est':>10} {'cargadas':>8} {'visitadas':>9}")
    out(encabezado)
    for lado, pasos in GRILLAS:
        fuente = FuenteGrilla(lado)
        cripta = cargar_esqueleto_completo(fuente, 'grilla')
        camino = recorrido(cripta, pasos)
        for nombre, clase in ESTRATEGIAS:
            estrategia = nombre.rstrip('*')
            with tempfile.TemporaryDirectory() as carpeta:
                red, esperas, visitadas = jugar(fuente, cripta, camino, estrategia, clase, carpeta)

            def una_partida():
                with tempfile.TemporaryDirectory() as t:
                    jugar(fuente, cripta, camino, estrategia, clase, t)
            ms = medir(una_partida)
            out(f"   {lado * lado:>5} {nombre:<20} {ms:>9.2f} {red.contador_solicitudes_contenido:>11} "
                f"{esperas:>8} {esperas * LATENCIA_MS / 1000:>9.1f}s {len(red._incorporadas):>8} "
                f"{visitadas:>9}")
        out("")
    out("   cripta-01 (datos offline), camino fijo 1-2-3-4-3-2-5 (solo red; ignora llaves):")
    fuente = DatosOffline()
    cripta = cargar_esqueleto_completo(fuente, 'cripta-01')
    for nombre, clase in ESTRATEGIAS:
        with tempfile.TemporaryDirectory() as carpeta:
            red, esperas, _ = jugar(fuente, cripta, [2, 3, 4, 3, 2, 5], nombre.rstrip('*'), clase, carpeta)
        out(f"   {6:>5} {nombre:<20} {'-':>9} {red.contador_solicitudes_contenido:>11} {esperas:>8} "
            f"{esperas * LATENCIA_MS / 1000:>9.1f}s {len(red._incorporadas):>8}")


def seccion_estructuras(out):
    out("C. ESTRUCTURAS")
    out("   C1. Cola de pendientes: Cola propia (lista enlazada) vs list.pop(0)")
    out(f"   {'n':>8} {'Cola propia ms':>15} {'list.pop(0) ms':>15}")
    for n in (10, 100, 1000, 10000, 100000):
        def con_cola():
            cola = Cola()
            for i in range(n):
                cola.encolar(i)
            while not cola.esta_vacia():
                cola.desencolar()

        def con_lista():
            lista = []
            for i in range(n):
                lista.append(i)
            while lista:
                lista.pop(0)
        out(f"   {n:>8} {medir(con_cola):>15.3f} {medir(con_lista):>15.3f}")

    out("")
    out("   C2. Pertenencia '¿ya pedida?': Vector lineal (implementado) vs ArrayOrdenado binario")
    out("       n inserciones sin duplicados + n consultas (mitad presentes)")
    out(f"   {'n':>8} {'Vector ms':>15} {'ArrayOrdenado ms':>17}")
    for n in (25, 100, 400, 1600):
        ids = list(range(n))
        random.Random(7).shuffle(ids)
        consultas = [i // 2 if i % 2 == 0 else n + i // 2 for i in range(n)]
        random.Random(8).shuffle(consultas)

        def con_vector():
            v = Vector()
            for i in ids:
                if not _contiene(v, i):
                    v.agregarValor(i)
            for c in consultas:
                _contiene(v, c)

        def con_ordenado():
            a = ArrayOrdenado()
            for i in ids:
                if a.busqueda_binaria(i) is None:
                    a.insertar(i, True)
            for c in consultas:
                a.busqueda_binaria(c)
        out(f"   {n:>8} {medir(con_vector):>15.3f} {medir(con_ordenado):>17.3f}")


def seccion_presupuesto(out):
    out("D. PRESUPUESTO EN cripta-01 (guardia igual a DatosHTTP; presupuesto = 9)")
    out("   Camino 1 -> 2 -> 3 -> 4 -> 6 (salida). Solo mide red: las llaves no se simulan.")
    with tempfile.TemporaryDirectory() as cache_a, tempfile.TemporaryDirectory() as cache_b:
        casos = (('caché vacía, con --cripta', False, cache_a),
                 ('caché vacía, listando criptas', True, cache_b),
                 ('caché caliente (2da partida)', False, cache_a))
        for etiqueta, listar, carpeta in casos:
            fuente = FuenteConGuardia(DatosOffline())
            if listar:
                fuente.listar_criptas()
            sesion = nueva_partida(fuente, 'cripta-01', carpeta, semilla=1)
            red = sesion.red
            cripta = red._cripta
            resultado = []
            for sala_id in (2, 3, 4, 6):
                if red.asegurar_entrada(sala_id) is not None:
                    resultado.append(f"sala {sala_id}: RECHAZADA")
                    continue
                resultado.append(f"sala {sala_id}: ok")
                red.planificar_precarga(cripta.sala_por_id(sala_id))
                red.procesar_cola()
            out(f"   {etiqueta:<32} solicitudes={fuente.solicitudes:<3} " + ", ".join(resultado))


def equipo(out):
    out("EQUIPO")
    out(f"   fecha        : {datetime.now():%Y-%m-%d %H:%M}")
    out(f"   sistema      : {platform.platform()}")
    out(f"   procesador   : {platform.processor() or platform.machine()}")
    out(f"   núcleos      : {os.cpu_count()}")
    out(f"   python       : {sys.version.split()[0]}")
    out(f"   repeticiones : {REPETICIONES} (se reporta la mediana)")


def main(argumentos=None):
    parser = argparse.ArgumentParser(description='Benchmark de precarga (4.02)')
    parser.add_argument('--salida', help='Archivo donde guardar también la evidencia (UTF-8)')
    opciones = parser.parse_args(argumentos)

    lineas = []

    def out(texto=""):
        print(texto, flush=True)
        lineas.append(texto)

    out("BENCHMARK 4.2 - PRECARGA DE CONTENIDO")
    out("=" * 72)
    equipo(out)
    for seccion in (seccion_frecuencias, seccion_estrategias, seccion_estructuras,
                    seccion_presupuesto):
        out("")
        with contextlib.redirect_stderr(io.StringIO()):
            seccion(out)

    if opciones.salida:
        carpeta = os.path.dirname(opciones.salida)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        with open(opciones.salida, 'w', encoding='utf-8') as archivo:
            archivo.write("\n".join(lineas) + "\n")
        print(f"\nEvidencia guardada en {opciones.salida}")


if __name__ == "__main__":
    main()
