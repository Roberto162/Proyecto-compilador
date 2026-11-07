"""
config.py
=========
Módulo de configuración global del compilador.
Contiene:
  - Estilos de consola (colores ANSI).
  - Palabras reservadas y reglas léxicas (Token Regex).
  - Mapeo de terminales sintácticos.
  - Equivalencias de operadores para Código Intermedio (Código P, Cuádruplos, Triplos).
  - Expresiones obligatorias del proyecto integrador (Casos de prueba).
"""

# =====================================================================
# 1. ESTILOS DE SALIDA EN TERMINAL (ANSI COLORS)
# =====================================================================
class Colores:
    """Códigos de escape ANSI para el formateo de texto en consola."""
    ROJO = '\033[91m'
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    CYAN = '\033[96m'
    NEGRITA = '\033[1m'
    RESET = '\033[0m'

# =====================================================================
# 2. CONFIGURACIÓN LÉXICA
# =====================================================================
# Palabras reservadas del lenguaje
KEYWORDS = {
    "complete", "bubble", "chain",
    "si", "sino", "mientras",
    "mostrar", "reverse"
}

# Expresiones regulares para la tokenización (ordenadas por prioridad)
TOKEN_REGEX = [
    ("NUM_DECIMAL", r"\d+\.\d+"),
    ("NUM_ENTERO", r"\d+"),
    ("CADENA", r'"[^"]*"'),
    ("OPERADOR_REL", r"==|!=|<=|>=|<|>"),
    ("OPERADOR_ARIT", r"[+\-*/]"),
    ("ASIGNACION", r"="),
    ("SIMBOLO", r"[:(),]"),
    ("IDENTIFICADOR", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("ESPACIO", r"[ \t]+"),
    ("NEWLINE", r"\n"),
    ("COMENTARIO", r"#.*"),
]

# =====================================================================
# 3. TRADUCCIÓN A TERMINALES SINTÁCTICOS
# =====================================================================
# Mapeo directo de operadores aritméticos a sus terminales gramaticales
MAPEO_OPERADORES_ARIT = {
    '+': 'OP_SUMA',
    '-': 'OP_RESTA',
    '*': 'OP_MULT',
    '/': 'OP_DIV'
}

# Mapeo de símbolos delimitadores a sus terminales gramaticales
MAPEO_SIMBOLOS = {
    ':': 'DOPUNTOS',
    '(': 'LPAR',
    ')': 'RPAR',
    ',': 'COMA'
}

# Precedencia de operadores para la construcción del AST y Código Intermedio, 
#mayor numero significa mayor prioridad
PRECEDENCIA_OPERADORES = {
    '+': 1,
    '-': 1,
    '*': 2,
    '/': 2,
    '==': 0,
    '!=': 0,
    '<': 0,
    '>': 0,
    '<=': 0,
    '>=': 0
}

# =====================================================================
# 4. INSTRUCCIONES PARA CÓDIGO INTERMEDIO 
# =====================================================================
# Mapeo de operadores aritméticos a instrucciones del Código P (Máquina de Pila)
OPCODES_CODIGO_P = {
    '+': 'ADD',
    '-': 'SUB',
    '*': 'MUL',
    '/': 'DIV',
    '==': 'EQ',
    '!=': 'NE',
    '<': 'LT',
    '>': 'GT',
    '<=': 'LE',
    '>=': 'GE',
    '=': 'STORE'
}

# Prefijo predeterminado para variables temporales en Cuádruplos (t1, t2, t3...)
PREFIJO_TEMPORALES = "t"

# =====================================================================
# 5. CASOS DE PRUEBA 
# =====================================================================
EXPRESIONES_PRUEBA_OBLIGATORIAS = [
    {
        "id": "PRUEBA_1",
        "descripcion": "Precedencia y asociatividad (a+b*c-d/e)",
        "expresion": "complete a = 10\ncomplete b = 20\ncomplete c = 5\ncomplete d = 8\ncomplete e = 2\ncomplete resultado = a + b * c - d / e"
    },
    {
        "id": "PRUEBA_2",
        "descripcion": "Paréntesis y subexpresiones ((a+b)*(c-d)/e)",
        "expresion": "complete a = 10\ncomplete b = 20\ncomplete c = 15\ncomplete d = 5\ncomplete e = 2\ncomplete resultado = (a + b) * (c - d) / e"
    },
    {
        "id": "PRUEBA_3",
        "descripcion": "Expresiones anidadas complejas (((a+b)*(c-d))/(e+f*g))",
        "expresion": "complete a = 10\ncomplete b = 20\ncomplete c = 15\ncomplete d = 5\ncomplete e = 2\ncomplete f = 3\ncomplete g = 4\ncomplete resultado = ((a + b) * (c - d)) / (e + f * g)"
    },
    {
        "id": "ERROR_1",
        "descripcion": "Operador colgado al final (Error Sintáctico)",
        "expresion": "complete a = 10\ncomplete b = 20\ncomplete resultado = a + b *"
    },
    {
        "id": "ERROR_2",
        "descripcion": "Variable no declarada (Error Semántico)",
        "expresion": "complete a = 10\ncomplete resultado = a + x"
    }
]