"""
modulos/optimizacion/validador.py
=================================
FASE 3 — Validador de semántica.

Ejecuta el código intermedio ORIGINAL y el OPTIMIZADO en un intérprete de
cuádruplos y compara:
  * el valor final de las variables de salida,
  * lo impreso con 'print' (mostrar),
  * los errores en tiempo de ejecución (p. ej. división entre cero).

Las variables de entrada (leídas antes de ser asignadas, p. ej. 'x' o 'limite')
se detectan con el análisis de vida y se prueban con varios juegos de valores
aleatorios reproducibles (semilla fija). También se cuentan las instrucciones
ejecutadas (métrica dinámica, útil para LICM).
"""

import math
import random
from dataclasses import dataclass, field

from config import (OPT_PRUEBAS_VALIDACION, OPT_SEMILLA_VALIDACION,
                    OPT_RANGO_ENTRADAS, OPT_MAX_PASOS_EJECUCION)
from modulos.optimizacion.cuadruplo import (
    es_constante, valor_constante, evaluar_operacion, OPERADORES_BINARIOS,
    OPERADORES_ARITMETICOS, OP_COPIA, OP_GOTO, OP_IF_FALSO, OP_IF_VERDADERO,
    OP_IMPRIMIR, OP_REVERSE
)
from modulos.optimizacion.bloques import particionar, analisis_vida


@dataclass
class Ejecucion:
    memoria: dict = field(default_factory=dict)
    impresiones: list = field(default_factory=list)
    pasos: int = 0
    ops_aritmeticas: int = 0
    error: str = None
    agotado: bool = False


def ejecutar(codigo, entradas=None, max_pasos=OPT_MAX_PASOS_EJECUCION):
    """Intérprete de cuádruplos."""
    ej = Ejecucion(memoria=dict(entradas or {}))
    etiquetas = {q.resultado: i for i, q in enumerate(codigo) if q.es_etiqueta()}

    def leer(x):
        if es_constante(x):
            return valor_constante(x)
        if x not in ej.memoria:
            raise NameError(f"variable '{x}' sin valor")
        return ej.memoria[x]

    pc = 0
    try:
        while pc < len(codigo):
            if ej.pasos >= max_pasos:
                ej.agotado = True
                break
            q = codigo[pc]
            pc += 1
            if q.es_etiqueta():
                continue                      # las etiquetas no son instrucciones ejecutables
            ej.pasos += 1
            op = q.op
            if op in OPERADORES_BINARIOS:
                ej.memoria[q.resultado] = evaluar_operacion(op, leer(q.arg1), leer(q.arg2))
                if op in OPERADORES_ARITMETICOS:
                    ej.ops_aritmeticas += 1
            elif op == OP_COPIA:
                ej.memoria[q.resultado] = leer(q.arg1)
            elif op == OP_GOTO:
                pc = etiquetas[q.resultado]
            elif op in (OP_IF_FALSO, OP_IF_VERDADERO):
                cond = bool(leer(q.arg1))
                if (op == OP_IF_FALSO and not cond) or (op == OP_IF_VERDADERO and cond):
                    pc = etiquetas[q.resultado]
            elif op == OP_IMPRIMIR:
                ej.impresiones.append(leer(q.arg1))
            elif op == OP_REVERSE:
                ej.memoria[q.resultado] = evaluar_operacion(OP_REVERSE, leer(q.arg1))
    except Exception as e:                    # error de ejecución reproducible
        ej.error = f"{type(e).__name__}: {e}"
    return ej


def detectar_entradas(codigo):
    """Variables que se leen antes de cualquier asignación (entradas del programa)."""
    bloques = particionar(codigo)
    if not bloques:
        return set()
    live_in, _ = analisis_vida(bloques, set())
    return set(live_in[0])


def _iguales(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        try:
            return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        except OverflowError:
            return a == b
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return a == b


@dataclass
class ResultadoValidacion:
    equivalente: bool
    variables_comparadas: list
    entradas: list
    corridas: list            # dicts con detalle por corrida
    pasos_original: float
    pasos_optimizado: float
    ops_original: float
    ops_optimizado: float
    observaciones: list


def validar(original, optimizado, salidas, entradas_fijas=None,
            pruebas=OPT_PRUEBAS_VALIDACION, semilla=OPT_SEMILLA_VALIDACION):
    entradas_fijas = entradas_fijas or {}
    vars_entrada = sorted(detectar_entradas(original) | detectar_entradas(optimizado))
    variables = sorted(salidas)
    rng = random.Random(semilla)
    n = pruebas if vars_entrada else 1
    corridas, obs = [], []
    equivalente = True

    for k in range(n):
        valores = {}
        for v in vars_entrada:
            if k == 0 and v in entradas_fijas:
                valores[v] = entradas_fijas[v]
            else:
                valores[v] = rng.randint(*OPT_RANGO_ENTRADAS)
        e1 = ejecutar(original, valores)
        e2 = ejecutar(optimizado, valores)
        difs = []
        if e1.agotado or e2.agotado:
            obs.append(f"Corrida {k + 1}: se alcanzó el límite de pasos (posible ciclo infinito)")
        if (e1.error is None) != (e2.error is None):
            difs.append(f"error: '{e1.error}' vs '{e2.error}'")
        for v in variables:
            a, b = e1.memoria.get(v, '<sin valor>'), e2.memoria.get(v, '<sin valor>')
            if not _iguales(a, b):
                difs.append(f"{v}: {a} vs {b}")
        if len(e1.impresiones) != len(e2.impresiones) or not all(
                _iguales(a, b) for a, b in zip(e1.impresiones, e2.impresiones)):
            difs.append(f"print: {e1.impresiones} vs {e2.impresiones}")
        if difs:
            equivalente = False
        corridas.append({
            "entradas": valores,
            "original": {v: e1.memoria.get(v) for v in variables},
            "optimizado": {v: e2.memoria.get(v) for v in variables},
            "impresiones": (e1.impresiones, e2.impresiones),
            "pasos": (e1.pasos, e2.pasos),
            "ops": (e1.ops_aritmeticas, e2.ops_aritmeticas),
            "errores": (e1.error, e2.error),
            "diferencias": difs,
        })

    prom = lambda i, key: sum(c[key][i] for c in corridas) / len(corridas)
    return ResultadoValidacion(
        equivalente=equivalente,
        variables_comparadas=variables,
        entradas=vars_entrada,
        corridas=corridas,
        pasos_original=prom(0, "pasos"), pasos_optimizado=prom(1, "pasos"),
        ops_original=prom(0, "ops"), ops_optimizado=prom(1, "ops"),
        observaciones=obs,
    )
