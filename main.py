import uuid
import requests
BASE_URL = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"
client_id = str(uuid.uuid4())
headers = {"X-Cripta-Client-Id": client_id}
respuesta = requests.get(
f"{BASE_URL}/criptas",
headers=headers,
timeout=10,
)
print(respuesta.status_code)
print(respuesta.json())