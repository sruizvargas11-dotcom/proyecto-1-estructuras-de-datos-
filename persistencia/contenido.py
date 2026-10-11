import json
import os


class PersistenciaContenido:

    def __init__(self, carpeta_base, version_cripta):
        self._base = carpeta_base
        self._version = version_cripta

    def _ruta_sala(self, cripta_id, sala_id):
        if not isinstance(cripta_id, str) or not cripta_id.strip():
            raise ValueError("El identificador de cripta debe ser texto no vacío.")
        if cripta_id in (".", "..") or any(c in cripta_id for c in "/\\:"):
            raise ValueError("El identificador de cripta no puede contener una ruta.")
        if type(sala_id) is not int or sala_id < 0:
            raise ValueError("El identificador de sala debe ser un entero no negativo.")
        return os.path.join(
            self._base, cripta_id, "contenido", f"sala_{sala_id}.json"
        )

    def guardar(self, cripta_id, sala_id, datos):
        ruta = self._ruta_sala(cripta_id, sala_id)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        temporal = ruta + ".tmp"
        documento = {
            "formato_cache": 1,
            "version": self._version,
            "datos": datos,
        }
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(documento, f, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)

    def cargar(self, cripta_id, sala_id):
        ruta = self._ruta_sala(cripta_id, sala_id)
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                documento = json.load(f)
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(documento, dict):
            return None
        if documento.get("formato_cache") != 1:
            return None
        if documento.get("version") != self._version:
            return None
        return documento.get("datos")
