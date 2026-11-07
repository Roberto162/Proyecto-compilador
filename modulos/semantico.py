"""
modulos/semantico.py
====================
Módulo de Análisis Semántico con validación estricta de variables declaradas.
"""

import re
from modulos.lexico import analizar_codigo
from modulos.sintactico import preparar_tokens, AnalizadorSintactico, NodoAST


class ElementoPila:
    def __init__(self, tipo_dato, valor_const=None):
        self.tipo_dato = tipo_dato
        self.valor_const = valor_const


class PilaSemantica:
    def __init__(self):
        self.pila = []

    def push(self, elem):
        self.pila.append(elem)

    def pop(self):
        if not self.esta_vacia():
            return self.pila.pop()
        return ElementoPila('error', None)

    def esta_vacia(self):
        return len(self.pila) == 0

    def limpiar(self):
        self.pila.clear()


class IncidenciaSemantica:
    def __init__(self, es_error, mensaje, linea, columna, sugerencia=""):
        self.es_error = es_error
        self.mensaje = mensaje
        self.linea = linea
        self.columna = columna
        self.sugerencia = sugerencia

    def __str__(self):
        prefijo = "❌ Error Semántico" if self.es_error else "⚠ Advertencia"
        msg = f"{prefijo} [Línea {self.linea}, Col {self.columna}]: {self.mensaje}"
        if self.sugerencia:
            msg += f"\n   ↳ Sugerencia: {self.sugerencia}"
        return msg


class ManejadorErroresSemanticos:
    def __init__(self):
        self.incidencias = []

    def agregar_error(self, mensaje, linea, columna, sugerencia=""):
        self.incidencias.append(IncidenciaSemantica(True, mensaje, linea, columna, sugerencia))

    def agregar_advertencia(self, mensaje, linea, columna, sugerencia=""):
        self.incidencias.append(IncidenciaSemantica(False, mensaje, linea, columna, sugerencia))

    def hay_errores(self):
        return any(i.es_error for i in self.incidencias)

    def reporte(self):
        if not self.incidencias:
            return "No se detectaron errores ni advertencias semánticas en la expresión. ✅"
        salida = [f"\n--- REPORTE DE INCIDENCIAS SEMÁNTICAS ({len(self.incidencias)}) ---\n" + "-" * 75]
        for idx, inc in enumerate(self.incidencias, 1):
            salida.append(f"{idx}. {inc}")
        salida.append("-" * 75)
        return "\n".join(salida)


class EntradaSimbolo:
    def __init__(self, nombre, tipo, linea, columna, direccion, tamano, valor=None, inicializada=False, ambito="global"):
        self.nombre = nombre
        self.tipo = tipo
        self.tipo_semantico = {
            'complete': 'entero',
            'bubble': 'decimal',
            'chain': 'cadena'
        }.get(tipo, tipo)
        self.linea = linea
        self.columna = columna
        self.direccion = direccion
        self.tamano = tamano
        self.valor = valor
        self.inicializada = inicializada
        self.ambito = ambito  # Atributo restituido


class GestorTablas:
    DIRECCION_BASE = 0x1000
    TAMANOS = {'complete': 4, 'bubble': 8, 'chain': 8, 'entero': 4, 'decimal': 8, 'cadena': 8}

    def __init__(self):
        self.tabla_simbolos = {}
        self.siguiente_direccion = self.DIRECCION_BASE

    def existe(self, nombre):
        return nombre in self.tabla_simbolos

    def insertar(self, nombre, tipo, linea, columna, valor=None, inicializada=False):
        if self.existe(nombre):
            return False
        tamano = self.TAMANOS.get(tipo, 4)
        dir_hex = f"0x{self.siguiente_direccion:04X}"
        self.tabla_simbolos[nombre] = EntradaSimbolo(
            nombre, tipo, linea, columna, dir_hex, tamano, valor, inicializada
        )
        self.siguiente_direccion += tamano
        return True

    def actualizar_valor(self, nombre, valor):
        if self.existe(nombre):
            self.tabla_simbolos[nombre].valor = valor
            # Al hacer una asignación (ej: x = 10), la variable pasa a estar inicializada
            self.tabla_simbolos[nombre].inicializada = True  

    def esta_inicializada(self, nombre):
        entrada = self.tabla_simbolos.get(nombre)
        return entrada.inicializada if entrada else False

    def obtener_tipo(self, nombre):
        entrada = self.tabla_simbolos.get(nombre)
        return entrada.tipo_semantico if entrada else None

    def obtener_valor(self, nombre):
        entrada = self.tabla_simbolos.get(nombre)
        return entrada.valor if entrada else None

    def generar_reporte(self):
        if not self.tabla_simbolos:
            return "Tabla de Símbolos vacía."

        lineas = []
        lineas.append("\n" + "=" * 95)
        lineas.append(f"{'TABLA DE SÍMBOLOS Y DIRECCIONES DE MEMORIA':^95}")
        lineas.append("=" * 95)
        encabezado = f"{'NOMBRE':<12}{'TIPO':<10}{'SEMÁNTICO':<12}{'ÁMBITO':<10}{'DIRECCIÓN':<12}{'TAMAÑO':<10}{'VALOR':<15}{'LÍNEA':<8}"
        lineas.append(encabezado)
        lineas.append("-" * 95)
        for s in self.tabla_simbolos.values():
            val_str = str(s.valor) if s.valor is not None else "None"
            lineas.append(
                f"{s.nombre:<12}{s.tipo:<10}{s.tipo_semantico:<12}{s.ambito:<10}"
                f"{s.direccion:<12}{str(s.tamano)+' B':<10}{val_str:<15}{s.linea:<8}"
            )
        lineas.append("=" * 95)
        return "\n".join(lineas)

def reconstruir_expresion(nodo):
    """Convierte un subárbol del AST de nuevo a una cadena de texto de la expresión."""
    if nodo is None:
        return ""
    if nodo.tipo_nodo in ['LITERAL', 'ID']:
        return str(nodo.valor)
    if nodo.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
        izq = reconstruir_expresion(nodo.izq)
        der = reconstruir_expresion(nodo.der)
        if nodo.izq and nodo.izq.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
            izq = f"({izq})"
        if nodo.der and nodo.der.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
            der = f"({der})"
        return f"{izq} {nodo.valor} {der}"
    return str(nodo.valor)

class AnalizadorSemantico:
    def __init__(self, lineas_ignoradas=None):
        self.tablas = GestorTablas()
        self.manejador = ManejadorErroresSemanticos()
        self.pila_semantica = PilaSemantica()
        self.lineas_ignoradas = lineas_ignoradas if lineas_ignoradas else set()

    def evaluar_ast(self, nodo):
        if nodo is None:
            return

        if nodo.tipo_nodo in ['BLOQUE', 'RAMAS_SI_SINO']:
            self.evaluar_ast(nodo.izq)
            self.evaluar_ast(nodo.der)
            return

        if getattr(nodo, 'linea', None) in self.lineas_ignoradas:
            return

        if nodo.tipo_nodo == 'DECLARACION':
            tipo_decl = nodo.valor
            nombre = nodo.izq.valor
            linea = nodo.linea
            col = nodo.columna
            tipo_esperado = {'complete': 'entero', 'bubble': 'decimal', 'chain': 'cadena'}.get(tipo_decl, tipo_decl)

            # 1. Error si la variable ya existía
            if self.tablas.existe(nombre):
                self.manejador.agregar_error(
                    f"Redeclaración de variable '{nombre}'. Ya existe en este ámbito.",
                    linea, col, "Declare la variable una sola vez."
                )
                return

            # 2. CASO NUEVO: Si es 'complete x' (nodo.der es None, no tiene '=' ni valor)
            if nodo.der is None:
                # Se guarda en la tabla de símbolos con inicializada = False
                self.tablas.insertar(nombre, tipo_decl, linea, col, valor=None, inicializada=False)
                return

            # 3. CASO NORMAL: Si es 'complete x = 10' (tiene expresión inicial)
            # Obtenemos la representación en texto de la expresión en lugar de calcularla
            expr_texto = reconstruir_expresion(nodo.der)
            tipo_expr, val_expr = self.evaluar_con_pila(nodo.der)

            if tipo_expr != 'error':
                if tipo_esperado == tipo_expr or (tipo_esperado == 'decimal' and tipo_expr == 'entero'):
                    self.tablas.insertar(nombre, tipo_decl, linea, col, valor=val_expr, inicializada=True)
                elif tipo_esperado == 'entero' and tipo_expr == 'decimal':
                    val_conv = int(val_expr) if val_expr is not None else None
                    self.tablas.insertar(nombre, tipo_decl, linea, col, valor=val_conv, inicializada=True)
                else:
                    self.manejador.agregar_error(
                        f"Incompatibilidad de tipos al declarar '{nombre}'. Se esperaba '{tipo_decl}' ({tipo_esperado}) y se obtuvo '{tipo_expr}'.",
                        linea, col
                    )
            return

        if nodo.tipo_nodo == 'ASIGNACION':
            nombre = nodo.izq.valor
            linea = nodo.linea
            col = nodo.columna

# Obtenemos la representación en texto de la expresión
            expr_texto = reconstruir_expresion(nodo.der)
            tipo_expr, val_expr = self.evaluar_con_pila(nodo.der)

            # Si la variable de destino no está declarada, reportar error
            if not self.tablas.existe(nombre):
                self.manejador.agregar_error(
                    f"Variable '{nombre}' no declarada.",
                    linea, col,
                    "Debe declarar la variable con 'complete', 'bubble' o 'chain' antes de asignarle un valor."
                )
                return
                
            tipo_actual = self.tablas.obtener_tipo(nombre)

            if tipo_expr != 'error':
                if tipo_actual == tipo_expr or (tipo_actual == 'decimal' and tipo_expr == 'entero'):
                    self.tablas.actualizar_valor(nombre, val_expr)
                elif tipo_actual == 'entero' and tipo_expr == 'decimal':
                    # Permite reasignar decimal a entero (convirtiendo/truncando el valor)
                    val_conv = int(val_expr) if val_expr is not None else None
                    self.tablas.actualizar_valor(nombre, val_conv)
                else:
                    self.manejador.agregar_error(
                        f"Incompatibilidad de tipos al asignar a '{nombre}'. Se esperaba tipo '{tipo_actual}' y se obtuvo '{tipo_expr}'.",
                        linea, col
                    )
            return

        if nodo.tipo_nodo in ['CONDICIONAL', 'CICLO', 'IMPRESION', 'OP_ESPECIAL']:
            self.evaluar_ast(nodo.izq)
            self.evaluar_ast(nodo.der)
            return

        self.evaluar_con_pila(nodo)

    def evaluar_con_pila(self, nodo):
        self.pila_semantica.limpiar()
        self._postorden_eval(nodo)
        if not self.pila_semantica.esta_vacia():
            elem = self.pila_semantica.pop()
            if nodo:
                nodo.tipo_dato = elem.tipo_dato
                nodo.valor_const = elem.valor_const
            return elem.tipo_dato, elem.valor_const
        return 'error', None

    def _postorden_eval(self, nodo):
        if nodo is None:
            return

        if nodo.tipo_nodo in ['BLOQUE', 'DECLARACION', 'ASIGNACION', 'CONDICIONAL', 'RAMAS_SI_SINO', 'CICLO', 'IMPRESION', 'OP_ESPECIAL']:
            self._postorden_eval(nodo.izq)
            self._postorden_eval(nodo.der)
            return

        if nodo.tipo_nodo == 'LITERAL':
            val = str(nodo.valor)
            if val.startswith('"') and val.endswith('"'):
                tipo = 'cadena'
                v_calc = val
            elif '.' in val:
                tipo = 'decimal'
                v_calc = float(val)
            else:
                tipo = 'entero'
                v_calc = int(val)
            self.pila_semantica.push(ElementoPila(tipo, v_calc))
            return

        # VALIDACIÓN ESTRICTA EN EXPRESIONES: Las variables deben estar previamente declaradas
        if nodo.tipo_nodo == 'ID':
            nombre = nodo.valor

            # 1. Error: La variable ni siquiera ha sido declarada
            if not self.tablas.existe(nombre):
                self.manejador.agregar_error(
                    f"Variable '{nombre}' no declarada.",
                    nodo.linea, nodo.columna,
                    "Debe declarar la variable con 'complete', 'bubble' o 'chain' antes de usarla."
                )
                self.pila_semantica.push(ElementoPila('error', None))

            # 2. Error Semántico: La variable está declarada pero NO tiene valor asignado
            elif not self.tablas.esta_inicializada(nombre):
                self.manejador.agregar_error(
                    f"Incompatibilidad semántica: La variable '{nombre}' no tiene un valor asignado.",
                    nodo.linea, nodo.columna,
                    f"Debe inicializar la variable '{nombre}' antes de utilizarla en una operación."
                )
                self.pila_semantica.push(ElementoPila('error', None))

            # 3. La variable existe y tiene valor: se coloca en la pila semántica
            else:
                tipo = self.tablas.obtener_tipo(nombre)
                val = self.tablas.obtener_valor(nombre)
                self.pila_semantica.push(ElementoPila(tipo, val))
            return

        self._postorden_eval(nodo.izq)
        self._postorden_eval(nodo.der)

        if len(self.pila_semantica.pila) < 2:
            self.pila_semantica.push(ElementoPila('error', None))
            return

        op2 = self.pila_semantica.pop()
        op1 = self.pila_semantica.pop()

        if op1.tipo_dato == 'error' or op2.tipo_dato == 'error':
            self.pila_semantica.push(ElementoPila('error', None))
            return

        op = nodo.valor

        if nodo.tipo_nodo == 'OPERADOR_ARIT':
            if op == '/':
                if op2.valor_const is not None and op2.valor_const == 0:
                    self.manejador.agregar_error(
                        "División por cero detectada en expresión.",
                        nodo.linea, nodo.columna
                    )
                    self.pila_semantica.push(ElementoPila('error', None))
                    return

            if op1.tipo_dato in ['entero', 'decimal'] and op2.tipo_dato in ['entero', 'decimal']:
                tipo_res = 'decimal' if (op == '/' or op1.tipo_dato == 'decimal' or op2.tipo_dato == 'decimal') else 'entero'
                self.pila_semantica.push(ElementoPila(tipo_res, None))
                return

            self.manejador.agregar_error(
                f"Operador '{op}' inválido entre tipos '{op1.tipo_dato}' y '{op2.tipo_dato}'.",
                nodo.linea, nodo.columna
            )
            self.pila_semantica.push(ElementoPila('error', None))
            return

        if nodo.tipo_nodo == 'OPERADOR_REL':
            if op1.tipo_dato in ['entero', 'decimal'] and op2.tipo_dato in ['entero', 'decimal']:
                self.pila_semantica.push(ElementoPila('booleano', None))
                return

            self.manejador.agregar_error(
                f"Comparación '{op}' no permitida entre tipos '{op1.tipo_dato}' y '{op2.tipo_dato}'.",
                nodo.linea, nodo.columna
            )
            self.pila_semantica.push(ElementoPila('error', None))
            return


def extraer_lineas_con_error(lista_errores):
    lineas = set()
    for err in lista_errores:
        match = re.search(r'línea (\d+)', err, re.IGNORECASE)
        if match:
            lineas.add(int(match.group(1)))
    return lineas


def ejecutar_pipeline_completo(codigo):
    tokens_lex, err_lex = analizar_codigo(codigo)
    lineas_error_lex = extraer_lineas_con_error(err_lex)

    tokens_sint = preparar_tokens(tokens_lex)
    parser = AnalizadorSintactico(tokens_sint)
    valido_sint, ast_raiz = parser.analizar()
    lineas_error_sint = extraer_lineas_con_error(parser.errores)

    lineas_a_ignorar = lineas_error_lex.union(lineas_error_sint)

    semantico = AnalizadorSemantico(lineas_ignoradas=lineas_a_ignorar)
    if ast_raiz:
        semantico.evaluar_ast(ast_raiz)

    reporte_sem = semantico.manejador.reporte()
    tabla_rep = semantico.tablas.generar_reporte()

    if lineas_a_ignorar:
        lineas_str = ", ".join(map(str, sorted(lineas_a_ignorar)))
        reporte_sem = f"⚠ Nota: Se omitió el análisis semántico de la(s) línea(s) con error previo: [{lineas_str}]\n\n" + reporte_sem

    valido_global = (len(err_lex) == 0 and len(parser.errores) == 0 and not semantico.manejador.hay_errores())

    return valido_global, err_lex, parser.errores, reporte_sem, tabla_rep, ast_raiz