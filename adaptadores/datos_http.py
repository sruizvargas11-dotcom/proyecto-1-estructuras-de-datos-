"""
Adaptador HTTP real de FuenteDeDatos.
Es el único módulo del proyecto que sabe que existe una API REST detrás.
"""

import time
import uuid

import requests

from adaptadores.fuente_datos import FuenteDeDatos

BASE_URL = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"


class DatosHTTP(FuenteDeDatos):
    """Implementación de FuenteDeDatos que consume el API REST de CRIPTA."""

    def __init__(self):
        self._base_url = BASE_URL
        self._client_id = str(uuid.uuid4())
        self._headers = {"X-Cripta-Client-Id": self._client_id}
        self._contador = 0
        self._presupuesto = 0



    def _get(self, ruta: str, params: dict = None) -> dict:
        """Único punto que habla con el servidor. Todo GET pasa por aquí."""
        while True:
            respuesta = requests.get(
                f"{self._base_url}{ruta}",
                headers=self._headers,
                params=params,
                timeout=10,
            )
            self._contador += 1

            if respuesta.status_code == 200:
                return respuesta.json()

            if respuesta.status_code == 429:
                espera = respuesta.json().get("reintentar_en", 5)
                time.sleep(espera)
                continue

            raise RuntimeError(
                f"GET {ruta} falló con status {respuesta.status_code}: {respuesta.text}"
            )



    def listar_criptas(self) -> dict:
        """GET #1 — lista de criptas disponibles."""
        return self._get("/criptas")


    def datos_cripta(self, cripta_id: str) -> dict:
        """GET #2 — datos generales de una cripta. Fija el presupuesto de solicitudes."""
        respuesta = self._get(f"/criptas/{cripta_id}")
        self._presupuesto = respuesta["presupuesto_solicitudes"]
        return respuesta


    def esqueleto_cripta(self, cripta_id: str, pagina: int) -> dict:

        return self._get(f"/criptas/{cripta_id}/salas", params={"pagina": pagina})

    def contenido_salas(self, cripta_id: str, sala_ids: list) -> dict:

        if len(sala_ids) > 10:
            raise ValueError("Máximo 10 salas por solicitud")
        salas = ",".join(str(s) for s in sala_ids)
        return self._get(f"/criptas/{cripta_id}/contenido", params={"salas": salas})

    def catalogo(self, tipo_ids: list) -> dict:

        if len(tipo_ids) > 10:
            raise ValueError("Máximo 10 ids por solicitud")
        ids = ",".join(tipo_ids)
        return self._get("/catalogo", params={"ids": ids})

    def version_cripta(self, cripta_id: str) -> dict:

        return self._get(f"/criptas/{cripta_id}/version")

    def version_catalogo(self) -> dict:

        return self._get("/catalogo/version")

    @property
    def requests_realizados(self) -> int:
        return self._contador

    @property
    def presupuesto(self) -> int:
        return self._presupuesto

    @property
    def dentro_del_presupuesto(self) -> bool:
        if self._presupuesto == 0:
            return True
        return self._contador <= self._presupuesto

    def reporte(self) -> dict:
        return {
            "client_id": self._client_id,
            "requests_realizados": self._contador,
            "presupuesto": self._presupuesto,
            "dentro_del_limite": self.dentro_del_presupuesto,
        }


"""
explicacion general del flujo de trabajo se crea una interfaz comun fuente_datos.py
esta es la interfaz que se va a comunicar con nuestro modelo de esta se genera un adaptador htpp
encargada de la conexion de la api y los gets primero declaramos la url de la api ,
de ahi la clase con sus respectivos variables  url declarada previamente , cliente con su
uuid unico ,header que pide el profe en el enunciado xd , un contador de respuestas 
y una variable de presupuesto para gestionar y medir el presupuesto de solicitud ,
---como trabajamos el json-----
   en  def _get(self, ruta: str, params: dict = None) -> dict: 
   recibimos una ruta,parametros enviados por referencia y un diccionario para leer el json
   en la variable respuesta que guarda la ruta , los parametros osea la informacion contenida en el json
   por cada solicitud o entrada el contador aumenta y ahora si hacemos la confirmacion que
   pide el profe en el enunciado si la respuesta ==200 se procesa o se lee 
   se hacen 2 validaciones mas el resto de funciones hasta las que dicen property 
   son los otros get con sus validaciones de limite de consultas

   las otras funciones ignorenla de momento son para verificar la consulta del json eventuamente se van a quitar
   otra cosa se crea un archivo verificar momentaneo para que vean los gets y la consulta hecha por la api
   la carpeta test son hechos por AI que verifican el codigo , por cada flujo se van hacer test
   para que todo este joya

"""