"""
modulos/optimizacion/generador_ir.py
====================================
Conexión entre el Generador de Código Intermedio y el optimizador.

El optimizador NO genera código: toma los cuádruplos que produce
`modulos/codigo_intermedio.py` (lista de diccionarios) y los convierte en
objetos `Cuadruplo`, la estructura formal sobre la que trabajan los pases.

    [ AST ] -> codigo_intermedio.generar_cuadruplos() -> [ dicts ] -> Cuadruplo(...) -> optimizador
"""

from modulos.codigo_intermedio import GeneradorCodigoIntermedio
from modulos.optimizacion.cuadruplo import Cuadruplo, numerar


def convertir_cuadruplos(lista_dicts):
    """Convierte la salida del generador ({'operador','arg1','arg2','resultado'}) a objetos Cuadruplo."""
    return numerar([Cuadruplo(d["operador"], d["arg1"], d["arg2"], d["resultado"]) for d in lista_dicts])


def generar_cuadruplos_desde_ast(ast_raiz):
    """Punto de entrada: AST -> cuádruplos del generador de código intermedio -> lista de Cuadruplo."""
    return convertir_cuadruplos(GeneradorCodigoIntermedio(ast_raiz).generar_cuadruplos())