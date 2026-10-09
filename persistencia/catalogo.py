import json
import os



class PersistenciaCatalogo:
    def __init__(self,carpeta,version_catalogo):
        self.carpeta = carpeta
        self.version = version_catalogo
    def ruta_ficha(self,tipo):
        return os.path.join(self.carpeta, "catalogo", f"{tipo}.json")
    def ruta_version(self):
        return os.path.join(self.carpeta, "catalogo_version.json")
    def version_catalogo(self):
        path = self.ruta_version()
        if not os.path.exists(path):
            return {}
        with open(path) as json_file:
            return json.load(json_file)
    def guardar_ficha(self,tipo,f):
        path = self.ruta_ficha(tipo)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as json_file:
            json.dump(f, json_file)

    def cargar_ficha(self, tipo_id):
        if self.version_catalogo() != self.version:
            return None
        ruta = self.ruta_ficha(tipo_id)
        if not os.path.exists(ruta):
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)





