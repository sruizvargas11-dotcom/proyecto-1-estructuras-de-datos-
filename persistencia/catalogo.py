import json
import os


class PersistenciaCatalogo:
    def __init__(self, carpeta, version_catalogo):
        self.carpeta = carpeta
        self.version = version_catalogo

    def ruta_ficha(self, tipo):
        if not isinstance(tipo, str) or not tipo.strip():
            raise ValueError("El tipo_id debe ser texto no vacío.")
        if tipo in (".", "..") or any(c in tipo for c in "/\\:"):
            raise ValueError("El tipo_id no puede contener una ruta.")
        return os.path.join(self.carpeta, "catalogo", f"{tipo}.json")

    def ruta_version(self):
        return os.path.join(self.carpeta, "catalogo_version.json")

    def version_catalogo(self):
        path = self.ruta_version()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    def guardar_ficha(self, tipo, ficha):
        ruta = self.ruta_ficha(tipo)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        temporal = ruta + ".tmp"
        documento = {
            "formato_cache": 1,
            "version": self.version,
            "ficha": ficha,
        }
        with open(temporal, "w", encoding="utf-8") as json_file:
            json.dump(documento, json_file, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)

    def cargar_ficha(self, tipo_id):
        ruta = self.ruta_ficha(tipo_id)
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                documento = json.load(f)
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(documento, dict):
            return None
        if documento.get("formato_cache") != 1:
            return None
        if documento.get("version") != self.version:
            return None
        return documento.get("ficha")
