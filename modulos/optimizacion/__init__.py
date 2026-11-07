"""
modulos/optimizacion
====================
Motor de Optimización de Código Intermedio (independiente de la máquina).

Estructura:
  cuadruplo.py       Representación formal de la IR (clase Cuadruplo) y lector de archivos .cuad
  generador_ir.py    AST -> cuádruplos con etiquetas y saltos (si / sino / mientras)
  bloques.py         FASE 1: líderes, bloques básicos, CFG, dominadores, ciclos, liveness
  pases_locales.py   FASE 2 nivel 1: plegado, simplificación algebraica, CSE local
  pases_globales.py  FASE 2 nivel 2: propagación de constantes/copias, código muerto, LICM
  mirilla.py         FASE 2 nivel 3: saltos redundantes, cargas/almacenamientos redundantes
  validador.py       FASE 3: intérprete y verificación de equivalencia
  optimizador.py     Pipeline (punto fijo) + métricas
  reporte.py         Formato de salida para CLI y GUI
  suite.py           Ejecución de la carpeta /tests y matriz de métricas

Uso rápido:
    from modulos.optimizacion import optimizar_desde_ast, optimizar_archivo_cuadruplos
"""

import re

from modulos.optimizacion.cuadruplo import Cuadruplo, parsear_cuadruplos
from modulos.optimizacion.generador_ir import generar_cuadruplos_desde_ast
from modulos.optimizacion.optimizador import (
    PASES, PASES_POR_DEFECTO, Optimizador, optimizar_programa
)
from modulos.optimizacion import reporte


def extraer_salidas_fuente(codigo_fuente: str):
    """
    Lee la directiva opcional  '# salida: a, b'  del código fuente (es un comentario,
    así que el léxico la ignora). Si no existe, devuelve None (todas las variables).
    """
    m = re.search(r'^\s*#\s*salidas?\s*:\s*(.+)$', codigo_fuente or "", re.MULTILINE | re.IGNORECASE)
    if not m:
        return None
    return {v for v in re.split(r'[,\s]+', m.group(1).strip()) if v}


def optimizar_desde_ast(ast_raiz, codigo_fuente="", pases_activos=None, titulo="Código fuente"):
    """Genera los cuádruplos (con control de flujo) desde el AST y los optimiza."""
    codigo = generar_cuadruplos_desde_ast(ast_raiz)
    return optimizar_programa(codigo, salidas=extraer_salidas_fuente(codigo_fuente),
                              pases_activos=pases_activos, titulo=titulo)


def optimizar_texto_cuadruplos(texto, pases_activos=None, titulo=None):
    prog = parsear_cuadruplos(texto)
    return optimizar_programa(prog.codigo, salidas=prog.salidas, entradas_fijas=prog.entradas,
                              pases_activos=pases_activos, titulo=titulo or prog.titulo or "Cuádruplos",
                              esperado=prog.esperado)


def optimizar_archivo_cuadruplos(ruta, pases_activos=None):
    with open(ruta, "r", encoding="utf-8") as f:
        return optimizar_texto_cuadruplos(f.read(), pases_activos)


def reoptimizar(resultado, pases_activos):
    """Vuelve a optimizar el mismo código original con otra selección de pases."""
    original = [q.con(notas=[]) for q in resultado.original]
    return optimizar_programa(original, salidas=resultado.salidas,
                              entradas_fijas=resultado.entradas_fijas, pases_activos=pases_activos,
                              titulo=resultado.titulo, esperado=resultado.esperado)


__all__ = [
    "Cuadruplo", "PASES", "PASES_POR_DEFECTO", "Optimizador", "optimizar_programa",
    "optimizar_desde_ast", "optimizar_texto_cuadruplos", "optimizar_archivo_cuadruplos",
    "reoptimizar", "extraer_salidas_fuente", "generar_cuadruplos_desde_ast",
    "parsear_cuadruplos", "reporte",
]
