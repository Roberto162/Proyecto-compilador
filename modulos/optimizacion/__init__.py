"""
modulos/optimizacion
====================
Motor de Optimización de Código Intermedio (independiente de la máquina).

Estructura:
  cuadruplo.py       Clase Cuadruplo (IR formal), conversión de los cuádruplos del generador
                     de código intermedio y lector de archivos .cuad
  bloques.py         FASE 1 · Flujo de control: líderes, bloques básicos, grafo de flujo (CFG),
                     ciclos y variables vivas
  pases_locales.py   FASE 2 · Nivel 1, pases LOCALES (dentro de un solo bloque básico):
                     plegado de constantes, simplificación algebraica, subexpresiones comunes
  pases_globales.py  FASE 2 · Nivel 2, pases GLOBALES (entre bloques, usando el CFG):
                     propagación de constantes y copias, código muerto / inalcanzable;
                     y pase de CICLOS: movimiento de código invariante (LICM)
  mirilla.py         FASE 2 · Nivel 3, pase de MIRILLA (pocas instrucciones seguidas):
                     saltos redundantes, cargas/almacenamientos redundantes
  validador.py       FASE 3 · Validación: ejecuta original y optimizado y compara resultados
  optimizador.py     Orquestador: repite los pases hasta que ninguno cambie nada + métricas
  reporte.py         Formato de salida para CLI y GUI

Uso rápido:
    from modulos.optimizacion import optimizar_desde_ast, optimizar_archivo_cuadruplos
"""

import re

from modulos.optimizacion.cuadruplo import Cuadruplo, parsear_cuadruplos, generar_cuadruplos_desde_ast
from modulos.optimizacion.optimizador import (
    PASES, PASES_POR_DEFECTO, NIVELES, DESCRIPCION_PASES, Optimizador, optimizar_programa
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
    "Cuadruplo", "PASES", "PASES_POR_DEFECTO", "NIVELES", "DESCRIPCION_PASES", "Optimizador", "optimizar_programa",
    "optimizar_desde_ast", "optimizar_texto_cuadruplos", "optimizar_archivo_cuadruplos",
    "reoptimizar", "extraer_salidas_fuente", "generar_cuadruplos_desde_ast",
    "parsear_cuadruplos", "reporte",
]