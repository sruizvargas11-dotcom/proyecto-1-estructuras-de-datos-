import json
import os

from persistencia.cache_json import cargar_cache, guardar_cache, validar_identificador



class PersistenciaCatalogo:
    def __init__(self,carpeta,version_catalogo):
        self.carpeta = carpeta
        self.version = version_catalogo
    def ruta_ficha(self,tipo):
        validar_identificador(tipo)
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
        guardar_cache(self.ruta_ficha(tipo), self.version, tipo, f)

    def cargar_ficha(self, tipo_id):
        return cargar_cache(self.ruta_ficha(tipo_id), self.version, tipo_id)
