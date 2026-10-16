import json
import os
import sys
from adaptadores.datos_http import DatosHTTP

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA = os.path.join(RAIZ, "datos_offline") # los datos de la cripta siempre se guardan en datos_offline
MAX_POR_LOTE = 10


def guardar(ruta, objeto): # crea las carpetas que hagan falta
    ruta = os.path.join(CARPETA, ruta)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(objeto, archivo, ensure_ascii=False, indent=2)
    print(f" Guardado: {ruta}")

def agrupar(lista, tamano): # Divide las consultas para respetar el límite de cada solicitud.
    grupos = []
    for i in range(0, len(lista), tamano):
        grupos.append(lista[i:i + tamano])
    return grupos

def agregar_sin_repetir(lista, valor): # Evita duplicados sin cambiar el orden de descubrimiento.
    if valor not in lista:
        lista.append(valor)

def main():
    """Descarga los datos de una cripta para poder jugar sin conexión."""
    http = DatosHTTP()
    cripta_id = sys.argv[1] if len(sys.argv) > 1 else "cripta-01"
    guardar("criptas.json", http.listar_criptas())
    guardar(os.path.join(cripta_id, "general.json"), http.datos_cripta(cripta_id))
    guardar(os.path.join(cripta_id, "version.json"), http.version_cripta(cripta_id))

    # Recorre todas las páginas del mapa y reúne los identificadores de sala.
    ids_salas = []
    pagina = 1
    total_paginas = 1
    while pagina <= total_paginas:
        respuesta = http.esqueleto_cripta(cripta_id, pagina)
        guardar(os.path.join(cripta_id, f"salas_p{pagina}.json"), respuesta)
        total_paginas = respuesta["total_paginas"]
        for sala in respuesta["salas"]:
            ids_salas.append(sala["id"])
        pagina += 1

    # Descarga el contenido en lotes y guarda un archivo por sala.
    tipos = []
    for lote in agrupar(ids_salas, MAX_POR_LOTE):
        respuesta = http.contenido_salas(cripta_id, lote)
        for sala in respuesta["contenido"]:
            guardar(os.path.join(cripta_id, "contenido", f"sala_{sala['sala']}.json"), sala)
            for enemigo in sala["enemigos"]:
                agregar_sin_repetir(tipos, enemigo["tipo"])
            for objeto in sala["objetos"]:
                agregar_sin_repetir(tipos, objeto)
            for trampa in sala["trampas"]:
                agregar_sin_repetir(tipos, trampa["tipo"])

    # Resuelve el catálogo, incluidos los tipos que aparecen en el botín.
    i = 0
    while i < len(tipos):
        lote = tipos[i:i + MAX_POR_LOTE]
        respuesta = http.catalogo(lote)
        for ficha in respuesta["entidades"]:
            guardar(os.path.join("catalogo", f"{ficha['id']}.json"), ficha)
            for suelto in ficha.get("suelta", []):
                agregar_sin_repetir(tipos, suelto)
        i += len(lote)

    guardar("catalogo_version.json", http.version_catalogo())
    print(http.reporte())


if __name__ == "__main__":
    main()