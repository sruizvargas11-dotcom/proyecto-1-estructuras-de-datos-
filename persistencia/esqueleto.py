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
        if not isinstance(cripta_id, str) or not cripta_id:
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
        except FileNotFoundError:
            return None

        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
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

        cripta.finalizar_carga()
        return cripta

