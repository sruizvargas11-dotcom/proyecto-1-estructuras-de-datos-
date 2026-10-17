"""Tabla local de resultados: Vector propio y persistencia JSON."""

import json
import os
import tempfile
from pathlib import Path

from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar


RESULTADOS = ("victoria", "derrota", "en_curso")

CAMPOS = (
    "nombre",
    "cripta_id",
    "version_cripta",
    "acciones_jugador",
    "enemigos_derrotados",
    "tiempo_final",
    "resultado",
)


class Puntaje:
    """Resultado de una partida.

    en_curso identifica una sesión interrumpida sin victoria ni derrota.
    """

    def __init__(self, nombre, cripta_id, version_cripta,
                 acciones_jugador, enemigos_derrotados, tiempo_final,
                 resultado="en_curso"):

        for campo, valor in (
            ("nombre", nombre),
            ("cripta_id", cripta_id),
            ("version_cripta", version_cripta),
        ):
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"{campo} debe ser un texto no vacío.")

        for campo, valor in (
            ("acciones_jugador", acciones_jugador),
            ("enemigos_derrotados", enemigos_derrotados),
            ("tiempo_final", tiempo_final),
        ):
            if type(valor) is not int or valor < 0:
                raise ValueError(
                    f"{campo} debe ser un entero no negativo."
                )

        if resultado not in RESULTADOS:
            raise ValueError("Resultado de partida inválido.")

        self.nombre = nombre.strip()
        self.cripta_id = cripta_id.strip()
        self.version_cripta = version_cripta.strip()
        self.acciones_jugador = acciones_jugador
        self.enemigos_derrotados = enemigos_derrotados
        self.tiempo_final = tiempo_final
        self.resultado = resultado

    @property
    def nombre_jugador(self):
        return self.nombre

    def a_datos(self):
        """Prepara los campos para JSON."""
        return {
            campo: getattr(self, campo)
            for campo in CAMPOS
        }

    @classmethod
    def desde_datos(cls, datos):
        """Construye y valida un puntaje leído desde JSON."""
        if (
            not isinstance(datos, dict)
            or len(datos) != len(CAMPOS)
            or any(campo not in datos for campo in CAMPOS)
        ):
            raise ValueError(
                "El registro de puntaje tiene campos inválidos."
            )

        return cls(**datos)


def comparar_puntajes(a, b):
    """Agrupa por cripta y versión; clasifica dentro de cada grupo.

    Prioridades:
    1. Victoria, derrota y sesión interrumpida.
    2. Más enemigos derrotados.
    3. Menos acciones.
    4. Menor tiempo virtual.
    """

    def clave(puntaje):
        return (
            puntaje.cripta_id,
            puntaje.version_cripta,
            RESULTADOS.index(puntaje.resultado),
            -puntaje.enemigos_derrotados,
            puntaje.acciones_jugador,
            puntaje.tiempo_final,
        )

    izquierda = clave(a)
    derecha = clave(b)

    return (izquierda > derecha) - (izquierda < derecha)


class TablaPuntajes:
    """Mantiene los registros ordenados en un Vector propio."""

    def __init__(self):
        self._puntajes = Vector()

    def __len__(self):
        return len(self._puntajes)

    def obtener(self, indice):
        """Devuelve una copia para proteger el orden interno."""
        puntaje = self._puntajes.obtenerValor(indice)
        return Puntaje.desde_datos(puntaje.a_datos())

    def _posicion_insercion(self, puntaje):
        """Busca en O(log n) dónde insertar después de los empates."""
        izquierda = 0
        derecha = len(self._puntajes)

        while izquierda < derecha:
            medio = (izquierda + derecha) // 2
            actual = self._puntajes.obtenerValor(medio)

            if comparar_puntajes(actual, puntaje) <= 0:
                izquierda = medio + 1
            else:
                derecha = medio

        return izquierda

    def agregar(self, puntaje):
        """Inserta en orden: búsqueda O(log n) y desplazamiento O(n)."""
        if not isinstance(puntaje, Puntaje):
            raise TypeError(
                "La tabla solo acepta objetos Puntaje."
            )

        # La tabla conserva su propio registro validado.
        copia = Puntaje.desde_datos(puntaje.a_datos())
        posicion = self._posicion_insercion(copia)
        cantidad = len(self._puntajes)

        # Abrir un espacio al final; el Vector crece si hace falta.
        self._puntajes.agregarValor(copia)

        # Desplazar de derecha a izquierda para no perder registros.
        for indice in range(cantidad, posicion, -1):
            anterior = self._puntajes.obtenerValor(indice - 1)
            self._puntajes.asignarValor(indice, anterior)

        self._puntajes.asignarValor(posicion, copia)
        return posicion + 1

    def a_datos(self):
        """Prepara los registros para JSON sin exponer los originales."""
        return [
            puntaje.a_datos()
            for puntaje in self._puntajes
        ]

    @classmethod
    def cargar(cls, ruta):
        """Lee una tabla completa.

        Archivo inexistente: tabla vacía.
        Archivo dañado o incompatible: error, sin sobrescribirlo.
        """
        tabla = cls()

        try:
            with open(ruta, encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except FileNotFoundError:
            return tabla
        except (json.JSONDecodeError, UnicodeError) as error:
            raise ValueError(
                "El archivo de puntajes está dañado."
            ) from error

        # Formato del PR24: convertir en memoria y validar antes de escribir.
        if isinstance(datos, dict) and 'formato_puntajes' in datos:
            if (len(datos) != 2 or type(datos['formato_puntajes']) is not int
                    or datos['formato_puntajes'] != 1
                    or not isinstance(datos.get('registros'), list)):
                raise ValueError('Formato de puntajes incompatible.')
            registros = []
            for original in datos['registros']:
                if not isinstance(original, dict):
                    raise ValueError('Registro de puntaje inválido.')
                registro = original.copy()  # representación JSON, no índice
                if 'nombre_jugador' not in registro or 'nombre' in registro:
                    raise ValueError('Nombre de puntaje inválido.')
                registro['nombre'] = registro.pop('nombre_jugador')
                if type(registro.get('version_cripta')) is int:
                    registro['version_cripta'] = str(registro['version_cripta'])
                registros.append(registro)
            datos = {'formato': 1, 'puntajes': registros}

        if (
            not isinstance(datos, dict)
            or len(datos) != 2
            or type(datos.get("formato")) is not int
            or datos["formato"] != 1
            or not isinstance(datos.get("puntajes"), list)
        ):
            raise ValueError("Formato de puntajes incompatible.")

        anterior = None
        esta_ordenada = True

        for registro in datos["puntajes"]:
            puntaje = Puntaje.desde_datos(registro)

            if (
                anterior is not None
                and comparar_puntajes(anterior, puntaje) > 0
            ):
                esta_ordenada = False

            tabla._puntajes.agregarValor(puntaje)
            anterior = puntaje

        # Una tabla guardada normalmente ya viene ordenada.
        # Si alguien alteró su orden, usamos el selector propio.
        if not esta_ordenada:
            ordenar(tabla._puntajes, comparar_puntajes)

        return tabla

    def guardar(self, ruta):
        """Escribe un temporal y después reemplaza el archivo destino."""
        registros = self.a_datos()

        for registro in registros:
            Puntaje.desde_datos(registro)

        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=destino.parent,
                prefix=".puntajes-",
                suffix=".tmp",
                delete=False,
            ) as archivo:
                temporal = Path(archivo.name)

                json.dump(
                    {
                        "formato": 1,
                        "puntajes": registros,
                    },
                    archivo,
                    ensure_ascii=False,
                    indent=4,
                    allow_nan=False,
                )

                archivo.flush()
                os.fsync(archivo.fileno())

            os.replace(temporal, destino)

        finally:
            if temporal is not None and temporal.exists():
                temporal.unlink()


def registrar_puntaje(ruta, puntaje):
    """Carga la tabla, incorpora un resultado y guarda la actualización."""
    tabla = TablaPuntajes.cargar(ruta)
    tabla.agregar(puntaje)
    tabla.guardar(ruta)

    return tabla