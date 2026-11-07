"""
modulos/semantico.py
====================
Módulo de Análisis Semántico.

Responsabilidades (sólo verificación, NO calcula ni optimiza expresiones):
  - Tabla de símbolos con tipo, dirección de memoria y tamaño de cada variable.
  - Variables declaradas antes de usarse y sin redeclaraciones.
  - Variables con valor asignado antes de usarse (incluyendo el flujo de 'si'/'sino'/'mientras').
  - Compatibilidad de tipos en declaraciones, asignaciones, operaciones y condiciones.
  - División entre cero literal o con una variable de valor constante conocido.

Reglas de tipos:
  complete -> entero   bubble -> decimal   chain -> cadena
  aritméticos (+ - * /) : sólo números; '/' siempre produce decimal
  relacionales          : números entre sí; cadenas sólo con == y !=; producen booleano
  decimal -> entero     : permitido con ADVERTENCIA (se trunca)
  condiciones           : booleano; un número genera advertencia; una cadena es error
"""

import re
from modulos.lexico import analizar_codigo
from modulos.sintactico import preparar_tokens, AnalizadorSintactico, NodoAST

TIPOS_DECLARACION = {'complete': 'entero', 'bubble': 'decimal', 'chain': 'cadena'}
NUMERICOS = ('entero', 'decimal')


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
        errores = sum(1 for i in self.incidencias if i.es_error)
        advertencias = len(self.incidencias) - errores
        salida = [f"\n--- REPORTE DE INCIDENCIAS SEMÁNTICAS ({errores} errores, {advertencias} advertencias) ---\n" + "-" * 75]
        for idx, inc in enumerate(self.incidencias, 1):
            salida.append(f"{idx}. {inc}")
        salida.append("-" * 75)
        return "\n".join(salida)


class EntradaSimbolo:
    def __init__(self, nombre, tipo, linea, columna, direccion, tamano, valor=None, inicializada=False, ambito="global"):
        self.nombre = nombre
        self.tipo = tipo
        self.tipo_semantico = TIPOS_DECLARACION.get(tipo, tipo)
        self.linea = linea
        self.columna = columna
        self.direccion = direccion
        self.tamano = tamano
        self.valor = valor                 # texto mostrado en la tabla (literal o expresión asignada)
        self.valor_const = None            # valor literal conocido (sólo si se asignó un literal)
        self.inicializada = inicializada
        self.ambito = ambito


class GestorTablas:
    DIRECCION_BASE = 0x1000
    TAMANOS = {'complete': 4, 'bubble': 8, 'chain': 8, 'entero': 4, 'decimal': 8, 'cadena': 8}

    def __init__(self):
        self.tabla_simbolos = {}
        self.siguiente_direccion = self.DIRECCION_BASE

    def existe(self, nombre):
        return nombre in self.tabla_simbolos

    def insertar(self, nombre, tipo, linea, columna, valor=None, inicializada=False, valor_const=None):
        if self.existe(nombre):
            return False
        tamano = self.TAMANOS.get(tipo, 4)
        dir_hex = f"0x{self.siguiente_direccion:04X}"
        entrada = EntradaSimbolo(nombre, tipo, linea, columna, dir_hex, tamano, valor, inicializada)
        entrada.valor_const = valor_const
        self.tabla_simbolos[nombre] = entrada
        self.siguiente_direccion += tamano
        return True

    def actualizar_valor(self, nombre, valor, valor_const=None):
        if self.existe(nombre):
            self.tabla_simbolos[nombre].valor = valor
            self.tabla_simbolos[nombre].valor_const = valor_const
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

    def obtener_valor_const(self, nombre):
        entrada = self.tabla_simbolos.get(nombre)
        return entrada.valor_const if entrada else None

    def generar_reporte(self):
        if not self.tabla_simbolos:
            return "Tabla de Símbolos vacía."

        ancho = 104
        lineas = []
        lineas.append("\n" + "=" * ancho)
        lineas.append(f"{'TABLA DE SÍMBOLOS Y DIRECCIONES DE MEMORIA':^{ancho}}")
        lineas.append("=" * ancho)
        encabezado = f"{'NOMBRE':<12}{'TIPO':<10}{'SEMÁNTICO':<12}{'ÁMBITO':<10}{'DIRECCIÓN':<12}{'TAMAÑO':<10}{'VALOR':<24}{'LÍNEA':<8}"
        lineas.append(encabezado)
        lineas.append("-" * ancho)
        for s in self.tabla_simbolos.values():
            val_str = str(s.valor) if s.valor is not None else "—"
            if len(val_str) > 22:
                val_str = val_str[:21] + "…"
            lineas.append(
                f"{s.nombre:<12}{s.tipo:<10}{s.tipo_semantico:<12}{s.ambito:<10}"
                f"{s.direccion:<12}{str(s.tamano)+' B':<10}{val_str:<24}{s.linea:<8}"
            )
        lineas.append("=" * ancho)
        lineas.append("VALOR: literal asignado o expresión asignada (el cálculo se realiza en fases posteriores).")
        return "\n".join(lineas)


def _es_menos_unario(nodo):
    # El sintáctico representa -x como (0 - x) con el 0 en la misma posición que el '-'
    return (nodo.tipo_nodo == 'OPERADOR_ARIT' and nodo.valor == '-' and nodo.izq is not None
            and nodo.izq.tipo_nodo == 'LITERAL' and str(nodo.izq.valor) == '0'
            and nodo.izq.linea == nodo.linea and nodo.izq.columna == nodo.columna)


def reconstruir_expresion(nodo):
    """Convierte un subárbol del AST de nuevo a una cadena de texto de la expresión."""
    if nodo is None:
        return ""
    if nodo.tipo_nodo in ['LITERAL', 'ID']:
        return str(nodo.valor)
    if nodo.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
        der = reconstruir_expresion(nodo.der)
        if nodo.der and nodo.der.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
            der = f"({der})"
        if _es_menos_unario(nodo):
            return f"-{der}"
        izq = reconstruir_expresion(nodo.izq)
        if nodo.izq and nodo.izq.tipo_nodo in ['OPERADOR_ARIT', 'OPERADOR_REL']:
            izq = f"({izq})"
        return f"{izq} {nodo.valor} {der}"
    return str(nodo.valor)


def _literal_numerico(nodo):
    """Valor de un literal numérico (o -literal). None si no es un literal numérico."""
    if nodo is None:
        return None
    if _es_menos_unario(nodo):
        v = _literal_numerico(nodo.der)
        return -v if v is not None else None
    if nodo.tipo_nodo == 'LITERAL':
        txt = str(nodo.valor)
        if txt.startswith('"'):
            return None
        return float(txt) if '.' in txt else int(txt)
    return None


class AnalizadorSemantico:
    def __init__(self, lineas_ignoradas=None):
        self.tablas = GestorTablas()
        self.manejador = ManejadorErroresSemanticos()
        self.pila_semantica = PilaSemantica()
        self.lineas_ignoradas = lineas_ignoradas if lineas_ignoradas else set()
        self.nivel_control = 0                 # > 0 dentro de un si / sino / mientras
        self.quizas_sin_valor = set()          # variables con valor asignado sólo en algunas ramas

    # ------------------------------------------------------------------
    # Utilidades de flujo de control
    # ------------------------------------------------------------------
    def _inicializadas(self):
        return {n for n, s in self.tablas.tabla_simbolos.items() if s.inicializada}

    def _restaurar_inicializadas(self, conjunto):
        for n, s in self.tablas.tabla_simbolos.items():
            s.inicializada = n in conjunto

    def _valor_desconocido_tras_control(self, nombres):
        # Tras un si / mientras no se sabe qué rama se ejecutó: el valor deja de ser constante
        for n in nombres:
            s = self.tablas.tabla_simbolos.get(n)
            if s is not None:
                s.valor_const = None

    def _asignadas_en(self, nodo, acum=None):
        acum = set() if acum is None else acum
        if nodo is None:
            return acum
        if nodo.tipo_nodo in ('DECLARACION', 'ASIGNACION') and nodo.izq is not None:
            acum.add(nodo.izq.valor)
        if nodo.tipo_nodo in ('BLOQUE', 'CONDICIONAL', 'CICLO', 'DECLARACION', 'ASIGNACION'):
            self._asignadas_en(nodo.izq, acum)
            self._asignadas_en(nodo.der, acum)
        return acum

    def _verificar_condicion(self, nodo_cond, palabra):
        tipo, _ = self.evaluar_con_pila(nodo_cond)
        if nodo_cond is None or tipo == 'error' or tipo == 'booleano':
            return
        if tipo == 'cadena':
            self.manejador.agregar_error(
                f"La condición de '{palabra}' es de tipo cadena.",
                nodo_cond.linea, nodo_cond.columna,
                "Use una comparación, por ejemplo: s == \"texto\".")
        elif tipo in NUMERICOS:
            self.manejador.agregar_advertencia(
                f"La condición de '{palabra}' es numérica ({tipo}): se considera verdadera si es distinta de 0.",
                nodo_cond.linea, nodo_cond.columna,
                "Se recomienda usar una comparación explícita, por ejemplo: x != 0.")

    # ------------------------------------------------------------------
    # Recorrido del AST
    # ------------------------------------------------------------------
    def evaluar_ast(self, nodo):
        if nodo is None:
            return

        if nodo.tipo_nodo == 'BLOQUE':
            self.evaluar_ast(nodo.izq)
            self.evaluar_ast(nodo.der)
            return

        if getattr(nodo, 'linea', None) in self.lineas_ignoradas:
            return

        if nodo.tipo_nodo == 'DECLARACION':
            self._declaracion(nodo)
        elif nodo.tipo_nodo == 'ASIGNACION':
            self._asignacion(nodo)
        elif nodo.tipo_nodo == 'CONDICIONAL':
            self._condicional(nodo)
        elif nodo.tipo_nodo == 'CICLO':
            self._ciclo(nodo)
        elif nodo.tipo_nodo == 'IMPRESION':
            self.evaluar_con_pila(nodo.izq)
        elif nodo.tipo_nodo == 'OP_ESPECIAL':
            self._op_especial(nodo)
        else:
            self.evaluar_con_pila(nodo)       # expresión usada como sentencia

    def _registrar_valor(self, nombre, nodo_expr, tipo_destino):
        """Texto y valor literal que se guardan en la tabla tras una asignación."""
        texto = reconstruir_expresion(nodo_expr)
        lit = _literal_numerico(nodo_expr)
        if lit is not None and tipo_destino == 'entero':
            lit = int(lit)
            texto = str(lit)
        # Dentro de un si / mientras el valor puede no llegar a asignarse: no es constante
        valor_const = lit if self.nivel_control == 0 else None
        return texto, valor_const

    def _compatibilidad(self, nombre, tipo_destino, tipo_expr, nodo, accion):
        """Devuelve True si el valor puede guardarse en la variable (con o sin advertencia)."""
        if tipo_expr == 'error':
            return True                                   # el error ya se reportó en la expresión
        if tipo_destino == tipo_expr or (tipo_destino == 'decimal' and tipo_expr == 'entero'):
            return True
        if tipo_destino == 'entero' and tipo_expr == 'decimal':
            self.manejador.agregar_advertencia(
                f"Conversión implícita de decimal a entero al {accion} '{nombre}': se pierde la parte decimal.",
                nodo.linea, nodo.columna, "Declare la variable con 'bubble' si necesita decimales.")
            return True
        self.manejador.agregar_error(
            f"Incompatibilidad de tipos al {accion} '{nombre}'. Se esperaba '{tipo_destino}' y se obtuvo '{tipo_expr}'.",
            nodo.linea, nodo.columna)
        return False

    def _declaracion(self, nodo):
        tipo_decl = nodo.valor
        nombre = nodo.izq.valor
        linea, col = nodo.linea, nodo.columna
        tipo_esperado = TIPOS_DECLARACION.get(tipo_decl, tipo_decl)

        if self.tablas.existe(nombre):
            self.manejador.agregar_error(
                f"Redeclaración de variable '{nombre}'. Ya existe en este ámbito.",
                linea, col, "Declare la variable una sola vez.")
            return

        # 'complete x' sin valor inicial
        if nodo.der is None:
            self.tablas.insertar(nombre, tipo_decl, linea, col, valor=None, inicializada=False)
            return

        tipo_expr, _ = self.evaluar_con_pila(nodo.der)
        self._compatibilidad(nombre, tipo_esperado, tipo_expr, nodo, "declarar")
        texto, valor_const = self._registrar_valor(nombre, nodo.der, tipo_esperado)
        # Se inserta aunque haya error en la expresión, para no generar errores en cascada
        self.tablas.insertar(nombre, tipo_decl, linea, col, valor=texto, inicializada=True,
                             valor_const=valor_const)
        if self.nivel_control == 0:
            self.quizas_sin_valor.discard(nombre)

    def _asignacion(self, nodo):
        nombre = nodo.izq.valor
        tipo_expr, _ = self.evaluar_con_pila(nodo.der)

        if not self.tablas.existe(nombre):
            self.manejador.agregar_error(
                f"Variable '{nombre}' no declarada.", nodo.linea, nodo.columna,
                "Debe declarar la variable con 'complete', 'bubble' o 'chain' antes de asignarle un valor.")
            return

        tipo_actual = self.tablas.obtener_tipo(nombre)
        self._compatibilidad(nombre, tipo_actual, tipo_expr, nodo, "asignar a")
        texto, valor_const = self._registrar_valor(nombre, nodo.der, tipo_actual)
        self.tablas.actualizar_valor(nombre, texto, valor_const)
        if self.nivel_control == 0:
            self.quizas_sin_valor.discard(nombre)

    def _condicional(self, nodo):
        self._verificar_condicion(nodo.izq, 'si')
        ramas = nodo.der
        rama_si = ramas.izq if ramas else None
        rama_sino = ramas.der if ramas else None

        antes = self._inicializadas()
        self.nivel_control += 1
        self.evaluar_ast(rama_si)
        ini_si = self._inicializadas()
        self._restaurar_inicializadas(antes)
        self.evaluar_ast(rama_sino)
        ini_sino = self._inicializadas()
        self.nivel_control -= 1

        # Con valor seguro: lo que ya tenía valor, o lo que recibe valor en AMBAS ramas
        seguras = antes | (ini_si & ini_sino) if rama_sino is not None else set(antes)
        parciales = (ini_si | ini_sino) - seguras
        self._restaurar_inicializadas(seguras | parciales)
        self.quizas_sin_valor |= parciales
        self.quizas_sin_valor -= (seguras - antes)
        self._valor_desconocido_tras_control(self._asignadas_en(ramas))

    def _ciclo(self, nodo):
        self._verificar_condicion(nodo.izq, 'mientras')
        antes = self._inicializadas()
        self.nivel_control += 1
        # Las variables que cambian dentro del ciclo no tienen valor constante ni siquiera en
        # la primera vuelta de la condición siguiente
        self._valor_desconocido_tras_control(self._asignadas_en(nodo.der))
        self.evaluar_ast(nodo.der)
        self.nivel_control -= 1
        # El cuerpo puede no ejecutarse nunca
        self.quizas_sin_valor |= self._inicializadas() - antes

    def _op_especial(self, nodo):
        tipo, _ = self.evaluar_con_pila(nodo.izq)
        if tipo not in ('cadena', 'error'):
            self.manejador.agregar_error(
                f"'reverse' sólo se puede aplicar a cadenas y '{nodo.izq.valor}' es de tipo '{tipo}'.",
                nodo.linea, nodo.columna, "Declare la variable con 'chain'.")
        elif tipo == 'cadena':
            self.tablas.actualizar_valor(nodo.izq.valor, f"reverse({nodo.izq.valor})", None)

    # ------------------------------------------------------------------
    # Evaluación de tipos de expresiones con pila semántica (postorden)
    # ------------------------------------------------------------------
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

        if nodo.tipo_nodo == 'LITERAL':
            val = str(nodo.valor)
            if val.startswith('"') and val.endswith('"'):
                tipo, v_calc = 'cadena', val
            elif '.' in val:
                tipo, v_calc = 'decimal', float(val)
            else:
                tipo, v_calc = 'entero', int(val)
            self.pila_semantica.push(ElementoPila(tipo, v_calc))
            return

        # VALIDACIÓN ESTRICTA: las variables deben estar declaradas y tener valor
        if nodo.tipo_nodo == 'ID':
            nombre = nodo.valor
            if not self.tablas.existe(nombre):
                self.manejador.agregar_error(
                    f"Variable '{nombre}' no declarada.", nodo.linea, nodo.columna,
                    "Debe declarar la variable con 'complete', 'bubble' o 'chain' antes de usarla.")
                self.pila_semantica.push(ElementoPila('error', None))
            elif not self.tablas.esta_inicializada(nombre):
                self.manejador.agregar_error(
                    f"La variable '{nombre}' no tiene un valor asignado.", nodo.linea, nodo.columna,
                    f"Debe inicializar la variable '{nombre}' antes de utilizarla en una operación.")
                self.pila_semantica.push(ElementoPila('error', None))
            else:
                if nombre in self.quizas_sin_valor:
                    self.manejador.agregar_advertencia(
                        f"La variable '{nombre}' podría no tener valor: sólo se le asigna dentro de un 'si' o 'mientras'.",
                        nodo.linea, nodo.columna,
                        f"Asigne un valor a '{nombre}' antes del bloque o en todas las ramas.")
                    self.quizas_sin_valor.discard(nombre)      # se advierte una sola vez
                tipo = self.tablas.obtener_tipo(nombre)
                self.pila_semantica.push(ElementoPila(tipo, self.tablas.obtener_valor_const(nombre)))
            return

        if nodo.tipo_nodo not in ('OPERADOR_ARIT', 'OPERADOR_REL'):
            self.pila_semantica.push(ElementoPila('error', None))
            return

        self._postorden_eval(nodo.izq)
        self._postorden_eval(nodo.der)

        op2 = self.pila_semantica.pop()
        op1 = self.pila_semantica.pop()

        if op1.tipo_dato == 'error' or op2.tipo_dato == 'error':
            self.pila_semantica.push(ElementoPila('error', None))
            return

        op = nodo.valor

        if nodo.tipo_nodo == 'OPERADOR_ARIT':
            if op1.tipo_dato in NUMERICOS and op2.tipo_dato in NUMERICOS:
                if op == '/' and op2.valor_const is not None and op2.valor_const == 0:
                    if self.nivel_control == 0:
                        self.manejador.agregar_error("División entre cero detectada en expresión.",
                                                     nodo.linea, nodo.columna)
                        self.pila_semantica.push(ElementoPila('error', None))
                        return
                    self.manejador.agregar_advertencia("Posible división entre cero.", nodo.linea, nodo.columna)
                tipo_res = 'decimal' if (op == '/' or 'decimal' in (op1.tipo_dato, op2.tipo_dato)) else 'entero'
                self.pila_semantica.push(ElementoPila(tipo_res, None))
                return

            self.manejador.agregar_error(
                f"Operador '{op}' inválido entre tipos '{op1.tipo_dato}' y '{op2.tipo_dato}'.",
                nodo.linea, nodo.columna)
            self.pila_semantica.push(ElementoPila('error', None))
            return

        # OPERADOR_REL
        numericos = op1.tipo_dato in NUMERICOS and op2.tipo_dato in NUMERICOS
        cadenas_igualdad = op1.tipo_dato == op2.tipo_dato == 'cadena' and op in ('==', '!=')
        if numericos or cadenas_igualdad:
            self.pila_semantica.push(ElementoPila('booleano', None))
            return

        self.manejador.agregar_error(
            f"Comparación '{op}' no permitida entre tipos '{op1.tipo_dato}' y '{op2.tipo_dato}'.",
            nodo.linea, nodo.columna)
        self.pila_semantica.push(ElementoPila('error', None))


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