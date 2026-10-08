import json
from pathlib import Path

from modelo.mundo.cripta_modelo import CriptaModelo
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida


class PersistenciaEsqueleto:
    def __init__(self, carpeta_base=None):
        if carpeta_base is None:
            raiz = Path(__file__).resolve().parent.parent
            carpeta_base = raiz / "partidas" / "cache"

        self._carpeta_base = Path(carpeta_base)

    def _ruta(self, cripta_id):
        if not isinstance(cripta_id, str) or not cripta_id.strip():
            raise ValueError("El identificador debe ser un texto no vacío.")

        if cripta_id in (".", "..") or any(
            c in cripta_id for c in '/\\:'
        ):
            raise ValueError("El identificador no puede contener una ruta.")

        return self._carpeta_base / cripta_id / "esqueleto.json"

    def guardar_esqueleto(self, cripta):
        """Llamar al terminar la carga inicial, antes de jugar."""
        if not isinstance(cripta.version, str) or not cripta.version.strip():
            raise ValueError("La cripta debe tener una versión válida.")

        datos = {
            "formato": 1,
            "id": cripta.id,
            "version": cripta.version,
            "sala_inicial_id": cripta.sala_inicial_id,
            "sala_salida_id": cripta.sala_salida_id,
            "llave_salida": cripta.llave_salida,
            "presupuesto_solicitudes": cripta.presupuesto_solicitudes,
            "inventario_max": cripta.inventario_max,
            "salas": [],
        }

        for sala in cripta.recorrer_salas():
            salidas = []

            for salida in sala.salidas.recorrer_valores():
                salidas.append({
                    "direccion": salida.direccion,
                    "sala_destino_id": salida.sala_destino_id,
                    "cerrada": salida.cerrada,
                    "llave": salida.llave,
                    "cierre_automatico": salida.cierre_automatico,
                })

            datos["salas"].append({
                "id": sala.id,
                "nombre": sala.nombre,
                "salidas": salidas,
            })

        if not self._estructura_valida(datos):
            raise ValueError("El esqueleto contiene campos inválidos.")
        # Exigir un modelo finalizado y destinos existentes antes de tocar el disco.
        for identificador in (cripta.sala_inicial_id, cripta.sala_salida_id):
            if cripta.sala_por_id(identificador) is None:
                raise ValueError("Sala inicial o de salida inexistente.")
        for sala in cripta.recorrer_salas():
            for salida in sala.salidas.recorrer_valores():
                if cripta.sala_por_id(salida.sala_destino_id) is None:
                    raise ValueError("Una salida apunta a una sala inexistente.")
        texto = json.dumps(datos, ensure_ascii=False, indent=2)

        ruta = self._ruta(cripta.id)
        ruta.parent.mkdir(parents=True, exist_ok=True)

        temporal = ruta.with_suffix(".tmp")
        temporal.write_text(texto, encoding="utf-8")
        temporal.replace(ruta)

    def cargar_esqueleto(self, cripta_id, version_actual):
        if not isinstance(version_actual, str) or not version_actual.strip():
            raise ValueError(
                "Se necesita la versión actual para validar la copia."
            )

        ruta = self._ruta(cripta_id)

        try:
            texto = ruta.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            return None

        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            return None

        if not self._estructura_valida(datos):
            return None

        if (
            datos["formato"] != 1
            or datos["id"] != cripta_id
            or datos["version"] != version_actual
        ):
            return None

        cripta = CriptaModelo(
            datos["id"],
            datos["version"],
            datos["sala_inicial_id"],
            datos["sala_salida_id"],
            datos["llave_salida"],
            datos["presupuesto_solicitudes"],
            datos["inventario_max"],
        )

        for dato_sala in datos["salas"]:
            sala = Sala(dato_sala["id"], dato_sala["nombre"])

            for dato_salida in reversed(dato_sala["salidas"]):
                salida = Salida(
                    dato_salida["direccion"],
                    dato_salida["sala_destino_id"],
                    dato_salida["cerrada"],
                    dato_salida["llave"],
                    dato_salida["cierre_automatico"],
                )

                sala.salidas.insertar_al_inicio(salida)

            cripta.agregar_sala(sala)

        try:
            cripta.finalizar_carga()
        except ValueError:
            return None

        if (cripta.sala_por_id(cripta.sala_inicial_id) is None
                or cripta.sala_por_id(cripta.sala_salida_id) is None):
            return None
        for sala in cripta.recorrer_salas():
            for salida in sala.salidas.recorrer_valores():
                if cripta.sala_por_id(salida.sala_destino_id) is None:
                    return None
        return cripta


    @staticmethod
    def _estructura_valida(datos):
        """Validar el documento JSON antes de construir objetos del modelo."""
        if not isinstance(datos, dict):
            return False
        campos = ("formato", "id", "version", "sala_inicial_id",
                  "sala_salida_id", "llave_salida", "presupuesto_solicitudes",
                  "inventario_max", "salas")
        if any(campo not in datos for campo in campos):
            return False
        if type(datos["formato"]) is not int:
            return False
        if any(not isinstance(datos[c], str) or not datos[c]
               for c in ("id", "version")):
            return False
        if any(type(datos[c]) is not int for c in
               ("sala_inicial_id", "sala_salida_id", "presupuesto_solicitudes", "inventario_max")):
            return False
        if datos["presupuesto_solicitudes"] < 0 or datos["inventario_max"] < 0:
            return False
        if datos["llave_salida"] is not None and not isinstance(datos["llave_salida"], str):
            return False
        if not isinstance(datos["salas"], list) or not datos["salas"]:
            return False
        for sala in datos["salas"]:
            if not isinstance(sala, dict):
                return False
            if type(sala.get("id")) is not int or not isinstance(sala.get("nombre"), str):
                return False
            if not isinstance(sala.get("salidas"), list):
                return False
            direcciones = []
            for salida in sala["salidas"]:
                if not isinstance(salida, dict) or any(c not in salida for c in
                        ("direccion", "sala_destino_id", "cerrada", "llave", "cierre_automatico")):
                    return False
                direccion = salida["direccion"]
                if direccion not in ("N", "S", "E", "O") or direccion in direcciones:
                    return False
                direcciones.append(direccion)
                if type(salida["sala_destino_id"]) is not int or type(salida["cerrada"]) is not bool:
                    return False
                if salida["llave"] is not None and not isinstance(salida["llave"], str):
                    return False
                cierre = salida["cierre_automatico"]
                if cierre is not None and (type(cierre) is not int or cierre < 0):
                    return False
        return True
