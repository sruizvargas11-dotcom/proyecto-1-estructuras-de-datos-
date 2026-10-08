"""
Adaptador HTTP real de FuenteDeDatos.
Es el único módulo del proyecto que sabe que existe una API REST detrás.
"""

import time
import uuid

import requests

from adaptadores.fuente_datos import FuenteDeDatos

BASE_URL = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"
## Recomendación: Utilizar la API Key como una variable de entorno para no exponerla

class DatosHTTP(FuenteDeDatos):
    """Implementación de FuenteDeDatos que consume el api  de la cripta."""

    def __init__(self, max_reintentos=3):
        if type(max_reintentos) is not int or max_reintentos < 0:
            raise ValueError("max_reintentos debe ser un entero no negativo")
        self._max_reintentos = max_reintentos
        self._base_url = BASE_URL
        self._client_id = str(uuid.uuid4())
        self._headers = {"X-Cripta-Client-Id": self._client_id}
        self._contador = 0
        self._presupuesto = None



    def _get(self, ruta: str, params: dict = None) -> dict:
        """se comunica con el servidor aca pasan los gets """
        reintentos = 0
        while True:
            if self._presupuesto is not None and self._contador >= self._presupuesto:
                raise RuntimeError("Presupuesto de solicitudes agotado.")
            self._contador += 1
            try:
                respuesta = requests.get(
                    f"{self._base_url}{ruta}", headers=self._headers,
                    params=params, timeout=10,
                )
            except requests.RequestException as error:
                raise RuntimeError(f"No se pudo consultar {ruta}: {error}") from error

            if respuesta.status_code == 200:
                datos = respuesta.json()
                if not isinstance(datos, dict):
                    raise ValueError(f"Respuesta JSON inválida en {ruta}")
                return datos

            if respuesta.status_code == 429:
                if reintentos >= self._max_reintentos:
                    raise RuntimeError("El servidor sigue ocupado: límite de reintentos alcanzado.")
                if self._presupuesto is not None and self._contador >= self._presupuesto:
                    raise RuntimeError("Presupuesto de solicitudes agotado.")
                datos = respuesta.json()
                espera = datos.get("reintentar_en", 5) if isinstance(datos, dict) else None
                if type(espera) not in (int, float) or not 0 <= espera <= 60:
                    raise ValueError("Intervalo de reintento inválido o mayor de 60 segundos.")
                time.sleep(espera)
                reintentos += 1
                continue

            raise RuntimeError(
                f"GET {ruta} falló con status {respuesta.status_code}: {respuesta.text}"
            )



    def listar_criptas(self) -> dict:
        """GET #1 — lista de criptas disponibles."""
        return self._get("/criptas")


    def datos_cripta(self, cripta_id: str) -> dict:
        """GET #2 -datos generales y se tiene la cantidad de solicitudes """
        respuesta = self._get(f"/criptas/{cripta_id}")
        presupuesto = respuesta.get("presupuesto_solicitudes")
        if type(presupuesto) is not int or presupuesto < 0:
            raise ValueError("Presupuesto de solicitudes inválido.")
        self._presupuesto = presupuesto
        if self._contador > presupuesto:
            raise RuntimeError("La carga inicial ya excedió el presupuesto informado.")
        return respuesta


    def esqueleto_cripta(self, cripta_id: str, pagina: int) -> dict:
        """"'informacion del esqueleto de la cripta"""
        return self._get(f"/criptas/{cripta_id}/salas", params={"pagina": pagina})

    def contenido_salas(self, cripta_id: str, sala_ids: list) -> dict:
        """"'contenido de salas listado,se permiten 10 salas por solicitud """
        if not sala_ids or len(sala_ids) > 10:
            raise ValueError("tope de maximo 10 salas por solicitud")
        salas = ",".join(str(s) for s in sala_ids)
        return self._get(f"/criptas/{cripta_id}/contenido", params={"salas": salas})

    def catalogo(self, tipo_ids: list) -> dict:
        """"'informacion del catalogo se unen los ids por formato y se verifican el maximo
        10 ids
        """
        if not tipo_ids or len(tipo_ids) > 10:
            raise ValueError("Máximo 10 ids por solicitud")
        ids = ",".join(tipo_ids)
        return self._get("/catalogo", params={"ids": ids})

    def version_cripta(self, cripta_id: str) -> dict:
        """"'version de la cripta """
        return self._get(f"/criptas/{cripta_id}/version")

    def version_catalogo(self) -> dict:
        """"'version del catalogo"""
        return self._get("/catalogo/version")

    """"'metodos momentaneos son para verificar la funcionalidad de la conexion"""
    @property
    def requests_realizados(self) -> int:
        return self._contador

    @property
    def presupuesto(self) -> int:
        return self._presupuesto if self._presupuesto is not None else 0

    @property
    def dentro_del_presupuesto(self) -> bool:
        if self._presupuesto is None:
            return True
        return self._contador <= self._presupuesto

    def reporte(self) -> dict:
        return {
            "client_id": self._client_id,
            "requests_realizados": self._contador,
            "presupuesto": self.presupuesto,
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
