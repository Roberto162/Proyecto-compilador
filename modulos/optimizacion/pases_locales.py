"""
modulos/optimizacion/pases_locales.py
=====================================
FASE 2 — NIVEL 1: Optimizaciones locales (dentro de cada bloque básico).

  * Plegado de constantes (Constant Folding)
        t1 = 4 * 10            ->  t1 = 40
        ifFalse 0 goto L1      ->  goto L1      (condición constante)
  * Simplificación algebraica y reducción de fuerza
        x * 1 -> x   x + 0 -> x   x * 0 -> 0   x - x -> 0   x * 2 -> x + x
  * Eliminación de subexpresiones comunes locales (CSE) con tabla de
    expresiones disponibles por bloque.
"""

from modulos.optimizacion.cuadruplo import (
    Cuadruplo, es_numero, es_constante, es_variable, valor_constante, formatear_constante,
    evaluar_operacion, OPERADORES_BINARIOS, OPERADORES_CONMUTATIVOS,
    OP_COPIA, OP_GOTO, OP_IF_FALSO, OP_REVERSE
)
from modulos.optimizacion.bloques import particionar, reensamblar


# ---------------------------------------------------------------------------
# Funciones puras reutilizables (también las usa la propagación de constantes)
# ---------------------------------------------------------------------------
def plegar(q):
    """
    Intenta evaluar en compilación una instrucción con operandos constantes.
    Devuelve (nueva_instruccion | None si se elimina, descripcion) o None si no aplica.
    """
    if q.op in OPERADORES_BINARIOS and es_numero(q.arg1) and es_numero(q.arg2):
        try:
            v = evaluar_operacion(q.op, valor_constante(q.arg1), valor_constante(q.arg2))
        except (ZeroDivisionError, TypeError):
            return None                      # no se pliega: se conserva el error en ejecución
        c = formatear_constante(v)
        desc = f"Plegado: {q.arg1} {q.op} {q.arg2} = {c}"
        return q.con(nota=desc, op=OP_COPIA, arg1=c, arg2=""), desc

    if q.op == OP_REVERSE and q.arg1 and q.arg1.startswith('"'):
        c = formatear_constante(evaluar_operacion(OP_REVERSE, valor_constante(q.arg1)))
        desc = f"Plegado: reverse({q.arg1}) = {c}"
        return q.con(nota=desc, op=OP_COPIA, arg1=c), desc

    if q.es_salto_condicional() and es_constante(q.arg1):
        verdadero = bool(valor_constante(q.arg1))
        salta = (not verdadero) if q.op == OP_IF_FALSO else verdadero
        if salta:
            desc = f"Condición constante ({q.arg1}): salto siempre se toma"
            return q.con(nota=desc, op=OP_GOTO, arg1=""), desc
        return None, f"Condición constante ({q.arg1}): el salto nunca se toma"
    return None


def simplificar(q):
    """Identidades algebraicas y reducción de fuerza. Devuelve (nueva, desc) o None."""
    if q.op not in ('+', '-', '*', '/'):
        return None
    a, b, r = q.arg1, q.arg2, q.resultado

    def num(x):
        return valor_constante(x) if es_numero(x) else None

    va, vb = num(a), num(b)

    def copia(fuente, regla):
        return q.con(nota=f"Simplificación: {regla}", op=OP_COPIA, arg1=fuente, arg2=""), regla

    if q.op == '+':
        if vb == 0:
            return copia(a, f"{a} + 0 -> {a}")
        if va == 0:
            return copia(b, f"0 + {b} -> {b}")
    elif q.op == '-':
        if vb == 0:
            return copia(a, f"{a} - 0 -> {a}")
        if es_variable(a) and a == b:
            return copia("0", f"{a} - {a} -> 0")
    elif q.op == '*':
        if vb == 1:
            return copia(a, f"{a} * 1 -> {a}")
        if va == 1:
            return copia(b, f"1 * {b} -> {b}")
        if vb == 0 or va == 0:
            return copia("0", f"{a} * {b} -> 0")
        if vb == 2 and es_variable(a):
            regla = f"Reducción de fuerza: {a} * 2 -> {a} + {a}"
            return q.con(nota=regla, op='+', arg1=a, arg2=a), regla
        if va == 2 and es_variable(b):
            regla = f"Reducción de fuerza: 2 * {b} -> {b} + {b}"
            return q.con(nota=regla, op='+', arg1=b, arg2=b), regla
    elif q.op == '/':
        if vb == 1:
            return copia(a, f"{a} / 1 -> {a}")
    return None


# ---------------------------------------------------------------------------
# Pases
# ---------------------------------------------------------------------------
def _pase_por_instruccion(codigo, ctx, funcion):
    nuevo = []
    for q in codigo:
        res = funcion(q)
        if res is None:
            nuevo.append(q)
            continue
        q2, desc = res
        if q2 is None:
            ctx.eliminar(q, desc)
        else:
            ctx.log(f"{q.tac():<24} ->  {q2.tac():<20} [{desc}]")
            nuevo.append(q2)
    return nuevo


def pase_plegado_constantes(codigo, ctx):
    return _pase_por_instruccion(codigo, ctx, plegar)


def pase_simplificacion_algebraica(codigo, ctx):
    return _pase_por_instruccion(codigo, ctx, simplificar)


def _clave(q):
    a, b = q.arg1, q.arg2
    if q.op in OPERADORES_CONMUTATIVOS and b < a:
        a, b = b, a
    return (q.op, a, b)


def pase_cse_local(codigo, ctx):
    """Eliminación de subexpresiones comunes con tabla de expresiones disponibles por bloque."""
    bloques = particionar(codigo)
    for b in bloques:
        disponibles = {}                      # (op, a, b) -> variable que ya contiene el valor
        nuevas = []
        for q in b.instrucciones:
            if q.es_expresion():
                k = _clave(q)
                if k in disponibles:
                    previo = disponibles[k]
                    q2 = q.con(nota=f"CSE: reutiliza {previo} ({q.arg1} {q.op} {q.arg2})",
                               op=OP_COPIA, arg1=previo, arg2="")
                    ctx.log(f"{q.tac():<24} ->  {q2.tac():<20} [subexpresión común en {b.nombre}]")
                    q = q2
            d = q.definicion()
            if d:
                # 'd' cambia: se invalidan las expresiones que la usan o la contenían
                disponibles = {k: v for k, v in disponibles.items()
                               if v != d and d not in (k[1], k[2])}
                if q.es_expresion() and d not in (q.arg1, q.arg2):
                    disponibles[_clave(q)] = d
            nuevas.append(q)
        b.instrucciones = nuevas
    return reensamblar(bloques)
