"""
modulos/optimizacion/suite.py
=============================
Ejecuta todos los archivos de la carpeta /tests:
  *.cuad -> archivos de cuádruplos (se optimizan directamente)
  *.txt  -> código fuente del lenguaje (léxico -> sintáctico -> semántico -> IR -> optimización)
y arma la matriz comparativa de métricas.
"""

import os

from config import DIRECTORIO_TESTS
from modulos.optimizacion import optimizar_archivo_cuadruplos, optimizar_desde_ast


def optimizar_archivo_fuente(ruta, pases_activos=None):
    from modulos.semantico import ejecutar_pipeline_completo
    with open(ruta, "r", encoding="utf-8") as f:
        codigo = f.read()
    valido, err_lex, err_sint, rep_sem, _, ast = ejecutar_pipeline_completo(codigo)
    if not valido or ast is None:
        errores = err_lex + err_sint
        raise ValueError("el código fuente tiene errores: " + ("; ".join(errores) if errores else rep_sem))
    return optimizar_desde_ast(ast, codigo, pases_activos, titulo=os.path.basename(ruta))


def listar_tests(directorio=DIRECTORIO_TESTS):
    if not os.path.isdir(directorio):
        return []
    return sorted(os.path.join(directorio, f) for f in os.listdir(directorio)
                  if f.endswith((".cuad", ".txt")))


def ejecutar_archivo(ruta, pases_activos=None):
    if ruta.endswith(".cuad"):
        return optimizar_archivo_cuadruplos(ruta, pases_activos)
    return optimizar_archivo_fuente(ruta, pases_activos)


def ejecutar_suite(directorio=DIRECTORIO_TESTS, pases_activos=None):
    filas = []
    for ruta in listar_tests(directorio):
        nombre = os.path.basename(ruta)
        try:
            filas.append({"archivo": nombre, "resultado": ejecutar_archivo(ruta, pases_activos)})
        except Exception as e:
            filas.append({"archivo": nombre, "error": str(e)})
    return filas
