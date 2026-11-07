"""
modulos/sintactico.py
=====================
Analizador Sintáctico LL(1) (descenso recursivo) que construye el Árbol de Sintaxis Abstracta (AST).

Gramática:
    P            -> Sentencias EOF
    Sentencias   -> Sentencia Sentencias | ε
    Sentencia    -> Declaracion | Asignacion | Condicional | Ciclo | Impresion | OpEspecial | ExprRel
    Declaracion  -> (COMPLETE | BUBBLE | CHAIN) ID [ '=' ExprRel ] FinSentencia
    Asignacion   -> ID '=' ExprRel FinSentencia
    Condicional  -> SI ExprRel ':' Bloque [ SINO ':' Bloque ]
    Ciclo        -> MIENTRAS ExprRel ':' Bloque
    Impresion    -> MOSTRAR '(' ExprRel { ',' ExprRel } ')' FinSentencia
    OpEspecial   -> REVERSE '(' ID ')' FinSentencia | REVERSE ID '=' ExprRel FinSentencia
    Bloque       -> Sentencia                          (en la misma línea que ':')
                  | NEWLINE Sentencias-indentadas      (líneas con más sangría que el 'si'/'mientras')
    ExprRel      -> ExprArit [ OP_REL ExprArit ]
    ExprArit     -> Term E'          E' -> (+|-) Term E' | ε
    Term         -> Factor T'        T' -> (*|/) Factor T' | ε
    Factor       -> '(' ExprRel ')' | ID | NUM_ENTERO | NUM_DECIMAL | CADENA | '-' Factor
    FinSentencia -> NEWLINE | EOF

Bloques por SANGRÍA (como Python): el cuerpo de un 'si', 'sino' o 'mientras' lo forman las
líneas con mayor sangría (columna) que la palabra que lo abre. El 'sino' debe ir en la misma
columna que su 'si'. La sangría se obtiene de la columna que el léxico registra en cada token.

Recuperación de errores en modo pánico: al primer error de una sentencia se descarta el resto
de esa línea (y su bloque indentado, si lo tenía) y se continúa con la siguiente, evitando
errores en cascada.
"""


class NodoAST: #representa un nodo del Árbol de Sintaxis Abstracta (AST). Guarda el tipo de nodo,
    # su valor, los hijos izquierdo y derecho, la línea, la columna, el tipo de dato y el valor constante.
    def __init__(self, tipo_nodo, valor, izq=None, der=None, linea=1, columna=1):
        self.tipo_nodo = tipo_nodo  # 'DECLARACION', 'ASIGNACION', 'OPERADOR_ARIT', 'OPERADOR_REL', 'LITERAL', 'ID', 'BLOQUE', 'CONDICIONAL', 'CICLO', 'IMPRESION', 'OP_ESPECIAL'
        self.valor = valor
        self.izq = izq
        self.der = der
        self.linea = linea
        self.columna = columna
        self.tipo_dato = None
        self.valor_const = None

    def __repr__(self): #devuelve una representación textual del nodo, mostrando su tipo y valor.
        return f"NodoAST({self.tipo_nodo}, '{self.valor}')"


def preparar_tokens(tokens_lexico):
    #convierte los tokens del análisis léxico en tokens que pueda utilizar el analizador sintáctico.
    # Ignora espacios y comentarios, asigna nombres de terminales y agrega el token EOF al final.
    tokens_sintacticos = []
    ultima_linea = 1
    ultima_col = 1

    for t in tokens_lexico:
        tipo_orig = t["tipo"]
        lex = t["lexema"]

        if tipo_orig in ["ESPACIO", "COMENTARIO"]:
            continue

        term = None
        #identifican el tipo de token léxico y le asignan su terminal correspondiente.
        if tipo_orig == "PALABRA_CLAVE":
            term = lex.upper()
        elif tipo_orig == "IDENTIFICADOR":
            term = "ID"
        elif tipo_orig == "ASIGNACION":
            term = "OP_ASIG"
        elif tipo_orig == "OPERADOR_REL":
            term = "OP_REL"
        elif tipo_orig == "OPERADOR_ARIT":
            term = {'+': 'OP_SUMA', '-': 'OP_RESTA', '*': 'OP_MULT', '/': 'OP_DIV'}.get(lex, 'OP_ARIT')
        elif tipo_orig == "SIMBOLO":
            term = {':': 'DOPUNTOS', '(': 'LPAR', ')': 'RPAR', ',': 'COMA'}.get(lex, 'SIMBOLO')
        elif tipo_orig in ["NUM_ENTERO", "NUM_DECIMAL", "CADENA", "NEWLINE"]:
            term = tipo_orig

        if term: #comprueba si se reconoció un terminal válido antes de agregar el token a la lista sintáctica.
            t_copia = dict(t)
            t_copia['terminal'] = term
            tokens_sintacticos.append(t_copia)

    if tokens_sintacticos:
        #obtiene la posición justo después del último token para ubicar el EOF
        ult = tokens_sintacticos[-1]
        ultima_linea = ult['linea']
        ultima_col = ult['columna'] + len(ult['lexema'])

    tokens_sintacticos.append({
        'terminal': 'EOF',
        'lexema': 'EOF',
        'tipo': 'EOF',
        'linea': ultima_linea,
        'columna': ultima_col
    })
    return tokens_sintacticos


# Nombre legible de cada terminal para los mensajes de error
NOMBRES_VISIBLES = {
    'DOPUNTOS': "':'", 'LPAR': "'('", 'RPAR': "')'", 'COMA': "','", 'OP_ASIG': "'='",
    'ID': 'un identificador', 'OP_REL': 'un operador relacional', 'NEWLINE': 'fin de línea',
    'EOF': 'fin de archivo', 'SI': "'si'", 'SINO': "'sino'", 'MIENTRAS': "'mientras'",
    'MOSTRAR': "'mostrar'", 'REVERSE': "'reverse'",
}


class ErrorSintactico(Exception):
    """Se lanza al primer error de una sentencia para abandonarla (modo pánico)."""


# Terminales que pueden iniciar una sentencia (conjunto PRIMEROS de <Sentencia>)
PRIMEROS_SENTENCIA = {'COMPLETE', 'BUBBLE', 'CHAIN', 'SI', 'MIENTRAS', 'MOSTRAR', 'REVERSE',
                      'ID', 'LPAR', 'NUM_ENTERO', 'NUM_DECIMAL', 'CADENA', 'OP_RESTA'}


class AnalizadorSintactico:
    #realiza el análisis sintáctico de los tokens, verifica si cumplen la gramática y registra
    # los errores encontrados. También almacena el avance del análisis, la traza y los datos del AST.
    def __init__(self, tokens):
        # inicializa los tokens, la posición actual, la traza, los errores y las estructuras donde se almacenará el AST.
        if not tokens or tokens[-1].get('terminal') != 'EOF':
            ult = tokens[-1] if tokens else {'linea': 1, 'columna': 1}
            tokens = list(tokens) + [{'terminal': 'EOF', 'lexema': 'EOF', 'tipo': 'EOF',
                                      'linea': ult['linea'], 'columna': ult['columna']}]
        self.tokens = tokens
        self.pos = 0
        self.actual = self.tokens[0]
        self.traza = []
        self.errores = []
        self.hay_errores = False
        self.ast_raiz = None
        self.ast_nodos = []

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def avanzar(self):
        #avanza al siguiente token de la secuencia (el EOF nunca se rebasa).
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        self.actual = self.tokens[self.pos]

    def match(self, esperado):
        #verifica si el token actual coincide con el esperado. Si coincide,
        # lo registra en la traza y avanza al siguiente; si no, registra un error sintáctico.
        if self.actual['terminal'] == esperado:
            lex_vis = self.actual['lexema'].replace('\n', '\\n')
            self.traza.append(f"Match: {esperado} ('{lex_vis}')")
            tok = self.actual
            self.avanzar()
            return tok
        self.registrar_error(esperado)

    def registrar_error(self, esperado=None, mensaje=None):
        """Registra el error y abandona la sentencia actual lanzando ErrorSintactico."""
        self.hay_errores = True
        if self.actual['terminal'] in ('NEWLINE', 'EOF'):
            encontrado = NOMBRES_VISIBLES[self.actual['terminal']]
        else:
            encontrado = f"'{self.actual['lexema']}'"
        detalle = mensaje if mensaje else f"se esperaba {NOMBRES_VISIBLES.get(esperado, esperado)} y se encontró {encontrado}"
        err = f"Error sintáctico en línea {self.actual['linea']}, columna {self.actual['columna']}: {detalle}"
        if not self.errores or self.errores[-1] != err:
            self.errores.append(err)
            self.traza.append(f"❌ {err}")
        raise ErrorSintactico(err)

    def sincronizar(self):
        # recupera el análisis después de un error descartando el resto de la línea
        # (punto de sincronización: NEWLINE o EOF).
        while self.actual['terminal'] not in ('NEWLINE', 'EOF'):
            self.avanzar()
        if self.actual['terminal'] == 'NEWLINE':
            self.avanzar()

    def _saltar_lineas_vacias(self):
        while self.actual['terminal'] == 'NEWLINE':
            self.avanzar()

    def fin_sentencia(self):
        # Toda sentencia simple termina en salto de línea o en el fin de archivo.
        if self.actual['terminal'] == 'NEWLINE':
            self.match('NEWLINE')
        elif self.actual['terminal'] != 'EOF':
            self.registrar_error('NEWLINE')

    def _construir_bloque(self, lista_nodos):
        #agrupa varios nodos del AST en una estructura de tipo BLOQUE. Si no hay nodos, devuelve None; si hay uno, lo devuelve directamente.
        if not lista_nodos:
            return None
        if len(lista_nodos) == 1:
            return lista_nodos[0]
        raiz = lista_nodos[0]
        for nodo in lista_nodos[1:]:
            raiz = NodoAST('BLOQUE', 'PROGRAMA', izq=raiz, der=nodo)
        return raiz

    # ------------------------------------------------------------------
    # Programa y bloques
    # ------------------------------------------------------------------
    def analizar(self):
        #inicia el análisis sintáctico, procesa el programa, determina si es válido y construye el AST final.
        self.traza.append("Iniciando análisis sintáctico (Símbolo inicial <P>)")
        self.P()

        if not self.hay_errores:
            self.traza.append("\nRESULTADO: VÁLIDO ✅")
        else:
            self.traza.append(f"\nRESULTADO: INVÁLIDO ❌ (Se detectaron {len(self.errores)} errores)")

        self.ast_raiz = self._construir_bloque(self.ast_nodos)
        return not self.hay_errores, self.ast_raiz

    def P(self):
        self._saltar_lineas_vacias()
        if self.actual['terminal'] == 'EOF':
            return
        # Las sentencias del nivel superior deben iniciar en la misma columna que la primera
        self.Sentencias(self.actual['columna'], col_padre=0)
        self.traza.append("Match: EOF")

    def Sentencias(self, col_bloque, col_padre):
        """
        Procesa las sentencias de un bloque cuya sangría es 'col_bloque'. El bloque termina
        al llegar a una línea con sangría <= col_padre o al EOF.
        """
        while True:
            self._saltar_lineas_vacias()
            col = self.actual['columna']
            if self.actual['terminal'] == 'EOF' or col <= col_padre:
                return
            try:
                if col != col_bloque:
                    self.registrar_error(mensaje=f"sangría inesperada (se esperaba columna {col_bloque})")
                self.Sentencia()
            except ErrorSintactico:
                self.sincronizar()
                # Las líneas más indentadas que siguen pertenecían a la sentencia fallida: se descartan
                while self.actual['terminal'] != 'EOF' and self.actual['columna'] > col_bloque:
                    self.sincronizar()
                    self._saltar_lineas_vacias()

    def Bloque(self, tok_abre):
        """Cuerpo de 'si', 'sino' o 'mientras'. Devuelve la lista de nodos AST del cuerpo."""
        len_antes = len(self.ast_nodos)
        col_padre = tok_abre['columna']

        if self.actual['terminal'] not in ('NEWLINE', 'EOF'):
            # Cuerpo de una sola sentencia en la misma línea:  si x > 0: y = 1
            self.Sentencia()
        else:
            if self.actual['terminal'] == 'NEWLINE':
                self.match('NEWLINE')
            self._saltar_lineas_vacias()
            if self.actual['terminal'] == 'EOF' or self.actual['columna'] <= col_padre:
                self.registrar_error(mensaje=f"se esperaba un bloque con sangría después de '{tok_abre['lexema']} ... :' (línea {tok_abre['linea']})")
            col_bloque = self.actual['columna']
            self.traza.append(f"Bloque de '{tok_abre['lexema']}' (línea {tok_abre['linea']}) con sangría en columna {col_bloque}")
            self.Sentencias(col_bloque, col_padre)

        cuerpo = self.ast_nodos[len_antes:]
        self.ast_nodos = self.ast_nodos[:len_antes]
        return cuerpo

    # ------------------------------------------------------------------
    # Sentencias
    # ------------------------------------------------------------------
    def Sentencia(self):
        #identifica qué tipo de sentencia se encuentra y llama a la función correspondiente.
        t = self.actual['terminal']
        if t in ['COMPLETE', 'BUBBLE', 'CHAIN']:
            self.Declaracion()
        elif t == 'SI':
            self.Condicional()
        elif t == 'MIENTRAS':
            self.Ciclo()
        elif t == 'MOSTRAR':
            self.Impresion()
        elif t == 'REVERSE':
            self.OpEspecial()
        elif t == 'ID' and self.tokens[self.pos + 1]['terminal'] == 'OP_ASIG':
            self.Asignacion()
        elif t in PRIMEROS_SENTENCIA:
            # Expresión usada como sentencia
            nodo = self.ExprRel()
            self.fin_sentencia()
            self.ast_nodos.append(nodo)
        elif t == 'SINO':
            self.registrar_error(mensaje="'sino' sin un 'si' correspondiente (revise la sangría)")
        else:
            self.registrar_error('el inicio de una sentencia')

    def Declaracion(self):
        tok_tipo = self.match(self.actual['terminal'])
        tok_id = self.match('ID')

        nodo_expr = None
        # Si tiene signo '=', se procesa la expresión inicial
        if self.actual['terminal'] == 'OP_ASIG':
            self.match('OP_ASIG')
            nodo_expr = self.ExprRel()
        self.fin_sentencia()

        self.ast_nodos.append(NodoAST(
            'DECLARACION', tok_tipo['lexema'],
            NodoAST('ID', tok_id['lexema'], linea=tok_id['linea'], columna=tok_id['columna']),
            nodo_expr, linea=tok_tipo['linea'], columna=tok_tipo['columna']
        ))

    def Asignacion(self):
        tok_id = self.match('ID')
        self.match('OP_ASIG')
        nodo_expr = self.ExprRel()
        self.fin_sentencia()
        self.ast_nodos.append(NodoAST(
            'ASIGNACION', '=',
            NodoAST('ID', tok_id['lexema'], linea=tok_id['linea'], columna=tok_id['columna']),
            nodo_expr, linea=tok_id['linea'], columna=tok_id['columna']
        ))

    def Condicional(self):
        tok_si = self.match('SI')
        nodo_cond = self.ExprRel()
        self.match('DOPUNTOS')
        cuerpo_si = self.Bloque(tok_si)
        cuerpo_sino = self.SinoOpcional(tok_si)

        self.ast_nodos.append(NodoAST(
            'CONDICIONAL', 'si',
            izq=nodo_cond,
            der=NodoAST('BLOQUE', 'RAMAS_SI_SINO', izq=self._construir_bloque(cuerpo_si),
                        der=self._construir_bloque(cuerpo_sino),
                        linea=tok_si['linea'], columna=tok_si['columna']),
            linea=tok_si['linea'], columna=tok_si['columna']
        ))

    def SinoOpcional(self, tok_si):
        # El 'sino' pertenece a este 'si' sólo si está en su misma columna
        self._saltar_lineas_vacias()
        if self.actual['terminal'] == 'SINO' and self.actual['columna'] == tok_si['columna']:
            tok_sino = self.match('SINO')
            self.match('DOPUNTOS')
            return self.Bloque(tok_sino)
        return []

    def Ciclo(self):
        tok_m = self.match('MIENTRAS')
        nodo_cond = self.ExprRel()
        self.match('DOPUNTOS')
        cuerpo_ciclo = self.Bloque(tok_m)

        self.ast_nodos.append(NodoAST(
            'CICLO', 'mientras',
            izq=nodo_cond,
            der=self._construir_bloque(cuerpo_ciclo),
            linea=tok_m['linea'], columna=tok_m['columna']
        ))

    def Impresion(self):
        tok_m = self.match('MOSTRAR')
        self.match('LPAR')
        argumentos = [self.ExprRel()]
        while self.actual['terminal'] == 'COMA':
            self.match('COMA')
            argumentos.append(self.ExprRel())
        self.match('RPAR')
        self.fin_sentencia()
        # Un nodo IMPRESION por argumento: mostrar(a, b) equivale a mostrar(a) y mostrar(b)
        for arg in argumentos:
            self.ast_nodos.append(NodoAST('IMPRESION', 'mostrar', izq=arg,
                                          linea=tok_m['linea'], columna=tok_m['columna']))

    def OpEspecial(self):
        tok_r = self.match('REVERSE')
        if self.actual['terminal'] == 'LPAR':
            self.match('LPAR')
            tok_id = self.match('ID')
            self.match('RPAR')
            self.fin_sentencia()
            self.ast_nodos.append(NodoAST(
                'OP_ESPECIAL', 'reverse',
                izq=NodoAST('ID', tok_id['lexema'], linea=tok_id['linea'], columna=tok_id['columna']),
                linea=tok_r['linea'], columna=tok_r['columna']))
        elif self.actual['terminal'] == 'ID':
            tok_id = self.match('ID')
            self.match('OP_ASIG')
            nodo_expr = self.ExprRel()
            self.fin_sentencia()
            self.ast_nodos.append(NodoAST(
                'DECLARACION', 'chain',
                NodoAST('ID', tok_id['lexema'], linea=tok_id['linea'], columna=tok_id['columna']),
                nodo_expr, linea=tok_r['linea'], columna=tok_r['columna']))
        else:
            self.registrar_error(mensaje=f"se esperaba '(' o un identificador después de 'reverse' y se encontró '{self.actual['lexema']}'")

    # ------------------------------------------------------------------
    # Expresiones
    # ------------------------------------------------------------------
    def ExprRel(self):
        izq = self.ExprArit()
        if self.actual['terminal'] == 'OP_REL':
            op_tok = self.match('OP_REL')
            der = self.ExprArit()
            return NodoAST('OPERADOR_REL', op_tok['lexema'], izq, der, op_tok['linea'], op_tok['columna'])
        return izq

    def ExprArit(self):
        izq = self.Term()
        return self.E_Prime(izq)

    def E_Prime(self, izq):
        # Asociatividad izquierda: a - b - c  =>  (a - b) - c
        if self.actual['terminal'] in ['OP_SUMA', 'OP_RESTA']:
            op_tok = self.match(self.actual['terminal'])
            der = self.Term()
            nodo_op = NodoAST('OPERADOR_ARIT', op_tok['lexema'], izq, der, op_tok['linea'], op_tok['columna'])
            return self.E_Prime(nodo_op)
        return izq

    def Term(self):
        izq = self.Factor()
        return self.T_Prime(izq)

    def T_Prime(self, izq):
        if self.actual['terminal'] in ['OP_MULT', 'OP_DIV']:
            op_tok = self.match(self.actual['terminal'])
            der = self.Factor()
            nodo_op = NodoAST('OPERADOR_ARIT', op_tok['lexema'], izq, der, op_tok['linea'], op_tok['columna'])
            return self.T_Prime(nodo_op)
        return izq

    def Factor(self):
        t = self.actual['terminal']
        if t == 'LPAR':
            self.match('LPAR')
            nodo = self.ExprRel()
            self.match('RPAR')
            return nodo
        if t in ['ID', 'NUM_ENTERO', 'NUM_DECIMAL', 'CADENA']:
            tok = self.match(t)
            tipo_n = 'ID' if t == 'ID' else 'LITERAL'
            return NodoAST(tipo_n, tok['lexema'], linea=tok['linea'], columna=tok['columna'])
        if t == 'OP_RESTA':
            # Menos unario:  -x  se representa como  0 - x
            tok = self.match('OP_RESTA')
            operando = self.Factor()
            cero = NodoAST('LITERAL', '0', linea=tok['linea'], columna=tok['columna'])
            return NodoAST('OPERADOR_ARIT', '-', cero, operando, tok['linea'], tok['columna'])
        self.registrar_error("un identificador, número o cadena")