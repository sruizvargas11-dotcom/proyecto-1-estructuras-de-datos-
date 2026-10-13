import os
import json

from persistencia.cache_json import cargar_cache, guardar_cache, validar_identificador


class PersistenciaContenido:

    def __init__(self, carpeta_base, version_cripta):
        self._base    = carpeta_base
        self._version = version_cripta

    def _ruta_sala(self, cripta_id, sala_id):
        validar_identificador(cripta_id)
        if type(sala_id) is not int or sala_id < 0:
            raise ValueError("La sala debe ser un entero no negativo.")
        return os.path.join(
            self._base, cripta_id, "contenido", f"sala_{sala_id}.json"
        )

    def _version_vigente(self, cripta_id):
        ruta = os.path.join(self._base, cripta_id, "version.json")
        if not os.path.exists(ruta):
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f).get("version")

    def guardar(self, cripta_id, sala_id, datos):
        ruta = self._ruta_sala(cripta_id, sala_id)
        guardar_cache(ruta, self._version, f"{cripta_id}:{sala_id}", datos)

    def cargar(self, cripta_id, sala_id):
        ruta = self._ruta_sala(cripta_id, sala_id)
        return cargar_cache(ruta, self._version, f"{cripta_id}:{sala_id}")

    def invalidar(self, cripta_id, sala_id):
        """Retira una copia que no permite construir las entidades de la sala."""
        try:
            os.remove(self._ruta_sala(cripta_id, sala_id))
        except FileNotFoundError:
            pass
