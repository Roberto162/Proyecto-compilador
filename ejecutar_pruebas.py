"""
ejecutar_pruebas.py
===================
Ejecuta la suite de /tests y muestra la matriz comparativa de métricas.

Uso:
    python ejecutar_pruebas.py            # matriz de métricas
    python ejecutar_pruebas.py -v         # + reporte completo de cada archivo
    python ejecutar_pruebas.py tests/caso4_licm.cuad   # reporte completo de un archivo

Código de salida 0 si todos los casos preservan la semántica (y coinciden con la
salida esperada cuando el archivo la define); 1 en otro caso.
"""

import sys

from modulos.optimizacion import reporte
from modulos.optimizacion.suite import ejecutar_suite, ejecutar_archivo


def main(argv):
    archivos = [a for a in argv if not a.startswith("-")]
    if archivos:
        for ruta in archivos:
            print(reporte.reporte_completo(ejecutar_archivo(ruta)))
        return 0

    filas = ejecutar_suite()
    if "-v" in argv:
        for f in filas:
            if "resultado" in f:
                print(reporte.reporte_completo(f["resultado"]))
                print("\n" + "#" * 92 + "\n")
    print(reporte.matriz_suite(filas))

    ok = all("resultado" in f and f["resultado"].metricas["equivalente"]
             and f["resultado"].coincide_esperado is not False for f in filas)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
