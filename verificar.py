"""Script de prueba real contra el API de CRIPTA. Sin mocks."""

from adaptadores.datos_http import DatosHTTP

def main():
    http = DatosHTTP()

    print("=" * 50)
    print("GET #1 — Listar criptas")
    print("=" * 50)
    criptas = http.listar_criptas()
    for c in criptas["criptas"]:
        print(f"  {c['id']} — {c['nombre']} ({c['salas']} salas)")

    cripta_id = criptas["criptas"][0]["id"]

    print(f"\n{'=' * 50}")
    print(f"GET #2 — Datos generales de {cripta_id}")
    print("=" * 50)
    datos = http.datos_cripta(cripta_id)
    print(f"  Versión:      {datos['version']}")
    print(f"  Sala inicial: {datos['sala_inicial']}")
    print(f"  Sala salida:  {datos['sala_salida']}")
    print(f"  Presupuesto:  {datos['presupuesto_solicitudes']}")
    print(f"  Inventario:   {datos['inventario_max']}")
    print(f"  Jugador:      {datos['jugador']}")

    print(f"\n{'=' * 50}")
    print(f"GET #3 — Esqueleto página 1")
    print("=" * 50)
    esqueleto = http.esqueleto_cripta(cripta_id, 1)
    print(f"  Página {esqueleto['pagina']} de {esqueleto['total_paginas']}")
    print(f"  Salas en esta página: {len(esqueleto['salas'])}")
    for sala in esqueleto["salas"][:3]:
        print(f"    Sala {sala['id']}: {sala['nombre']}")
        print(f"    Salidas: {list(sala['salidas'].keys())}")

    print(f"\n{'=' * 50}")
    print(f"GET #4 — Contenido salas 1, 2, 3")
    print("=" * 50)
    ids_salas = [s["id"] for s in esqueleto["salas"][:3]]
    contenido = http.contenido_salas(cripta_id, ids_salas)
    for c in contenido["contenido"]:
        print(f"  Sala {c['sala']}:")
        print(f"    Enemigos: {len(c['enemigos'])}")
        print(f"    Objetos:  {len(c['objetos'])}")
        print(f"    Trampas:  {len(c['trampas'])}")

    print(f"\n{'=' * 50}")
    print(f"GET #5 — Catálogo de tipos encontrados")
    print("=" * 50)
    tipos = set()
    for c in contenido["contenido"]:
        for e in c["enemigos"]:
            tipos.add(e["tipo"])
        for o in c["objetos"]:
            tipos.add(o)
        for t in c["trampas"]:
            tipos.add(t["tipo"])
    if tipos:
        fichas = http.catalogo(list(tipos)[:10])
        for f in fichas["entidades"]:
            print(f"  {f['id']} ({f['clase']}): {f['nombre']}")
    else:
        print("  Sin tipos nuevos en estas salas")

    print(f"\n{'=' * 50}")
    print(f"GET #6 — Versión de la cripta")
    print("=" * 50)
    version = http.version_cripta(cripta_id)
    print(f"  {version}")

    print(f"\n{'=' * 50}")
    print(f"GET #7 — Versión del catálogo")
    print("=" * 50)
    version_cat = http.version_catalogo()
    print(f"  {version_cat}")

    print(f"\n{'=' * 50}")
    print("REPORTE FINAL")
    print("=" * 50)
    reporte = http.reporte()
    print(f"  Client ID:           {reporte['client_id']}")
    print(f"  Requests realizados: {reporte['requests_realizados']}")
    print(f"  Presupuesto:         {reporte['presupuesto']}")
    print(f"  Dentro del límite:   {reporte['dentro_del_limite']}")


if __name__ == "__main__":
    main()
