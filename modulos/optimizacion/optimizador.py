"""
modulos/optimizacion/optimizador.py
===================================
Orquestador del motor de optimización:

   [ Código intermedio original ]
              │
     1. Partición en bloques básicos + CFG          (bloques.py)
     2. Pipeline de pases hasta punto fijo          (pases_*.py, mirilla.py)
     3. Reensamblado                                (cada pase devuelve lista lineal)
              │
   [ Código intermedio optimizado ] ──> Validador + Métricas (validador.py)
"""

from dataclasses import dataclass, field

from config import OPT_MAX_RONDAS
from modulos.optimizacion.cuadruplo import (
    es_temporal, es_variable, clave_natural, tuplas, OPERADORES_BINARIOS, OPERADORES_ARITMETICOS
)
from modulos.optimizacion.bloques import particionar
from modulos.optimizacion.contexto import ContextoOptimizacion
from modulos.optimizacion.pases_locales import (
    pase_plegado_constantes, pase_simplificacion_algebraica, pase_cse_local
)
from modulos.optimizacion.pases_globales import (
    pase_propagacion_constantes, pase_propagacion_copias, pase_codigo_muerto, pase_licm
)
from modulos.optimizacion.mirilla import pase_mirilla
from modulos.optimizacion.validador import validar


# Catálogo de pases en el orden en que se ejecutan dentro de cada ronda.
#   clave: (nombre visible, nivel, función)
PASES = {
    "plegado":     ("Plegado de constantes",                       "Nivel 1 · Local",  pase_plegado_constantes),
    "algebraica":  ("Simplificación algebraica / reducción de fuerza", "Nivel 1 · Local", pase_simplificacion_algebraica),
    "cse":         ("Eliminación de subexpresiones comunes (CSE)", "Nivel 1 · Local",  pase_cse_local),
    "prop_const":  ("Propagación de constantes",                   "Nivel 2 · Global", pase_propagacion_constantes),
    "prop_copias": ("Propagación de copias",                       "Nivel 2 · Global", pase_propagacion_copias),
    "dce":         ("Eliminación de código muerto / inalcanzable", "Nivel 2 · Global", pase_codigo_muerto),
    "licm":        ("Movimiento de código invariante (LICM)",      "Nivel 2 · Ciclos", pase_licm),
    "mirilla":     ("Mirilla: saltos y cargas redundantes",        "Nivel 3 · Mirilla", pase_mirilla),
}
PASES_POR_DEFECTO = list(PASES.keys())


@dataclass
class PasoTraza:
    ronda: int
    clave: str
    nombre: str
    nivel: str
    mensajes: list
    antes: list
    despues: list


@dataclass
class ResultadoOptimizacion:
    titulo: str
    original: list
    optimizado: list
    salidas: set
    entradas_fijas: dict
    pases_activos: list
    traza: list = field(default_factory=list)
    eliminadas: dict = field(default_factory=dict)
    rondas: int = 0
    validacion: object = None
    metricas: dict = field(default_factory=dict)
    esperado: list = None

    @property
    def coincide_esperado(self):
        if self.esperado is None:
            return None
        return tuplas(self.optimizado) == tuplas(self.esperado)


def variables_usuario(codigo):
    """Variables asignadas en el programa que no son temporales del compilador."""
    return {d for d in _definidas(codigo) if es_variable(d) and not es_temporal(d)}


def _definidas(codigo):
    return {q.definicion() for q in codigo if q.definicion()}


def calcular_metricas(original, optimizado, validacion):
    def contar(c, pred):
        return sum(1 for q in c if pred(q))

    temps_o = {d for d in _definidas(original) if es_temporal(d)}
    temps_p = {d for d in _definidas(optimizado) if es_temporal(d)}
    user_o = {d for d in _definidas(original) if not es_temporal(d)}
    user_p = {d for d in _definidas(optimizado) if not es_temporal(d)}
    n_o, n_p = len(original), len(optimizado)
    m = {
        "instr_antes": n_o,
        "instr_despues": n_p,
        "reduccion_pct": (100.0 * (n_o - n_p) / n_o) if n_o else 0.0,
        "temporales_antes": len(temps_o),
        "temporales_despues": len(temps_p),
        "temporales_eliminados": sorted(temps_o - temps_p, key=clave_natural),
        "variables_eliminadas": sorted(user_o - user_p, key=clave_natural),
        "ops_antes": contar(original, lambda q: q.op in OPERADORES_BINARIOS),
        "ops_despues": contar(optimizado, lambda q: q.op in OPERADORES_BINARIOS),
        "arit_antes": contar(original, lambda q: q.op in OPERADORES_ARITMETICOS),
        "arit_despues": contar(optimizado, lambda q: q.op in OPERADORES_ARITMETICOS),
        "saltos_antes": contar(original, lambda q: q.es_salto()),
        "saltos_despues": contar(optimizado, lambda q: q.es_salto()),
        "etiquetas_antes": contar(original, lambda q: q.es_etiqueta()),
        "etiquetas_despues": contar(optimizado, lambda q: q.es_etiqueta()),
        "bloques_antes": len(particionar(original)),
        "bloques_despues": len(particionar(optimizado)),
    }
    if validacion is not None:
        m.update({
            "dinamicas_antes": validacion.pasos_original,
            "dinamicas_despues": validacion.pasos_optimizado,
            "dinamicas_arit_antes": validacion.ops_original,
            "dinamicas_arit_despues": validacion.ops_optimizado,
            "reduccion_dinamica_pct": (100.0 * (validacion.pasos_original - validacion.pasos_optimizado)
                                       / validacion.pasos_original) if validacion.pasos_original else 0.0,
            "equivalente": validacion.equivalente,
        })
    return m


class Optimizador:
    def __init__(self, codigo, salidas=None, pases_activos=None, max_rondas=OPT_MAX_RONDAS):
        self.original = list(codigo)
        # Si no se indican variables de salida se asume (de forma conservadora)
        # que TODAS las variables del usuario son observables al final.
        self.salidas = set(salidas) if salidas else variables_usuario(self.original)
        self.pases_activos = [p for p in PASES if p in (pases_activos or PASES_POR_DEFECTO)]
        self.max_rondas = max_rondas

    def optimizar(self):
        ctx = ContextoOptimizacion(self.salidas)
        codigo = list(self.original)
        traza = []
        rondas = 0
        for ronda in range(1, self.max_rondas + 1):
            rondas = ronda
            hubo_cambio = False
            for clave in self.pases_activos:
                nombre, nivel, funcion = PASES[clave]
                ctx.pase_actual = nombre
                ctx.mensajes = []
                antes = codigo
                codigo = funcion(codigo, ctx)
                if tuplas(codigo) != tuplas(antes):
                    hubo_cambio = True
                    traza.append(PasoTraza(ronda, clave, nombre, nivel, list(ctx.mensajes), antes, codigo))
            if not hubo_cambio:
                break
        return codigo, traza, ctx.eliminadas, rondas


def optimizar_programa(codigo, salidas=None, entradas_fijas=None, pases_activos=None,
                       titulo="Programa", esperado=None):
    """API principal: optimiza, valida y calcula métricas."""
    opt = Optimizador(codigo, salidas, pases_activos)
    optimizado, traza, eliminadas, rondas = opt.optimizar()
    val = validar(opt.original, optimizado, opt.salidas, entradas_fijas)
    res = ResultadoOptimizacion(
        titulo=titulo, original=opt.original, optimizado=optimizado, salidas=opt.salidas,
        entradas_fijas=entradas_fijas or {}, pases_activos=opt.pases_activos, traza=traza,
        eliminadas=eliminadas, rondas=rondas, validacion=val, esperado=esperado,
    )
    res.metricas = calcular_metricas(opt.original, optimizado, val)
    return res
