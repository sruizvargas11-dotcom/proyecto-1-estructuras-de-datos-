"""Tabla local de puntajes (enunciado §2.12).

Al terminar una partida con victoria o derrota se registra el nombre del
jugador, el id y la versión de la cripta, las acciones del jugador, los
enemigos derrotados y el tiempo final del reloj virtual. La tabla vive en
partidas/puntajes.json y se mantiene siempre ordenada.

Los registros se guardan en un Vector propio. Agregar uno lo coloca al final y
ejecuta InsertionSort: como el resto de la tabla ya está ordenado, solo el
registro nuevo puede estar fuera de lugar y hay como máximo n - 1 inversiones,
así que el costo es O(n). Se llama a insertion_sort directamente y no al
selector ordenar(): con más de 50 registros el selector vería un par
desordenado y pasaría a MergeSort, O(n log n), sin aprovechar que la tabla
está casi ordenada.

El nombre del jugador sale de SesionPartida.nombre_jugador, que la consola o
la portada de Pygame ya validaron (nunca vacío). Los dict y list de este
módulo solo son la representación de transporte JSON; la tabla en memoria es
el Vector.
"""
import json
import os
import tempfile

from estructuras.ordenamientos import insertion_sort
from estructuras.vector_dinamico import Vector

FORMATO_PUNTAJES = 1
VICTORIA = "victoria"
DERROTA = "derrota"
RESULTADOS = (VICTORIA, DERROTA)
CAMPOS = ("nombre_jugador", "cripta_id", "version_cripta", "acciones_jugador",
          "enemigos_derrotados", "tiempo_final", "resultado")


class ErrorTablaPuntajes(ValueError):
    """El archivo de puntajes existe pero no tiene un formato válido."""


def _entero_no_negativo(valor, campo):
    # bool es subclase de int en Python; True no es una cantidad válida.
    if type(valor) is not int or valor < 0:
        raise ValueError(f"{campo} debe ser un entero mayor o igual que 0.")
    return valor


def _texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{campo} debe ser texto no vacío.")
    return valor


class RegistroPuntaje:
    """Una fila de la tabla: el resultado de una partida terminada."""

    def __init__(self, nombre_jugador, cripta_id, version_cripta, acciones_jugador,
                 enemigos_derrotados, tiempo_final, resultado):
        self.nombre_jugador = _texto(nombre_jugador, "nombre_jugador")
        self.cripta_id = _texto(cripta_id, "cripta_id")
        if type(version_cripta) not in (str, int) or version_cripta == "":
            raise ValueError("version_cripta debe ser texto o entero.")
        self.version_cripta = version_cripta
        self.acciones_jugador = _entero_no_negativo(acciones_jugador, "acciones_jugador")
        self.enemigos_derrotados = _entero_no_negativo(enemigos_derrotados,
                                                       "enemigos_derrotados")
        self.tiempo_final = _entero_no_negativo(tiempo_final, "tiempo_final")
        if resultado not in RESULTADOS:
            raise ValueError("resultado debe ser 'victoria' o 'derrota'.")
        self.resultado = resultado

    @classmethod
    def desde_sesion(cls, sesion):
        """Toma los datos de una sesión cuya partida terminó en victoria o derrota."""
        partida = sesion.partida
        if partida.estado not in RESULTADOS:
            raise ValueError("Solo se registran partidas terminadas en victoria o derrota.")
        return cls(sesion.nombre_jugador, partida.cripta_id, partida.version_cripta,
                   partida.acciones_jugador, partida.enemigos_derrotados,
                   partida.reloj.tiempo_actual, partida.estado)

    @classmethod
    def desde_json(cls, datos):
        if not isinstance(datos, dict):
            raise ValueError("cada registro debe ser un objeto JSON.")
        faltantes = [campo for campo in CAMPOS if campo not in datos]
        if faltantes:
            raise ValueError(f"faltan campos en un registro: {', '.join(faltantes)}.")
        return cls(*(datos[campo] for campo in CAMPOS))

    def a_json(self):
        return {campo: getattr(self, campo) for campo in CAMPOS}

    def __repr__(self):
        return (f"RegistroPuntaje({self.nombre_jugador!r}, {self.cripta_id!r}, "
                f"{self.resultado}, t={self.tiempo_final}, acciones={self.acciones_jugador}, "
                f"derrotados={self.enemigos_derrotados})")


def _comparar_numeros(a, b):
    return (a > b) - (a < b)


def comparar_puntajes(a, b):
    """Comparador para insertion_sort: negativo si 'a' va antes que 'b'.

    1. Una victoria va antes que una derrota.
    2. Más enemigos derrotados va antes.
    3. Entre victorias, menor tiempo final (escapó más rápido); entre
       derrotas, mayor tiempo final (sobrevivió más).
    4. Menos acciones del jugador va antes.
    Si todo empata devuelve 0 e InsertionSort, que es estable, deja primero
    el registro más antiguo.
    """
    if a.resultado != b.resultado:
        return -1 if a.resultado == VICTORIA else 1
    diferencia = _comparar_numeros(b.enemigos_derrotados, a.enemigos_derrotados)
    if diferencia:
        return diferencia
    if a.resultado == VICTORIA:
        diferencia = _comparar_numeros(a.tiempo_final, b.tiempo_final)
    else:
        diferencia = _comparar_numeros(b.tiempo_final, a.tiempo_final)
    if diferencia:
        return diferencia
    return _comparar_numeros(a.acciones_jugador, b.acciones_jugador)


class TablaPuntajes:
    """Tabla de puntajes persistida en JSON y ordenada con InsertionSort."""

    def __init__(self, ruta):
        self.ruta = ruta
        self.registros = Vector()

    def __len__(self):
        return len(self.registros)

    def __iter__(self):
        return iter(self.registros)

    def cargar(self):
        """Lee el archivo; si no existe, la tabla queda vacía.

        También se ordena al cargar: si el archivo ya estaba ordenado cuesta
        O(n), y si alguien lo editó a mano se corrige el orden.
        """
        registros = Vector()
        if os.path.exists(self.ruta):
            try:
                with open(self.ruta, encoding="utf-8") as archivo:
                    documento = json.load(archivo)
            except (UnicodeError, json.JSONDecodeError) as error:
                raise ErrorTablaPuntajes(
                    f"'{self.ruta}' no es un archivo de puntajes válido: {error}") from error
            if (not isinstance(documento, dict)
                    or documento.get("formato_puntajes") != FORMATO_PUNTAJES
                    or not isinstance(documento.get("registros"), list)):
                raise ErrorTablaPuntajes(
                    f"'{self.ruta}' no tiene el formato de puntajes {FORMATO_PUNTAJES}.")
            for numero, datos in enumerate(documento["registros"], 1):
                try:
                    registros.agregarValor(RegistroPuntaje.desde_json(datos))
                except ValueError as error:
                    raise ErrorTablaPuntajes(
                        f"Registro {numero} inválido en '{self.ruta}': {error}") from error
            insertion_sort(registros, comparar_puntajes)
        self.registros = registros
        return self

    def agregar(self, registro):
        """Inserta el registro en su lugar y devuelve su posición (desde 1)."""
        if not isinstance(registro, RegistroPuntaje):
            raise TypeError("Solo se agregan objetos RegistroPuntaje.")
        self.registros.agregarValor(registro)
        insertion_sort(self.registros, comparar_puntajes)
        return self.posicion(registro)

    def posicion(self, registro):
        """Posición (desde 1) de ese registro exacto, o None si no está."""
        numero = 1
        for actual in self.registros:
            if actual is registro:
                return numero
            numero += 1
        return None

    def guardar(self):
        """Escribe la tabla de forma atómica: un fallo deja intacto el archivo anterior."""
        documento = {"formato_puntajes": FORMATO_PUNTAJES,
                     "registros": [registro.a_json() for registro in self.registros]}
        # Serializar primero: un error de datos no toca la copia anterior.
        texto = json.dumps(documento, ensure_ascii=False, indent=2)
        carpeta = os.path.dirname(os.path.abspath(self.ruta))
        os.makedirs(carpeta, exist_ok=True)
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=carpeta,
                                             prefix=".puntajes-", suffix=".tmp",
                                             delete=False) as archivo:
                temporal = archivo.name
                archivo.write(texto)
            os.replace(temporal, self.ruta)
            temporal = None
        finally:
            if temporal is not None:
                try:
                    os.remove(temporal)
                except OSError:
                    pass

    def registrar(self, sesion):
        """Registra la partida terminada de la sesión y devuelve el registro creado.

        Se vuelve a leer el archivo antes de agregar, para no perder registros
        escritos por otra ejecución. Si el archivo está dañado se lanza
        ErrorTablaPuntajes y no se sobrescribe.
        """
        registro = RegistroPuntaje.desde_sesion(sesion)
        self.cargar()
        self.agregar(registro)
        self.guardar()
        return registro
