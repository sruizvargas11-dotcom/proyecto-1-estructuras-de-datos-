"""Mide y perfila el ciclo del juego con una cripta sintética grande.

    python -m herramientas.perfilar_ciclo                    # x1, x10 y x50
    python -m herramientas.perfilar_ciclo --escala 50 --perfil
    python -m herramientas.perfilar_ciclo --guardar          # deja la tabla en docs/evidencia/

Ciclo medido (plan v4, ROL 3 día 12): desde que el jugador confirma una acción
hasta que el modelo queda listo para la siguiente decisión, incluidos los
eventos de enemigos y efectos de ese intervalo y la escritura del log. Se
excluyen red y render: la fuente es sintética en memoria y la vista no dibuja.
"""
import argparse
import cProfile
import gc
import io
import json
import os
import pstats
import random
import shutil
import tempfile
import time
from datetime import datetime

from adaptadores.fuente_datos import FuenteDeDatos
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import nueva_partida
from estructuras.ordenamientos import ordenar
from estructuras.vector_dinamico import Vector

META_MS = 20.0
SALAS_POR_PAGINA = 50
DIRECCIONES = ("N", "S", "E", "O")
OPUESTA = (("N", "S"), ("S", "N"), ("E", "O"), ("O", "E"))
CATALOGO = (
    {"id": "ent_rastreador", "nombre": "Rata", "clase": "enemigo", "vida_max": 40,
     "ataque": 3, "defensa": 1, "velocidad": 150, "comportamiento": "rastreador",
     "suelta": ["itm_pocion"]},
    {"id": "ent_errante", "nombre": "Murciélago", "clase": "enemigo", "vida_max": 30,
     "ataque": 2, "defensa": 1, "velocidad": 120, "comportamiento": "errante"},
    {"id": "ent_guardian", "nombre": "Guardián", "clase": "enemigo", "vida_max": 60,
     "ataque": 4, "defensa": 2, "velocidad": 90, "comportamiento": "guardián"},
    {"id": "ent_regenerador", "nombre": "Troll", "clase": "enemigo", "vida_max": 50,
     "ataque": 3, "defensa": 2, "velocidad": 100, "comportamiento": "guardián",
     "regeneracion": 2},
    {"id": "itm_pocion", "nombre": "Poción", "clase": "pocion", "peso": 1, "valor": 10,
     "cura": 5},
    {"id": "itm_daga", "nombre": "Daga", "clase": "arma", "peso": 2, "valor": 15,
     "ataque_bonus": 3},
    {"id": "itm_llave", "nombre": "Llave de hierro", "clase": "llave", "peso": 1,
     "valor": 0, "abre": "puertas"},
    {"id": "itm_llave_salida", "nombre": "Llave negra", "clase": "llave", "peso": 1,
     "valor": 0, "abre": "salida"},
    {"id": "itm_pergamino_retroceso", "nombre": "Pergamino de retroceso",
     "clase": "pergamino_retroceso", "peso": 1, "valor": 40},
    {"id": "trp_dardos", "nombre": "Dardos", "clase": "trampa", "daño": 1, "rearme": 300},
)
TIPOS_ENEMIGO = ("ent_rastreador", "ent_errante", "ent_guardian", "ent_regenerador")


def _opuesta(direccion):
    for a, b in OPUESTA:
        if a == direccion:
            return b
    raise ValueError(direccion)


class FuenteSintetica(FuenteDeDatos):
    """Cripta en cuadrícula con el mismo contrato que DatosHTTP/DatosOffline.

    Las salas se numeran 1..n en filas de 'ancho'. Una de cada 9 puertas Este
    está cerrada con llave y se cierra sola 300 unidades después de abrirse.
    Los enemigos se reparten en orden (rastreador, errante, guardián,
    regenerador) y una de cada 5 salas tiene trampa.
    """

    def __init__(self, salas=200, enemigos=300, semilla=7, tipo_unico=None,
                 sala_multitud=None, tipos_objeto=0):
        """tipo_unico: todos los enemigos de ese tipo. sala_multitud: todos en esa
        sala. tipos_objeto: fichas de objeto distintas repartidas por el suelo
        (para forzar una LRU grande)."""
        if salas < 4 or enemigos < 0:
            raise ValueError("Se necesitan al menos 4 salas y enemigos >= 0.")
        self.salas = salas
        self.ancho = 1
        while self.ancho * self.ancho < salas:
            self.ancho += 1
        self.cripta_id = f"sintetica-{salas}-{enemigos}"
        self.tipos_objeto = tipos_objeto
        azar = random.Random(semilla)
        self._enemigos = [[] for _ in range(salas + 1)]
        for i in range(enemigos):
            sala = sala_multitud or azar.randint(2, salas - 1)   # inicial y salida vacías
            tipo = tipo_unico or TIPOS_ENEMIGO[i % len(TIPOS_ENEMIGO)]
            self._enemigos[sala].append({"instancia": f"e-{i + 1}", "tipo": tipo})

    def _vecina(self, sala_id, direccion):
        fila, columna = (sala_id - 1) // self.ancho, (sala_id - 1) % self.ancho
        if direccion == "N":
            fila -= 1
        elif direccion == "S":
            fila += 1
        elif direccion == "E":
            columna += 1
        else:
            columna -= 1
        if fila < 0 or columna < 0 or columna >= self.ancho:
            return None
        vecina = fila * self.ancho + columna + 1
        return vecina if vecina <= self.salas else None

    def _salidas(self, sala_id):
        salidas = {}
        for direccion in DIRECCIONES:
            destino = self._vecina(sala_id, direccion)
            if destino is None:
                continue
            datos = {"sala": destino}
            origen_e = sala_id if direccion == "E" else destino if direccion == "O" else None
            if self.salas in (sala_id, destino):
                # La salida queda tras una llave que no existe: la medición
                # nunca termina en victoria antes de completar los ciclos.
                datos.update(cerrada=True, llave="itm_llave_salida")
            elif origen_e is not None and origen_e % 9 == 0:
                datos.update(cerrada=True, llave="itm_llave", cierre_automatico=300)
            salidas[direccion] = datos
        return salidas

    def listar_criptas(self):
        return {"criptas": [{"id": self.cripta_id, "nombre": "Cripta sintética"}]}

    def datos_cripta(self, cripta_id):
        return {"id": self.cripta_id, "version": "sintetica-v1", "salas_total": self.salas,
                "paginas": (self.salas + SALAS_POR_PAGINA - 1) // SALAS_POR_PAGINA,
                "salas_por_pagina": SALAS_POR_PAGINA, "sala_inicial": 1,
                "sala_salida": self.salas, "llave_salida": "itm_llave_salida",
                "presupuesto_solicitudes": 10 ** 9, "inventario_max": 10,
                "jugador": {"vida_max": 10 ** 9, "ataque": 25, "defensa": 3,
                            "velocidad": 100}}

    def esqueleto_cripta(self, cripta_id, pagina):
        total = (self.salas + SALAS_POR_PAGINA - 1) // SALAS_POR_PAGINA
        inicio = (pagina - 1) * SALAS_POR_PAGINA + 1
        fin = min(self.salas, inicio + SALAS_POR_PAGINA - 1)
        return {"pagina": pagina, "total_paginas": total,
                "salas": [{"id": s, "nombre": f"Sala {s}", "salidas": self._salidas(s)}
                          for s in range(inicio, fin + 1)]}

    def contenido_salas(self, cripta_id, sala_ids):
        if not 1 <= len(sala_ids) <= 10:
            raise ValueError("Máximo 10 salas por consulta.")
        contenido = []
        for s in sala_ids:
            objetos = ["itm_pocion"] if s % 4 == 0 else []
            if self.tipos_objeto:
                objetos += [f"itm_extra_{(s * 3 + k) % self.tipos_objeto}" for k in range(3)]
            if s % 9 == 8:
                objetos.append("itm_llave")
            trampas = [{"instancia": f"t-{s}", "tipo": "trp_dardos"}] if s % 5 == 0 else []
            contenido.append({"sala": s, "enemigos": list(self._enemigos[s]),
                              "objetos": objetos, "trampas": trampas})
        return {"contenido": contenido}

    def catalogo(self, tipo_ids):
        if not 1 <= len(tipo_ids) <= 10:
            raise ValueError("Máximo 10 ids por consulta.")
        fichas = []
        for tipo_id in tipo_ids:
            if tipo_id.startswith("itm_extra_"):
                fichas.append({"id": tipo_id, "nombre": f"Reliquia {tipo_id[10:]}",
                               "clase": "arma", "peso": 1, "valor": 1, "ataque_bonus": 0})
                continue
            for ficha in CATALOGO:
                if ficha["id"] == tipo_id:
                    fichas.append(dict(ficha))
        return {"entidades": fichas}

    def version_cripta(self, cripta_id):
        return {"id": self.cripta_id, "version": "sintetica-v1"}

    def version_catalogo(self):
        return {"version": "sintetica-cat-v1"}

    def modo(self):
        return "simulado"


class GuionPerfil:
    """Vista silenciosa que juega sola y cronometra cada ciclo.

    Política del jugador (su propio random, no el de la partida): si hay
    enemigos en la sala ataca; si no, recoge lo que haya o se mueve a una
    salida abierta al azar. Nunca dibuja: el render queda fuera de la medición.
    """

    def __init__(self, partida, ciclos, semilla=11, politica=None):
        """politica(guion) -> comando opcional; None usa la política por defecto."""
        self.partida = partida
        self.ciclos = ciclos
        self._azar = random.Random(semilla)
        self._inicio = None
        self.tiempos_ns = Vector()
        self.pendientes = ciclos
        self.politica = politica

    def leer_comando(self):
        ahora = time.perf_counter_ns()
        if self._inicio is not None:
            self.tiempos_ns.agregarValor(ahora - self._inicio)
        if self.pendientes == 0:
            return "Q"
        self.pendientes -= 1
        comando = self._decidir()
        self._inicio = time.perf_counter_ns()
        return comando

    def _decidir(self):
        if self.politica is not None:
            comando = self.politica(self)
            if comando is not None:
                return comando
        sala = self.partida.jugador.sala_actual
        if len(sala.enemigos_activos):
            return "A"
        jugador = self.partida.jugador
        if len(sala.objetos_suelo) and len(jugador.inventario) < jugador.inventario_max:
            return "R"
        abiertas = [s.direccion for s in sala.salidas if not s.cerrada]
        if not abiertas:
            return "W"
        return abiertas[self._azar.randrange(len(abiertas))]

    def agregar_mensaje(self, tiempo, texto):
        pass

    def mostrar_estado(self, partida):
        pass

    def mostrar_inventario(self, partida, objetos, criterio):
        pass

    def mostrar_ayuda(self):
        pass

    def mostrar_objeto(self, nodo):
        pass

    def mostrar_fin(self, partida):
        pass


def _comparar(a, b):
    return (a > b) - (a < b)


def estadisticas(tiempos_ns):
    """min, mediana, p95 y max en ms; ordena con el ordenamiento propio."""
    copia = Vector()
    for valor in tiempos_ns:
        copia.agregarValor(valor)
    ordenar(copia, _comparar)
    n = len(copia)

    def en(posicion):
        return copia.obtenerValor(min(n - 1, posicion)) / 1e6

    return {"ciclos": n, "min_ms": en(0), "mediana_ms": en(n // 2),
            "p95_ms": en((n * 95) // 100), "max_ms": en(n - 1)}


def preparar(salas, enemigos, semilla_cripta=7, semilla_partida=3, carpeta=None,
             activar=True, cache_size=25, bitacora=True, **opciones_fuente):
    """Partida sobre la cripta sintética. Con activar=True (peor caso) todas las
    salas quedan cargadas y todos sus enemigos activos."""
    fuente = FuenteSintetica(salas, enemigos, semilla_cripta, **opciones_fuente)
    carpeta = carpeta or tempfile.mkdtemp(prefix="perfil_ciclo_")
    sesion = nueva_partida(fuente, fuente.cripta_id, os.path.join(carpeta, "cache"),
                           semilla=semilla_partida, cache_size=cache_size,
                           ruta_bitacora=os.path.join(carpeta, "perfil.log") if bitacora else None)
    partida, red = sesion.partida, sesion.red
    if activar:
        for sala in partida.cripta.recorrer_salas():
            red.garantizar_contenido(sala.id)
        for sala in partida.cripta.recorrer_salas():
            partida.activar_enemigos(sala)
    return sesion, carpeta


def medir(salas, enemigos, ciclos=1000, perfil=False, semilla=3):
    inicio_preparacion = time.perf_counter()
    sesion, carpeta = preparar(salas, enemigos, semilla_partida=semilla)
    preparacion_s = time.perf_counter() - inicio_preparacion
    guion = GuionPerfil(sesion.partida, ciclos)
    controlador = ControladorJuego(sesion, guion)
    perfilador = cProfile.Profile() if perfil else None
    gc.collect()
    try:
        if perfilador:
            perfilador.enable()
        controlador.jugar()
    finally:
        if perfilador:
            perfilador.disable()
        shutil.rmtree(carpeta, ignore_errors=True)
    resultado = estadisticas(guion.tiempos_ns)
    resultado.update(salas=salas, enemigos=enemigos, preparacion_s=round(preparacion_s, 2),
                     eventos_en_agenda=len(sesion.partida.reloj.agenda),
                     turnos_enemigo=controlador.contador_turnos_enemigo,
                     efectos=controlador.contador_efectos)
    if perfilador:
        texto = io.StringIO()
        pstats.Stats(perfilador, stream=texto).sort_stats("tottime").print_stats(18)
        resultado["perfil"] = texto.getvalue()
    return resultado


ESCALAS = ((1, 200, 300), (10, 2000, 3000), (50, 10000, 15000))


def _politica_pergamino(guion):
    """Alterna esperar y pergamino; repone el pergamino para medir cada reversión."""
    partida = guion.partida
    if guion.pendientes % 2 == 0:
        return "W"
    ficha = partida._resolver_ficha("itm_pergamino_retroceso")
    partida.jugador.inventario.insertar_al_final(partida.fabrica.crear(ficha))
    return "P"


def _politica_mover(guion):
    """Siempre se mueve si puede: fuerza la precarga en cada ciclo."""
    abiertas = [s.direccion for s in guion.partida.jugador.sala_actual.salidas
                if not s.cerrada]
    return abiertas[guion._azar.randrange(len(abiertas))] if abiertas else "W"


def _politica_rotar(guion):
    """Con el inventario lleno suelta y recoge: muchas fichas distintas en juego."""
    jugador = guion.partida.jugador
    sala = jugador.sala_actual
    if len(sala.objetos_suelo) and len(jugador.inventario) >= jugador.inventario_max:
        return "T" if guion.pendientes % 2 else "R"
    return None


def _politica_multitud(guion):
    """Entra a la sala de la multitud (al Este de la inicial) y se queda peleando."""
    sala = guion.partida.jugador.sala_actual
    if sala.id == 1:
        return "E"
    return "A" if len(sala.enemigos_activos) else "W"


SOSPECHOSOS = (
    # nombre, descripción, opciones de preparar, política
    ("base", "x1: 200 salas, 300 enemigos activos", dict(salas=200, enemigos=300), None),
    ("sala_por_id", "cripta de 10000 salas, todas cargadas; el jugador siempre se mueve",
     dict(salas=10000, enemigos=300), _politica_mover),
    ("lru", "600 tipos de objeto y --cache-size 600; inventario rotando",
     dict(salas=200, enemigos=300, tipos_objeto=600, cache_size=600), _politica_rotar),
    ("rastreadores", "300 rastreadores activos persiguiendo al jugador",
     dict(salas=200, enemigos=300, tipo_unico="ent_rastreador"), _politica_mover),
    ("multitud", "300 enemigos dormidos en una sala; el jugador entra y pelea",
     dict(salas=200, enemigos=300, sala_multitud=2, activar=False), _politica_multitud),
    ("log", "x1 sin bitácora (comparar con base para aislar la escritura del log)",
     dict(salas=200, enemigos=300, bitacora=False), None),
    ("pergamino", "x1: alterna esperar y pergamino (revertir un intervalo)",
     dict(salas=200, enemigos=300), _politica_pergamino),
)


def medir_escenario(opciones, politica, ciclos):
    opciones = dict(opciones)
    inicio = time.perf_counter()
    sesion, carpeta = preparar(**opciones)
    preparacion_s = time.perf_counter() - inicio
    guion = GuionPerfil(sesion.partida, ciclos, politica=politica)
    controlador = ControladorJuego(sesion, guion)
    gc.collect()
    try:
        controlador.jugar()
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
    resultado = estadisticas(guion.tiempos_ns)
    resultado["preparacion_s"] = round(preparacion_s, 2)
    resultado["agenda"] = len(sesion.partida.reloj.agenda)
    return resultado


def sospechosos(ciclos=300, solo=None):
    filas = []
    print(f"{'escenario':<14}{'mediana':>9}{'p95':>9}{'max':>9}{'prep s':>8}  descripción")
    for nombre, descripcion, opciones, politica in SOSPECHOSOS:
        if solo and nombre not in solo:
            continue
        r = medir_escenario(opciones, politica, ciclos)
        r.update(escenario=nombre, descripcion=descripcion)
        filas.append(r)
        print(f"{nombre:<14}{r['mediana_ms']:>9.3f}{r['p95_ms']:>9.3f}{r['max_ms']:>9.3f}"
              f"{r['preparacion_s']:>8}  {descripcion}", flush=True)
    return filas


def imprimir(filas):
    print(f"{'escala':>6}{'salas':>7}{'enemigos':>9}{'ciclos':>7}{'min':>8}{'mediana':>9}"
          f"{'p95':>8}{'max':>8}{'prep s':>8}  meta")
    for f in filas:
        estado = "OK" if f["max_ms"] < META_MS else "SUPERA 20 ms"
        print(f"{'x' + str(f['escala']):>6}{f['salas']:>7}{f['enemigos']:>9}{f['ciclos']:>7}"
              f"{f['min_ms']:>8.3f}{f['mediana_ms']:>9.3f}{f['p95_ms']:>8.3f}"
              f"{f['max_ms']:>8.3f}{f['preparacion_s']:>8}  {estado}")


def main(argumentos=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--escala", type=int, action="append", choices=(1, 10, 50))
    parser.add_argument("--ciclos", type=int, default=1000)
    parser.add_argument("--perfil", action="store_true", help="cProfile del ciclo")
    parser.add_argument("--guardar", action="store_true", help="tabla en docs/evidencia/")
    parser.add_argument("--sospechosos", nargs="*", metavar="ESCENARIO",
                        help="escenarios que fuerzan cada sospechoso del plan (todos si "
                             "no se nombra ninguno)")
    opciones = parser.parse_args(argumentos)
    if opciones.sospechosos is not None:
        return sospechosos(min(opciones.ciclos, 300), opciones.sospechosos or None)
    elegidas = opciones.escala or [1, 10, 50]
    filas = []
    for escala, salas, enemigos in ESCALAS:
        if escala not in elegidas:
            continue
        fila = medir(salas, enemigos, opciones.ciclos, opciones.perfil)
        fila["escala"] = escala
        filas.append(fila)
        if opciones.perfil:
            print(f"--- cProfile x{escala} ---")
            print(fila.pop("perfil"))
    imprimir(filas)
    if opciones.guardar:
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta = os.path.join(raiz, "docs", "evidencia")
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"{datetime.now():%Y-%m-%d}-ciclo-20ms.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"meta_ms": META_MS, "filas": filas}, f, ensure_ascii=False, indent=2)
        print(f"Evidencia: {ruta}")
    return filas


if __name__ == "__main__":
    main()
