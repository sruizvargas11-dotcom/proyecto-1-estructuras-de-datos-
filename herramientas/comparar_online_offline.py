import os
import sys

from adaptadores.datos_http import DatosHTTP
from adaptadores.datos_offline import CARPETA_POR_DEFECTO, DatosOffline

MAX_POR_LOTE = 10


def agrupar(lista, tamano):
    grupos = []
    for inicio in range(0, len(lista), tamano):
        grupos.append(lista[inicio:inicio + tamano])
    return grupos


def claves_distintas(a, b):
    """Devuelve las claves cuyo valor no coincide entre dos diccionarios."""
    distintas = []
    for clave in list(a.keys()) + list(b.keys()):
        if a.get(clave) != b.get(clave) and clave not in distintas:
            distintas.append(clave)
    return distintas


def comparar(nombre, valor_http, valor_offline):
    """Compara dos respuestas completas. Devuelve True si son iguales."""
    if valor_http == valor_offline:
        print(f"  OK         {nombre}")
        return True
    print(f"  DIFERENTE  {nombre}")
    if isinstance(valor_http, dict) and isinstance(valor_offline, dict):
        for clave in claves_distintas(valor_http, valor_offline):
            print(f"             '{clave}': API={valor_http.get(clave)!r}  offline={valor_offline.get(clave)!r}")
    return False


def buscar(lista, clave, valor):
    for elemento in lista:
        if elemento.get(clave) == valor:
            return elemento
    return None


def comparar_lista(nombre, lista_http, lista_offline, clave):
    """
    Compara dos listas de elementos (salas o fichas) emparejándolos por `clave`.
    El contenido distinto cuenta como error. El orden distinto solo se avisa,
    porque el juego no debe depender del orden en que llega una respuesta.
    """
    iguales = True
    for elemento_offline in lista_offline:
        identificador = elemento_offline[clave]
        elemento_http = buscar(lista_http, clave, identificador)
        if elemento_http is None:
            print(f"  FALTA      {nombre} {identificador}: el API no lo devolvió")
            iguales = False
        elif not comparar(f"{nombre} {identificador}", elemento_http, elemento_offline):
            iguales = False

    for elemento_http in lista_http:
        if buscar(lista_offline, clave, elemento_http[clave]) is None:
            print(f"  FALTA      {nombre} {elemento_http[clave]}: no está en offline")
            iguales = False

    orden_http = [e[clave] for e in lista_http]
    orden_offline = [e[clave] for e in lista_offline]
    if iguales and orden_http != orden_offline:
        print(f"  AVISO      {nombre}: mismo contenido, distinto orden")
        print(f"             API={orden_http}")
        print(f"             offline={orden_offline}")
    return iguales


def main():
    cripta_id = sys.argv[1] if len(sys.argv) > 1 else "cripta-01"
    http = DatosHTTP()
    offline = DatosOffline()
    resultados = []

    print(f"Comparando API vs offline para {cripta_id}\n")

    print("Datos generales y versiones")
    resultados.append(comparar("listar_criptas", http.listar_criptas(), offline.listar_criptas()))
    resultados.append(comparar("datos_cripta", http.datos_cripta(cripta_id), offline.datos_cripta(cripta_id)))
    resultados.append(comparar("version_cripta", http.version_cripta(cripta_id), offline.version_cripta(cripta_id)))
    resultados.append(comparar("version_catalogo", http.version_catalogo(), offline.version_catalogo()))

    print("\nEsqueleto")
    ids_salas = []
    pagina = 1
    total_paginas = 1
    while pagina <= total_paginas:
        respuesta_offline = offline.esqueleto_cripta(cripta_id, pagina)
        respuesta_http = http.esqueleto_cripta(cripta_id, pagina)
        resultados.append(comparar(f"esqueleto pagina {pagina}", respuesta_http, respuesta_offline))
        total_paginas = respuesta_offline["total_paginas"]
        for sala in respuesta_offline["salas"]:
            ids_salas.append(sala["id"])
        pagina += 1

    print("\nContenido (pedido en orden inverso, para probar también el orden)")
    ids_invertidos = ids_salas[::-1]
    for lote in agrupar(ids_invertidos, MAX_POR_LOTE):
        contenido_http = http.contenido_salas(cripta_id, lote)["contenido"]
        contenido_offline = offline.contenido_salas(cripta_id, lote)["contenido"]
        resultados.append(comparar_lista("sala", contenido_http, contenido_offline, "sala"))

    print("\nCatálogo")
    carpeta_catalogo = os.path.join(CARPETA_POR_DEFECTO, "catalogo")
    tipo_ids = []
    for nombre_archivo in os.listdir(carpeta_catalogo):
        if nombre_archivo.endswith(".json"):
            tipo_ids.append(nombre_archivo[:-len(".json")])
    for lote in agrupar(tipo_ids, MAX_POR_LOTE):
        entidades_http = http.catalogo(lote)["entidades"]
        entidades_offline = offline.catalogo(lote)["entidades"]
        resultados.append(comparar_lista("ficha", entidades_http, entidades_offline, "id"))

    coinciden = resultados.count(True)
    print(f"\nResultado: {coinciden} de {len(resultados)} comparaciones coinciden")
    if coinciden == len(resultados):
        print("El modo offline es un reemplazo fiel del API para esta cripta.")
    else:
        print("Hay diferencias: vuelvan a descargar con herramientas.descargar_offline.")
    print(f"Solicitudes de red: {http.reporte()}")

    sys.exit(0 if coinciden == len(resultados) else 1)


if __name__ == "__main__":
    main()
