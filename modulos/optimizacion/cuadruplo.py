"""
modulos/optimizacion/cuadruplo.py
=================================
Representación formal de la IR (Representación Intermedia) usada por el optimizador.

Cada instrucción es un objeto `Cuadruplo(op, arg1, arg2, resultado)`; nunca se
manipula texto plano dentro de los pases. Además del cuádruplo clásico, cada
instrucción guarda:
  - origen : número de la instrucción en el código ORIGINAL (para poder decir
             qué le pasó a cada instrucción en la tabla comparativa).
  - notas  : lista de transformaciones que ha sufrido (columna "Transformación
             aplicada" de los reportes).

Operadores soportados:
  Binarios      : + - * /  == != < > <= >=        (resultado = arg1 op arg2)
  Copia         : =                                (resultado = arg1)
  Control       : label L | goto L | ifFalse c L | ifTrue c L
  Efecto lateral: print x
  Especial      : reverse x                        (x = reverse(x))
"""

import re
from dataclasses import dataclass, field, replace

from config import PREFIJO_TEMPORALES

# ---------------------------------------------------------------------------
# Catálogo de operadores
# ---------------------------------------------------------------------------
OPERADORES_ARITMETICOS = {'+', '-', '*', '/'}
OPERADORES_RELACIONALES = {'==', '!=', '<', '>', '<=', '>='}
OPERADORES_BINARIOS = OPERADORES_ARITMETICOS | OPERADORES_RELACIONALES
OPERADORES_CONMUTATIVOS = {'+', '*', '==', '!='}

OP_COPIA = '='
OP_ETIQUETA = 'label'
OP_GOTO = 'goto'
OP_IF_FALSO = 'ifFalse'
OP_IF_VERDADERO = 'ifTrue'
OP_IMPRIMIR = 'print'
OP_REVERSE = 'reverse'

SALTOS_CONDICIONALES = {OP_IF_FALSO, OP_IF_VERDADERO}
SALTOS = SALTOS_CONDICIONALES | {OP_GOTO}
# Instrucciones que nunca se eliminan por "código muerto" (afectan el flujo o la salida)
CON_EFECTO_LATERAL = SALTOS | {OP_ETIQUETA, OP_IMPRIMIR}

OPERADORES_VALIDOS = OPERADORES_BINARIOS | SALTOS | {OP_COPIA, OP_ETIQUETA, OP_IMPRIMIR, OP_REVERSE}

# ---------------------------------------------------------------------------
# Clasificación de operandos
# ---------------------------------------------------------------------------
_RE_NUMERO = re.compile(r'^-?\d+(\.\d+)?([eE][-+]?\d+)?$')
_RE_IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_RE_TEMPORAL = re.compile(rf'^{re.escape(PREFIJO_TEMPORALES)}\d+$')


def es_numero(s) -> bool:
    return isinstance(s, str) and bool(_RE_NUMERO.match(s))


def es_cadena(s) -> bool:
    return isinstance(s, str) and len(s) >= 2 and s.startswith('"') and s.endswith('"')


def es_constante(s) -> bool:
    return es_numero(s) or es_cadena(s)


def es_variable(s) -> bool:
    return isinstance(s, str) and bool(_RE_IDENT.match(s))


def es_temporal(s) -> bool:
    """Temporales generados por el compilador: t1, t2, ... (según PREFIJO_TEMPORALES)."""
    return isinstance(s, str) and bool(_RE_TEMPORAL.match(s))


def valor_constante(s):
    """Convierte el texto de una constante a su valor Python (int, float o str)."""
    if es_cadena(s):
        return s[1:-1]
    if re.match(r'^-?\d+$', s):
        return int(s)
    return float(s)


def formatear_constante(v) -> str:
    """Convierte un valor Python de vuelta a texto de constante de la IR."""
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, str):
        return f'"{v}"'
    return repr(v)


def evaluar_operacion(op, a, b=None):
    """
    Semántica ÚNICA de los operadores. La usan tanto el plegado de constantes como
    el intérprete del validador, garantizando que plegar no cambie el resultado.
    Lanza ZeroDivisionError / TypeError si la operación no es válida.
    """
    if op == '+':
        if isinstance(a, str) or isinstance(b, str):
            raise TypeError("'+' no está definido para cadenas en este lenguaje")
        return a + b
    if op == '-':
        return a - b
    if op == '*':
        return a * b
    if op == '/':
        if b == 0:
            raise ZeroDivisionError("división entre cero")
        return a / b
    if op == '==':
        return 1 if a == b else 0
    if op == '!=':
        return 1 if a != b else 0
    if op == '<':
        return 1 if a < b else 0
    if op == '>':
        return 1 if a > b else 0
    if op == '<=':
        return 1 if a <= b else 0
    if op == '>=':
        return 1 if a >= b else 0
    if op == OP_REVERSE:
        return str(a)[::-1]
    raise ValueError(f"Operador desconocido: {op}")


def clave_natural(nombre: str):
    """Orden natural para nombres como t2 < t10."""
    m = re.match(r'^(.*?)(\d+)$', nombre)
    return (m.group(1), int(m.group(2))) if m else (nombre, -1)


# ---------------------------------------------------------------------------
# Estructura formal de la instrucción
# ---------------------------------------------------------------------------
@dataclass
class Cuadruplo:
    op: str
    arg1: str = ""
    arg2: str = ""
    resultado: str = ""
    origen: int = None                       # índice 1-based en el código original
    notas: list = field(default_factory=list)  # transformaciones aplicadas

    # ---- Clasificación ---------------------------------------------------
    def es_expresion(self) -> bool:
        return self.op in OPERADORES_BINARIOS

    def es_copia(self) -> bool:
        return self.op == OP_COPIA

    def es_etiqueta(self) -> bool:
        return self.op == OP_ETIQUETA

    def es_salto(self) -> bool:
        return self.op in SALTOS

    def es_salto_condicional(self) -> bool:
        return self.op in SALTOS_CONDICIONALES

    def es_salto_incondicional(self) -> bool:
        return self.op == OP_GOTO

    def tiene_efecto_lateral(self) -> bool:
        return self.op in CON_EFECTO_LATERAL

    @property
    def destino(self):
        """Etiqueta destino de un salto (o nombre de la etiqueta si es 'label')."""
        return self.resultado if (self.es_salto() or self.es_etiqueta()) else None

    # ---- Análisis de flujo de datos --------------------------------------
    def posiciones_uso(self):
        """Nombres de los campos que se LEEN."""
        if self.op in OPERADORES_BINARIOS:
            return ['arg1', 'arg2']
        if self.op in (OP_COPIA, OP_IMPRIMIR, OP_REVERSE) or self.op in SALTOS_CONDICIONALES:
            return ['arg1']
        return []

    def usos(self) -> list:
        """Variables leídas por la instrucción."""
        return [getattr(self, p) for p in self.posiciones_uso() if es_variable(getattr(self, p))]

    def definicion(self):
        """Variable escrita por la instrucción (o None)."""
        if self.op in OPERADORES_BINARIOS or self.op in (OP_COPIA, OP_REVERSE):
            return self.resultado or None
        return None

    # ---- Transformación inmutable ----------------------------------------
    def con(self, nota=None, **cambios):
        """Devuelve una copia modificada conservando 'origen' y acumulando la nota."""
        datos = {"notas": list(self.notas)}
        datos.update(cambios)
        nuevo = replace(self, **datos)
        if nota:
            nuevo.notas.append(nota)
        return nuevo

    def sustituir_usos(self, mapa: dict, nota=None):
        """Reemplaza los operandos leídos según 'mapa'. Devuelve (nuevo, cambió)."""
        cambios = {}
        for pos in self.posiciones_uso():
            val = getattr(self, pos)
            if val in mapa and mapa[val] != val:
                cambios[pos] = mapa[val]
        if not cambios:
            return self, False
        return self.con(nota=nota, **cambios), True

    def tupla(self):
        return (self.op, self.arg1, self.arg2, self.resultado)

    # ---- Presentación ----------------------------------------------------
    def campos_visibles(self):
        return [self.op, self.arg1 or '_', self.arg2 or '_', self.resultado or '_']

    def tac(self) -> str:
        """Forma legible de código de tres direcciones."""
        op, a, b, r = self.op, self.arg1, self.arg2, self.resultado
        if op in OPERADORES_BINARIOS:
            return f"{r} = {a} {op} {b}"
        if op == OP_COPIA:
            return f"{r} = {a}"
        if op == OP_ETIQUETA:
            return f"{r}:"
        if op == OP_GOTO:
            return f"goto {r}"
        if op in SALTOS_CONDICIONALES:
            return f"{op} {a} goto {r}"
        if op == OP_IMPRIMIR:
            return f"print {a}"
        if op == OP_REVERSE:
            return f"{r} = reverse({a})"
        return " ".join(self.campos_visibles())

    def __str__(self):
        return f"({', '.join(self.campos_visibles())})"


def numerar(codigo):
    """Asigna 'origen' (1..n) a un código recién generado o leído."""
    return [q.con(origen=i) for i, q in enumerate(codigo, 1)]


def tuplas(codigo):
    return [q.tupla() for q in codigo]


# ---------------------------------------------------------------------------
# Lectura de archivos de cuádruplos (.cuad)
# ---------------------------------------------------------------------------
@dataclass
class ProgramaCuadruplos:
    titulo: str = ""
    codigo: list = field(default_factory=list)
    salidas: set = None            # variables observables al final (None = todas las de usuario)
    entradas: dict = field(default_factory=dict)   # valores fijos para el validador
    esperado: list = None          # salida esperada (opcional) para comparar


_VACIOS = {'_', '-', '—', ''}


def _parsear_linea(tokens, num_linea):
    if len(tokens) == 5 and re.match(r'^\(?\d+[).:]?$', tokens[0]):
        tokens = tokens[1:]                       # se permite numeración al inicio
    op = tokens[0]
    if op == 'iffalse':
        op = OP_IF_FALSO
    if op == 'iftrue':
        op = OP_IF_VERDADERO
    if op not in OPERADORES_VALIDOS:
        raise ValueError(f"Línea {num_linea}: operador desconocido '{op}'")
    args = [('' if t in _VACIOS else t) for t in tokens[1:]]

    if len(args) == 3:
        a1, a2, r = args
    elif op in (OP_ETIQUETA, OP_GOTO) and len(args) == 1:
        a1, a2, r = '', '', args[0]
    elif op in SALTOS_CONDICIONALES and len(args) == 2:
        a1, a2, r = args[0], '', args[1]
    elif op == OP_IMPRIMIR and len(args) == 1:
        a1, a2, r = args[0], '', ''
    elif op in (OP_COPIA, OP_REVERSE) and len(args) == 2:
        a1, a2, r = args[0], '', args[1]
    else:
        raise ValueError(f"Línea {num_linea}: número de campos inválido para '{op}'")
    return Cuadruplo(op, a1, a2, r)


def _lista_vars(texto):
    return {v.strip() for v in re.split(r'[,\s]+', texto) if v.strip()}


def parsear_cuadruplos(texto: str) -> ProgramaCuadruplos:
    """
    Formato (una instrucción por línea, separada por espacios, tabs o comas):
        # comentario  (la primera línea de comentario se usa como título)
        @salida res, x        -> variables vivas al final del programa
        @entrada x=3, y=4     -> valores fijos para la validación (opcional)
        *   4   10  t1
        =   t7  _   res
        label _ _ L1   (o: label L1)
        ifFalse t2 _ L1 (o: ifFalse t2 L1)
        @esperado             -> lo que sigue es la salida esperada (opcional)
    """
    prog = ProgramaCuadruplos()
    destino = prog.codigo
    for n, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if not s:
            continue
        if s.startswith('#'):
            if not prog.titulo:
                prog.titulo = s.lstrip('#').strip()
            continue
        if '#' in s and '"' not in s:
            s = s.split('#', 1)[0].strip()
        low = s.lower()
        if low.startswith('@titulo'):
            prog.titulo = s[len('@titulo'):].strip()
            continue
        if low.startswith('@salida'):
            prog.salidas = _lista_vars(s[len('@salida'):].replace(':', ' '))
            continue
        if low.startswith('@entrada'):
            for par in re.split(r'[,\s]+', s[len('@entrada'):].replace(':', ' ')):
                if '=' in par:
                    k, v = par.split('=', 1)
                    prog.entradas[k.strip()] = valor_constante(v.strip())
            continue
        if low.startswith('@esperado'):
            prog.esperado = []
            destino = prog.esperado
            continue
        tokens = [t for t in re.split(r'[,\s]+', s.replace('(', ' ').replace(')', ' ')) if t]
        if tokens:
            destino.append(_parsear_linea(tokens, n))
    prog.codigo = numerar(prog.codigo)
    return prog
