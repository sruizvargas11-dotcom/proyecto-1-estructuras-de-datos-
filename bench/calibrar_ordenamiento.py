"""Evidencia reproducible del umbral: python -m bench.calibrar_ordenamiento."""
import json
import platform
from pathlib import Path
from dataclasses import asdict
from bench.casos.ordenamiento import correr, REPETICIONES, MUESTRAS
from bench.medicion import imprimir_tabla


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', required=True)
    args = parser.parse_args()
    filas = correr()
    evidencia = {
        'python': platform.python_version(), 'sistema': platform.platform(),
        'procesador': platform.processor(), 'semillas': [42 + i for i in range(MUESTRAS)],
        'repeticiones': REPETICIONES, 'calentamiento': MUESTRAS,
        'unidad': 'mediana ms por ordenamiento; preparación de Vector excluida',
        'filas': [asdict(f) for f in filas],
    }
    destino = Path(args.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding='utf-8')
    imprimir_tabla(filas)


if __name__ == '__main__':
    main()
