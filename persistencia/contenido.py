import os
import json


class PersistenciaContenido:

    def __init__(self, carpeta_base, version_cripta):
        self._base    = carpeta_base
        self._version = version_cripta

    def _ruta_sala(self, cripta_id, sala_id):
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
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def cargar(self, cripta_id, sala_id):
        if self._version_vigente(cripta_id) != self._version:
            return None
        ruta = self._ruta_sala(cripta_id, sala_id)
        if not os.path.exists(ruta):
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)









