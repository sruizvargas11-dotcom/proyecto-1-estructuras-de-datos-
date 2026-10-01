import json
import os
from adaptadores.fuente_datos import FuenteDeDatos


class DatosOffline(FuenteDeDatos):

    CARPETA = "datos_offline"

    def __init__(self):
        if not os.path.exists(self.CARPETA):
            raise FileNotFoundError(
                f"Carpeta '{self.CARPETA}' no encontrada. "
                f"Verifica que la carpeta '{self.CARPETA}' exista en la raíz del "
                "proyecto y contenga los archivos JSON de la cripta."
            )


    def _leer(self, nombre_archivo):
        ruta = os.path.join(self.CARPETA, nombre_archivo)
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"Archivo offline no encontrado: '{ruta}'. ")
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)



    def listar_criptas(self):
        return self._leer("criptas.json")

    def datos_cripta(self, cripta_id):
        if not cripta_id:
            raise ValueError("informacion de cripta vacia ")
        return self._leer(f"{cripta_id}_general.json")

    def esqueleto_cripta(self, cripta_id, pagina):
        if not cripta_id:
            raise ValueError("id de la cripta no puede ser vacio.")
        if pagina < 1:
            raise ValueError(f"numero pagina invalido {pagina}")
        return self._leer(f"{cripta_id}_salas_p{pagina}.json")

    def contenido_salas(self, cripta_id, sala_ids):
        if not sala_ids:
            raise ValueError("sala_ids no puede estar vacío.")
        if len(sala_ids) > 10:
            raise ValueError(
                f"Máximo 10 salas por consulta, recibido: {len(sala_ids)}"
            )
        nombre = "_".join(str(x) for x in sala_ids)
        return self._leer(f"{cripta_id}_contenido_{nombre}.json")

    def catalogo(self, tipo_ids):
        if not tipo_ids:
            raise ValueError("tipo_ids no puede estar vacío.")
        if len(tipo_ids) > 10:
            raise ValueError(
                f"Máximo 10 ids por consulta, recibido: {len(tipo_ids)}"
            )
        nombre = "_".join(sorted(tipo_ids))
        return self._leer(f"catalogo_{nombre}.json")

    def version_cripta(self, cripta_id):
        if not cripta_id:
            raise ValueError("id de la cripta  no puede estar vacio.")
        return self._leer(f"{cripta_id}_version.json")

    def version_catalogo(self):
        return self._leer("catalogo_version.json")

    def modo(self):
        return "offline"


""" la informacion recibida de la api se almacena en un json, un json por cada get basicamente
se hace un wrapper funcion que guarda un json normal y se implementa y se llama en el resto de metodos
 ,validaciones que pide el profe en el enunciado en las demas funciones heredadas se llama al
 wrapper y con el archivo por leer,manejo de excepciones en caso de errores 
 




"""


