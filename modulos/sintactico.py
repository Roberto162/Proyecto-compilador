"""
modulos/sintactico.py
=====================
Analizador Sintáctico LL(1)
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
        ultima_linea = t["linea"]
        ultima_col = t["columna"] + len(lex)

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
        #verifica que haya tokens sintácticos para obtener la posición del último token antes de agregar
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


class AnalizadorSintactico:
    #realiza el análisis sintáctico de los tokens, verifica si cumplen la gramática y registra 
    # los errores encontrados. También almacena el avance del análisis, la traza y los datos del AST.
    def __init__(self, tokens):
 # inicializa los tokens, la posición actual, la traza, los errores y las estructuras donde se almacenará el AST.
        self.tokens = tokens
        self.pos = 0
        ult_pos = self.tokens[-1] if self.tokens else {'linea': 1, 'columna': 1}
        self.actual = self.tokens[self.pos] if self.tokens else {
            'terminal': 'EOF', 'lexema': 'EOF', 'tipo': 'EOF', 
            'linea': ult_pos['linea'], 'columna': ult_pos['columna']
        }
        self.traza = []
        self.errores = []
        self.hay_errores = False
        self.ast_raiz = None
        self.ast_nodos = []

    def avanzar(self):
 #avanza al siguiente token de la secuencia. Si ya no quedan tokens, establece el token actual como EOF.
        self.pos += 1
        if self.pos < len(self.tokens):
            self.actual = self.tokens[self.pos]
        else:
            ult_pos = self.tokens[-1] if self.tokens else {'linea': 1, 'columna': 1}
            self.actual = {
                'terminal': 'EOF', 'lexema': 'EOF', 'tipo': 'EOF', 
                'linea': ult_pos['linea'], 'columna': ult_pos['columna']
            }

    def match(self, esperado):
    #verifica si el token actual coincide con el esperado. Si coincide, 
    # lo registra en la traza y avanza al siguiente; si no, registra un error sintáctico.
        if self.actual['terminal'] == esperado:
            lex_vis = self.actual['lexema'].replace('\n', '\\n')
            msg = f"Match: {esperado} ('{lex_vis}')"
            self.traza.append(msg)
            tok = self.actual
            self.avanzar()
            return tok
        else:
            self.registrar_error(esperado)
            return None

    def registrar_error(self, esperado):
        self.hay_errores = True
        encontrado = self.actual['lexema'] if self.actual['terminal'] != 'EOF' else 'EOF'
        err = f"Error sintáctico en línea {self.actual['linea']}, columna {self.actual['columna']}: se esperaba '{esperado}' y se encontró '{encontrado}'"
        
        if not self.errores or self.errores[-1] != err:
            #evita agregar un error si es idéntico al último que se registró.
            self.errores.append(err)
            self.traza.append(f"❌ {err}")

        self.sincronizar()

    def sincronizar(self):
        #recupera el análisis después de un error, avanzando hasta encontrar un 
        # token que permita continuar, como un salto de línea, una palabra reservada o el final del archivo.
        puntos_sincronizacion = [
            'NEWLINE', 'EOF', 'COMPLETE', 'BUBBLE', 'CHAIN', 
            'SI', 'SINO', 'MIENTRAS', 'MOSTRAR', 'REVERSE'
        ]
        while self.actual['terminal'] not in puntos_sincronizacion:
            self.avanzar()
        if self.actual['terminal'] == 'NEWLINE':
            self.avanzar()

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

    def analizar(self):
        #inicia el análisis sintáctico, procesa el programa, determina si es válido y construye el AST final.
        self.traza.append("Iniciando análisis sintáctico (Símbolo inicial <P>)")
        if not self.tokens or self.actual['terminal'] == 'EOF':
            self.traza.append("RESULTADO: VÁLIDO ✅")
            return True, None

        self.P()

        if not self.hay_errores and self.actual['terminal'] != 'EOF':
            self.match('EOF')

        if not self.hay_errores:
            self.traza.append("\nRESULTADO: VÁLIDO ✅")
        else:
            self.traza.append(f"\nRESULTADO: INVÁLIDO ❌ (Se detectaron {len(self.errores)} errores)")

        self.ast_raiz = self._construir_bloque(self.ast_nodos)
        return not self.hay_errores, self.ast_raiz

    def P(self):
        self.Sentencias()

    def Sentencias(self):
       # procesa una secuencia de sentencias hasta encontrar un token que no pueda iniciar otra sentencia.
        primeros = ['COMPLETE', 'BUBBLE', 'CHAIN', 'SI', 'MIENTRAS', 'MOSTRAR', 'REVERSE', 'ID', 'LPAR', 'NUM_ENTERO', 'NUM_DECIMAL', 'CADENA', 'NEWLINE']
        # CORRECCIÓN CLAVE: El bucle itera ÚNICAMENTE si el terminal actual está en "Primeros".
        # Si encuentra SINO o EOF, la regla deriva limpiamente en épsilon (ε) evitando bucles infinitos.
        while self.actual['terminal'] in primeros:
            if self.actual['terminal'] == 'NEWLINE':
                self.avanzar()
            else:
                self.Sentencia()

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
        elif t == 'ID':
            next_t = self.tokens[self.pos + 1]['terminal'] if (self.pos + 1) < len(self.tokens) else None
            if next_t == 'OP_ASIG':
                self.Asignacion()
            elif next_t == 'DOPUNTOS':
                self.match('ID')
                self.match('DOPUNTOS')
            else:
                nodo = self.ExprRel()
                if nodo: self.ast_nodos.append(nodo)
                if self.actual['terminal'] == 'NEWLINE':
                    self.match('NEWLINE')
        elif t in ['LPAR', 'NUM_ENTERO', 'NUM_DECIMAL', 'CADENA']:
            nodo = self.ExprRel()
            if nodo: self.ast_nodos.append(nodo)
            if self.actual['terminal'] == 'NEWLINE':
                self.match('NEWLINE')
        elif t == 'NEWLINE':
            self.avanzar()

    def Declaracion(self):
        tok_tipo = self.match(self.actual['terminal'])
        tok_id = self.match('ID')
        
        nodo_expr = None
        # Si tiene signo '=', se procesa la expresión inicial
        if self.actual['terminal'] == 'OP_ASIG':
            self.match('OP_ASIG')
            nodo_expr = self.ExprRel()

        if tok_id and tok_tipo:
            nodo_decl = NodoAST(
                'DECLARACION', tok_tipo['lexema'], 
                NodoAST('ID', tok_id['lexema'], linea=tok_id['linea'], columna=tok_id['columna']), 
                nodo_expr, linea=tok_tipo['linea'], columna=tok_tipo['columna']
            )
            self.ast_nodos.append(nodo_decl)

        if self.actual['terminal'] == 'NEWLINE':
            self.match('NEWLINE')

    def Asignacion(self):
        tok_id = self.match('ID')
        self.match('OP_ASIG')
        nodo_expr = self.ExprRel()
        if nodo_expr and tok_id:
            nodo_asig = NodoAST(
                'ASIGNACION', '=', 
                NodoAST('ID', tok_id['lexema'], linea=tok_id['linea'], columna=tok_id['columna']), 
                nodo_expr, linea=tok_id['linea'], columna=tok_id['columna']
            )
            self.ast_nodos.append(nodo_asig)
        if self.actual['terminal'] == 'NEWLINE':
            self.match('NEWLINE')

    def Condicional(self):
        tok_si = self.match('SI')
        nodo_cond = self.ExprRel()
        self.match('DOPUNTOS')
        if self.actual['terminal'] == 'NEWLINE':
            self.match('NEWLINE')

        len_antes = len(self.ast_nodos)
        self.Sentencias()
        cuerpo_si = self.ast_nodos[len_antes:]
        self.ast_nodos = self.ast_nodos[:len_antes]

        cuerpo_sino = self.SinoOpcional()

        nodo_if = NodoAST(
            'CONDICIONAL', 'si',
            izq=nodo_cond,
            der=NodoAST('BLOQUE', 'RAMAS_SI_SINO', izq=self._construir_bloque(cuerpo_si), der=self._construir_bloque(cuerpo_sino)),
            linea=tok_si['linea'] if tok_si else 1, columna=tok_si['columna'] if tok_si else 1
        )
        self.ast_nodos.append(nodo_if)

    def SinoOpcional(self):
        if self.actual['terminal'] == 'SINO':
            self.match('SINO')
            self.match('DOPUNTOS')
            if self.actual['terminal'] == 'NEWLINE':
                self.match('NEWLINE')
            len_antes = len(self.ast_nodos)
            self.Sentencias()
            cuerpo_sino = self.ast_nodos[len_antes:]
            self.ast_nodos = self.ast_nodos[:len_antes]
            return cuerpo_sino
        return []

    def Ciclo(self):
        tok_m = self.match('MIENTRAS')
        nodo_cond = self.ExprRel()
        self.match('DOPUNTOS')
        if self.actual['terminal'] == 'NEWLINE':
            self.match('NEWLINE')

        len_antes = len(self.ast_nodos)
        self.Sentencias()
        cuerpo_ciclo = self.ast_nodos[len_antes:]
        self.ast_nodos = self.ast_nodos[:len_antes]

        nodo_while = NodoAST(
            'CICLO', 'mientras',
            izq=nodo_cond,
            der=self._construir_bloque(cuerpo_ciclo),
            linea=tok_m['linea'] if tok_m else 1, columna=tok_m['columna'] if tok_m else 1
        )
        self.ast_nodos.append(nodo_while)

    def Impresion(self):
        tok_m = self.match('MOSTRAR')
        self.match('LPAR')
        nodo_expr = self.ExprRel()
        if nodo_expr and tok_m:
            self.ast_nodos.append(NodoAST('IMPRESION', 'mostrar', izq=nodo_expr, linea=tok_m['linea'], columna=tok_m['columna']))
        while self.actual['terminal'] == 'COMA':
            self.match('COMA')
            self.ExprRel()
        self.match('RPAR')
        if self.actual['terminal'] == 'NEWLINE':
            self.match('NEWLINE')

    def OpEspecial(self):
        tok_r = self.match('REVERSE')
        if self.actual['terminal'] == 'LPAR':
            self.match('LPAR')
            tok_id = self.match('ID')
            self.match('RPAR')
            if tok_id and tok_r:
                self.ast_nodos.append(NodoAST('OP_ESPECIAL', 'reverse', izq=NodoAST('ID', tok_id['lexema']), linea=tok_r['linea'], columna=tok_r['columna']))
        elif self.actual['terminal'] == 'ID':
            tok_id = self.match('ID')
            if self.actual['terminal'] == 'OP_ASIG':
                self.match('OP_ASIG')
                nodo_expr = self.ExprRel()
                if nodo_expr and tok_id and tok_r:
                    self.ast_nodos.append(NodoAST('DECLARACION', 'chain', NodoAST('ID', tok_id['lexema']), nodo_expr, linea=tok_r['linea'], columna=tok_r['columna']))
        if self.actual['terminal'] == 'NEWLINE':
            self.match('NEWLINE')

    def ExprRel(self):
        izq = self.ExprArit()
        if self.actual['terminal'] == 'OP_REL':
            op_tok = self.match('OP_REL')
            der = self.ExprArit()
            if op_tok and izq and der:
                return NodoAST('OPERADOR_REL', op_tok['lexema'], izq, der, op_tok['linea'], op_tok['columna'])
        return izq

    def ExprArit(self):
        izq = self.Term()
        return self.E_Prime(izq)

    def E_Prime(self, izq):
        if self.actual['terminal'] in ['OP_SUMA', 'OP_RESTA']:
            op_tok = self.match(self.actual['terminal'])
            der = self.Term()
            if op_tok and izq and der:
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
            if op_tok and izq and der:
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
        elif t in ['ID', 'NUM_ENTERO', 'NUM_DECIMAL', 'CADENA']:
            tok = self.match(t)
            if tok:
                tipo_n = 'ID' if t == 'ID' else 'LITERAL'
                return NodoAST(tipo_n, tok['lexema'], linea=tok['linea'], columna=tok['columna'])
            return None
        else:
            self.registrar_error("ID, Número o Cadena")
            return None