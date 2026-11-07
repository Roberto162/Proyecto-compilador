"""
modulos/codigo_intermedio.py
============================
Generador de Código Intermedio Puro a partir del AST.
Módulo desacoplado sin tipos de datos ni verificaciones semánticas.

Produce exclusivamente:
1. Notación Polaca (Prefija)
2. Código P (Máquina de Pila)
3. Triplos Indexados (op, arg1, arg2)
4. Cuádruplos (op, arg1, arg2, resultado)
"""


from config import OPCODES_CODIGO_P, PREFIJO_TEMPORALES
from modulos.sintactico import NodoAST


class GeneradorCodigoIntermedio:
    #Es la clase principal del módulo. Recibe el AST del analizador sintáctico y
    #lo utiliza para generar cuatro representaciones del código intermedio: 
    # notación polaca, código P, triplos y cuádruplos.
    def __init__(self, ast_raiz: NodoAST):
        #Inicializa el generador y guarda la raíz del árbol sintáctico en self.raiz. 
        # A partir de ella, las demás funciones recorren el AST para producir el código intermedio.
        self.raiz = ast_raiz

    def _obtener_sentencias(self, nodo):
        """Descompone el AST en una lista plana de sentencias."""
        if not nodo:
            return []
        if nodo.tipo_nodo in ['BLOQUE', 'RAMAS_SI_SINO']:
            return self._obtener_sentencias(nodo.izq) + self._obtener_sentencias(nodo.der)
        return [nodo]

    # =========================================================================
    # 1. NOTACIÓN POLACA (PREFIJA)
    # =========================================================================
    def generar_polaca(self) -> str:
        #Genera la notación polaca o prefija mediante un recorrido en preorden del árbol.
        """Recorrido Preorden del árbol sintáctico."""
        #recorre cada nodo comenzando por el operador y después sus operandos.
        sentencias = self._obtener_sentencias(self.raiz)
        lineas = []

        for st in sentencias:
            tokens = []
            def _preorden(n):
                if not n: return
                if n.tipo_nodo in ['DECLARACION', 'ASIGNACION']:
                    tokens.append("=")
                    if n.izq:
                        tokens.append(str(n.izq.valor))
                    _preorden(n.der)
                elif n.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
                    tokens.append(str(n.valor))
                    _preorden(n.izq)
                    _preorden(n.der)
                else:  # ID o LITERAL
                    tokens.append(str(n.valor))

            _preorden(st)
            if tokens:
                lineas.append(" ".join(tokens))

        return "\n".join(lineas) if lineas else "N/A"

    # =========================================================================
    # 2. CÓDIGO P (MÁQUINA DE PILA)
    # =========================================================================
    def generar_codigo_p(self) -> list:
        #Genera instrucciones para una máquina de pila mediante un recorrido en posorden.
        """Recorrido Posorden para máquina de pila (PUSH, ADD, MUL, STORE)."""
        sentencias = self._obtener_sentencias(self.raiz)
        instrucciones = []

        for st in sentencias:
            def _postorden(n):
                #primero procesa los operandos y después el operador. 
                # Para identificadores y literales genera instrucciones PUSH, que colocan valores en la pila.
                if not n: return
                if n.tipo_nodo in ['DECLARACION', 'ASIGNACION']:
                    _postorden(n.der)
                    var_target = n.izq.valor if n.izq else ""
                    instrucciones.append(f"STORE {var_target}")
                elif n.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
                    _postorden(n.izq)
                    _postorden(n.der)
                    opcode = OPCODES_CODIGO_P.get(n.valor, str(n.valor).upper())
                    instrucciones.append(opcode)
                elif n.tipo_nodo in ['ID', 'LITERAL']:
                    instrucciones.append(f"PUSH {n.valor}")

            _postorden(st)

        return instrucciones

    # =========================================================================
    # 3. TRIPLOS INDEXADOS (op, arg1, arg2)
    # =========================================================================
    #Genera la representación de triplos, donde cada operación tiene un índice y los
    #  resultados de operaciones anteriores pueden referenciarse mediante ese índice.
    def generar_triplos(self) -> list:
        """Genera la representación en triplos usando referencias posicionales (0), (1)..."""
        sentencias = self._obtener_sentencias(self.raiz)
        triplos = []

        for st in sentencias:
            def _procesar(n):
                if not n: return ""
                if n.tipo_nodo in ['ID', 'LITERAL']:
                    return str(n.valor)

                if n.tipo_nodo in ['DECLARACION', 'ASIGNACION']:
                    res_expr = _procesar(n.der)
                    var_target = str(n.izq.valor) if n.izq else ""
                    idx = f"({len(triplos)})"
                    triplos.append({
                        "indice": idx,
                        "operador": "=",
                        "arg1": var_target,
                        "arg2": res_expr
                    })
                    return idx

                if n.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
                    arg1 = _procesar(n.izq)
                    arg2 = _procesar(n.der)
                    idx = f"({len(triplos)})"
                    triplos.append({
                        "indice": idx,
                        "operador": str(n.valor),
                        "arg1": arg1,
                        "arg2": arg2
                    })
                    return idx

                return ""

            _procesar(st)

        return triplos

    # =========================================================================
    # 4. CUÁDRUPLOS (op, arg1, arg2, resultado)
    # =========================================================================
    def generar_cuadruplos(self) -> list:
        #Genera cuádruplos utilizando variables temporales para almacenar los resultados de las operaciones.
        """Genera código de tres direcciones con variables temporales (t1, t2...)."""
        sentencias = self._obtener_sentencias(self.raiz)
        cuadruplos = []
        contador_temp = 1

        for st in sentencias:
            def _procesar(n):
                #procesa los operandos antes de generar cada operación. Si encuentra un identificador 
                # o literal, devuelve su valor. Si encuentra una operación aritmética o relacional, 
                # crea una variable temporal, como t1 o t2, y guarda la operación junto con sus 
                # argumentos y resultado. Si encuentra una declaración o asignación, genera un 
                # cuádruplo para guardar el resultado en la variable destino.
                nonlocal contador_temp
                #permite que la función interna modifique el contador de temporales definido 
                # en generar_cuadruplos, para que cada temporal tenga un número consecutivo.
                if not n: return ""
                if n.tipo_nodo in ['ID', 'LITERAL']:
                    return str(n.valor)

                if n.tipo_nodo in ['DECLARACION', 'ASIGNACION']:
                    res_expr = _procesar(n.der)
                    var_target = str(n.izq.valor) if n.izq else ""
                    cuadruplos.append({
                        "operador": "=",
                        "arg1": res_expr,
                        "arg2": "",
                        "resultado": var_target
                    })
                    return var_target

                if n.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
                    arg1 = _procesar(n.izq)
                    arg2 = _procesar(n.der)
                    temp_var = f"{PREFIJO_TEMPORALES}{contador_temp}"
                    contador_temp += 1
                    cuadruplos.append({
                        "operador": str(n.valor),
                        "arg1": arg1,
                        "arg2": arg2,
                        "resultado": temp_var
                    })
                    return temp_var

                return ""

            _procesar(st)

        return cuadruplos


# =============================================================================
# FUNCIONES AUXILIARES DE FORMATO DE SALIDA
# =============================================================================

def obtener_polaca_str(ast_raiz: NodoAST) -> str:
    gen = GeneradorCodigoIntermedio(ast_raiz)
    return f"--- 1. NOTACIÓN POLACA (PREFIJA) ---\n\n{gen.generar_polaca()}"


def obtener_codigo_p_str(ast_raiz: NodoAST) -> str:
    gen = GeneradorCodigoIntermedio(ast_raiz)
    salida = ["--- 2. CÓDIGO P (MÁQUINA DE PILA) ---\n"]
    for inst in gen.generar_codigo_p():
        salida.append(f"  {inst}")
    return "\n".join(salida)


def obtener_triplos_str(ast_raiz: NodoAST) -> str:
    gen = GeneradorCodigoIntermedio(ast_raiz)
    salida = ["--- 3. TRIPLOS INDEXADOS ---\n"]
    salida.append(f"{'ÍNDICE':<10}{'OPERADOR':<12}{'ARGUMENTO 1':<20}{'ARGUMENTO 2':<20}")
    salida.append("-" * 62)
    for t in gen.generar_triplos():
        salida.append(f"{t['indice']:<10}{t['operador']:<12}{t['arg1']:<20}{t['arg2']:<20}")
    return "\n".join(salida)


def obtener_cuadruplos_str(ast_raiz: NodoAST) -> str:
    gen = GeneradorCodigoIntermedio(ast_raiz)
    salida = ["--- 4. CUÁDRUPLOS ---\n"]
    salida.append(f"{'OPERADOR':<12}{'ARGUMENTO 1':<20}{'ARGUMENTO 2':<20}{'RESULTADO':<12}")
    salida.append("-" * 64)
    for c in gen.generar_cuadruplos():
        salida.append(f"{c['operador']:<12}{c['arg1']:<20}{c['arg2']:<20}{c['resultado']:<12}")
    return "\n".join(salida)


def obtener_reporte_codigo_intermedio_str(ast_raiz: NodoAST) -> str:
    salida = [
        obtener_polaca_str(ast_raiz), "\n" + "=" * 65 + "\n",
        obtener_codigo_p_str(ast_raiz), "\n" + "=" * 65 + "\n",
        obtener_triplos_str(ast_raiz), "\n" + "=" * 65 + "\n",
        obtener_cuadruplos_str(ast_raiz)
    ]
    return "\n".join(salida)