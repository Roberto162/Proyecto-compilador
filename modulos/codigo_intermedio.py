"""
modulos/codigo_intermedio.py
============================
Generador de Código Intermedio a partir del AST.
Sólo traduce: no calcula valores, no verifica tipos y no optimiza.

Las cuatro representaciones se obtienen del MISMO AST. Su objetivo principal son las
expresiones algebraicas (+ - * /, paréntesis y menos unario), respetando precedencia y
asociatividad; las estructuras de control (si / sino / mientras) se traducen a etiquetas
y saltos para que el programa completo quede en código intermedio.

Representaciones:
1. Notación Polaca (Prefija)          - recorrido en preorden
2. Código P (Máquina de Pila)         - recorrido en posorden (PUSH / operación / STORE, FJP / UJP / LAB)
3. Triplos Indexados (op, arg1, arg2) - los resultados se referencian por índice (n) y los saltos a [n]
4. Cuádruplos (op, arg1, arg2, res)   - temporales t1, t2... y etiquetas L1, L2...

Traducción de las estructuras de control (cuádruplos):

    si c: A  sino: B              mientras c: A
    ----------------              -------------
    tC = c                        label L1
    ifFalse tC _ L2               tC = c
    A                             ifFalse tC _ L2
    goto _ _ L1                   A
    label L2                      goto _ _ L1
    B                             label L2
    label L1

Una declaración sin valor inicial ('complete x') sólo reserva la variable (tabla de
símbolos) y no genera instrucciones.
"""

from config import OPCODES_CODIGO_P, PREFIJO_TEMPORALES, PREFIJO_ETIQUETAS
from modulos.sintactico import NodoAST

OPERADORES = ('OPERADOR_ARIT', 'OPERADOR_REL')


class GeneradorCodigoIntermedio:
    #Es la clase principal del módulo. Recibe el AST del analizador sintáctico y
    #lo utiliza para generar cuatro representaciones del código intermedio:
    # notación polaca, código P, triplos y cuádruplos.
    def __init__(self, ast_raiz: NodoAST):
        #Guarda la raíz del árbol sintáctico. A partir de ella, las demás funciones
        # recorren el AST para producir el código intermedio.
        self.raiz = ast_raiz

    def _obtener_sentencias(self, nodo):
        """Descompone un BLOQUE del AST en una lista plana de sentencias."""
        if not nodo:
            return []
        if nodo.tipo_nodo == 'BLOQUE':
            return self._obtener_sentencias(nodo.izq) + self._obtener_sentencias(nodo.der)
        return [nodo]

    @staticmethod
    def _ramas(nodo_si):
        """Devuelve (cuerpo_si, cuerpo_sino) de un nodo CONDICIONAL."""
        ramas = nodo_si.der
        return (ramas.izq, ramas.der) if ramas else (None, None)

    # =========================================================================
    # 1. NOTACIÓN POLACA (PREFIJA)
    # =========================================================================
    def generar_polaca(self) -> str:
        """Recorrido en preorden: primero el operador y después sus operandos.
        Las estructuras de control se muestran con sangría y su cierre (FIN_SI / FIN_MIENTRAS)."""
        lineas = []

        def expr(n):
            if n is None:
                return []
            if n.tipo_nodo in OPERADORES:
                return [str(n.valor)] + expr(n.izq) + expr(n.der)
            return [str(n.valor)]          # ID o LITERAL

        def bloque(nodo, nivel):
            sangria = "    " * nivel
            for st in self._obtener_sentencias(nodo):
                t = st.tipo_nodo
                if t in ('DECLARACION', 'ASIGNACION'):
                    if st.der is not None:
                        lineas.append(sangria + " ".join(["=", str(st.izq.valor)] + expr(st.der)))
                elif t == 'CONDICIONAL':
                    cuerpo_si, cuerpo_sino = self._ramas(st)
                    lineas.append(sangria + "SI " + " ".join(expr(st.izq)))
                    bloque(cuerpo_si, nivel + 1)
                    if cuerpo_sino is not None:
                        lineas.append(sangria + "SINO")
                        bloque(cuerpo_sino, nivel + 1)
                    lineas.append(sangria + "FIN_SI")
                elif t == 'CICLO':
                    lineas.append(sangria + "MIENTRAS " + " ".join(expr(st.izq)))
                    bloque(st.der, nivel + 1)
                    lineas.append(sangria + "FIN_MIENTRAS")
                elif t == 'IMPRESION':
                    lineas.append(sangria + " ".join(["mostrar"] + expr(st.izq)))
                elif t == 'OP_ESPECIAL':
                    lineas.append(sangria + f"reverse {st.izq.valor}")
                else:                                  # expresión usada como sentencia
                    lineas.append(sangria + " ".join(expr(st)))

        bloque(self.raiz, 0)
        return "\n".join(lineas) if lineas else "N/A"

    # =========================================================================
    # 2. CÓDIGO P (MÁQUINA DE PILA)
    # =========================================================================
    def generar_codigo_p(self) -> list:
        """Recorrido en posorden para una máquina de pila.
        PUSH coloca un valor, las operaciones toman los dos valores de la cima,
        STORE guarda la cima en una variable, FJP salta si la cima es falsa,
        UJP salta siempre y LAB marca el destino de un salto."""
        instrucciones = []
        contador = [0]

        def etiqueta():
            contador[0] += 1
            return f"{PREFIJO_ETIQUETAS}{contador[0]}"

        def expr(n):
            if n is None:
                return
            if n.tipo_nodo in OPERADORES:
                expr(n.izq)
                expr(n.der)
                instrucciones.append(OPCODES_CODIGO_P.get(n.valor, str(n.valor).upper()))
            else:
                instrucciones.append(f"PUSH {n.valor}")

        def bloque(nodo):
            for st in self._obtener_sentencias(nodo):
                t = st.tipo_nodo
                if t in ('DECLARACION', 'ASIGNACION'):
                    if st.der is not None:
                        expr(st.der)
                        instrucciones.append(f"{OPCODES_CODIGO_P['=']} {st.izq.valor}")
                elif t == 'CONDICIONAL':
                    cuerpo_si, cuerpo_sino = self._ramas(st)
                    l_fin = etiqueta()
                    expr(st.izq)
                    if cuerpo_sino is not None:
                        l_sino = etiqueta()
                        instrucciones.append(f"{OPCODES_CODIGO_P['ifFalse']} {l_sino}")
                        bloque(cuerpo_si)
                        instrucciones.append(f"{OPCODES_CODIGO_P['goto']} {l_fin}")
                        instrucciones.append(f"{OPCODES_CODIGO_P['label']} {l_sino}")
                        bloque(cuerpo_sino)
                    else:
                        instrucciones.append(f"{OPCODES_CODIGO_P['ifFalse']} {l_fin}")
                        bloque(cuerpo_si)
                    instrucciones.append(f"{OPCODES_CODIGO_P['label']} {l_fin}")
                elif t == 'CICLO':
                    l_ini, l_fin = etiqueta(), etiqueta()
                    instrucciones.append(f"{OPCODES_CODIGO_P['label']} {l_ini}")
                    expr(st.izq)
                    instrucciones.append(f"{OPCODES_CODIGO_P['ifFalse']} {l_fin}")
                    bloque(st.der)
                    instrucciones.append(f"{OPCODES_CODIGO_P['goto']} {l_ini}")
                    instrucciones.append(f"{OPCODES_CODIGO_P['label']} {l_fin}")
                elif t == 'IMPRESION':
                    expr(st.izq)
                    instrucciones.append(OPCODES_CODIGO_P['print'])
                elif t == 'OP_ESPECIAL':
                    var = st.izq.valor
                    instrucciones.extend([f"PUSH {var}", OPCODES_CODIGO_P["reverse"], f"{OPCODES_CODIGO_P['=']} {var}"])
                else:                                   # expresión suelta: su resultado queda en la pila
                    expr(st)

        bloque(self.raiz)
        return instrucciones

    # =========================================================================
    # 4. CUÁDRUPLOS (op, arg1, arg2, resultado)
    # =========================================================================
    def generar_cuadruplos(self) -> list:
        """Código de tres direcciones con temporales (t1, t2...) y etiquetas (L1, L2...)."""
        cuadruplos = []
        cont = {"temp": 0, "etiq": 0}

        def temporal():
            cont["temp"] += 1
            return f"{PREFIJO_TEMPORALES}{cont['temp']}"

        def etiqueta():
            cont["etiq"] += 1
            return f"{PREFIJO_ETIQUETAS}{cont['etiq']}"

        def emitir(op, a1="", a2="", res=""):
            cuadruplos.append({"operador": op, "arg1": str(a1), "arg2": str(a2), "resultado": str(res)})

        def expr(n):
            # Devuelve el operando (variable, literal o temporal) que contiene el valor de la expresión
            if n is None:
                return ""
            if n.tipo_nodo in OPERADORES:
                a = expr(n.izq)
                b = expr(n.der)
                t = temporal()
                emitir(str(n.valor), a, b, t)
                return t
            return str(n.valor)

        def bloque(nodo):
            for st in self._obtener_sentencias(nodo):
                t = st.tipo_nodo
                if t in ('DECLARACION', 'ASIGNACION'):
                    if st.der is not None:
                        emitir("=", expr(st.der), "", st.izq.valor)
                elif t == 'CONDICIONAL':
                    cuerpo_si, cuerpo_sino = self._ramas(st)
                    c = expr(st.izq)
                    l_fin = etiqueta()
                    if cuerpo_sino is not None:
                        l_sino = etiqueta()
                        emitir("ifFalse", c, "", l_sino)
                        bloque(cuerpo_si)
                        emitir("goto", "", "", l_fin)
                        emitir("label", "", "", l_sino)
                        bloque(cuerpo_sino)
                    else:
                        emitir("ifFalse", c, "", l_fin)
                        bloque(cuerpo_si)
                    emitir("label", "", "", l_fin)
                elif t == 'CICLO':
                    l_ini, l_fin = etiqueta(), etiqueta()
                    emitir("label", "", "", l_ini)
                    c = expr(st.izq)
                    emitir("ifFalse", c, "", l_fin)
                    bloque(st.der)
                    emitir("goto", "", "", l_ini)
                    emitir("label", "", "", l_fin)
                elif t == 'IMPRESION':
                    emitir("print", expr(st.izq))
                elif t == 'OP_ESPECIAL':
                    var = st.izq.valor
                    emitir("reverse", var, "", var)
                else:                                   # expresión suelta
                    expr(st)

        bloque(self.raiz)
        return cuadruplos

    # =========================================================================
    # 3. TRIPLOS INDEXADOS (op, arg1, arg2)
    # =========================================================================
    def generar_triplos(self) -> list:
        """Triplos obtenidos de los cuádruplos: cada temporal se sustituye por el índice (n)
        del triplo que lo calcula, y cada etiqueta por el índice [n] de la instrucción destino."""
        cuadruplos = self.generar_cuadruplos()
        triplos = []
        ref_temporal = {}          # t3 -> "(5)"
        destino_etiqueta = {}      # L1 -> índice del triplo siguiente a la etiqueta
        pendientes = []            # (índice del triplo, campo, etiqueta) para resolver al final

        def ref(x):
            return ref_temporal.get(x, x)

        def agregar(op, a1, a2):
            triplos.append({"indice": f"({len(triplos)})", "operador": op, "arg1": a1, "arg2": a2})
            return len(triplos) - 1

        for c in cuadruplos:
            op, a1, a2, res = c["operador"], c["arg1"], c["arg2"], c["resultado"]
            if op == "label":
                destino_etiqueta[res] = len(triplos)
            elif op == "=":
                agregar("=", res, ref(a1))
            elif op == "ifFalse":
                k = agregar("ifFalse", ref(a1), "")
                pendientes.append((k, "arg2", res))
            elif op == "goto":
                k = agregar("goto", "", "")
                pendientes.append((k, "arg1", res))
            elif op == "print":
                agregar("print", ref(a1), "")
            elif op == "reverse":
                k = agregar("reverse", a1, "")
                agregar("=", res, f"({k})")
            else:                                   # operador aritmético o relacional
                k = agregar(op, ref(a1), ref(a2))
                ref_temporal[res] = f"({k})"

        for k, campo, etiq in pendientes:
            triplos[k][campo] = f"[{destino_etiqueta[etiq]}]"
        return triplos


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
    triplos = gen.generar_triplos()
    for t in triplos:
        salida.append(f"{t['indice']:<10}{t['operador']:<12}{t['arg1']:<20}{t['arg2']:<20}")
    if any(t['operador'] in ('goto', 'ifFalse') for t in triplos):
        salida.append("\n(n) = resultado del triplo n · [n] = salto al triplo n")
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