"""
modulos/optimizacion/generador_ir.py
====================================
Traduce el AST del analizador sintáctico a una lista de objetos `Cuadruplo`
INCLUYENDO control de flujo (etiquetas y saltos), que es lo que necesita el
optimizador para particionar en bloques básicos.

Nota: el generador de `modulos/codigo_intermedio.py` sólo traduce expresiones y
asignaciones (ignora 'si', 'mientras' y 'mostrar'); por eso el optimizador usa
este generador, que produce la misma forma de cuádruplo (op, arg1, arg2, resultado)
y además:

    si c: A sino: B          mientras c: A
    ---------------          ---------------
    tC = ...                 label Lini
    ifFalse tC _ Lsino       tC = ...
    A                        ifFalse tC _ Lfin
    goto Lfin                A
    label Lsino              goto Lini
    B                        label Lfin
    label Lfin
"""

from config import PREFIJO_TEMPORALES, PREFIJO_ETIQUETAS
from modulos.optimizacion.cuadruplo import (
    Cuadruplo, numerar, OP_COPIA, OP_ETIQUETA, OP_GOTO, OP_IF_FALSO, OP_IMPRIMIR, OP_REVERSE
)


class GeneradorIR:
    def __init__(self):
        self.codigo = []
        self.n_temp = 0
        self.n_etiq = 0

    # -- utilidades --------------------------------------------------------
    def _temporal(self):
        self.n_temp += 1
        return f"{PREFIJO_TEMPORALES}{self.n_temp}"

    def _etiqueta(self):
        self.n_etiq += 1
        return f"{PREFIJO_ETIQUETAS}{self.n_etiq}"

    def _emitir(self, op, a1="", a2="", res=""):
        self.codigo.append(Cuadruplo(op, str(a1), str(a2), str(res)))

    # -- expresiones -------------------------------------------------------
    def _expr(self, n):
        """Genera el código de una expresión y devuelve el operando que la contiene."""
        if n is None:
            return ""
        if n.tipo_nodo in ('ID', 'LITERAL'):
            return str(n.valor)
        if n.tipo_nodo in ('OPERADOR_ARIT', 'OPERADOR_REL'):
            a = self._expr(n.izq)
            b = self._expr(n.der)
            t = self._temporal()
            self._emitir(str(n.valor), a, b, t)
            return t
        return str(n.valor)

    # -- sentencias --------------------------------------------------------
    def _sentencia(self, n):
        if n is None:
            return
        tipo = n.tipo_nodo

        if tipo == 'BLOQUE':
            self._sentencia(n.izq)
            self._sentencia(n.der)

        elif tipo in ('DECLARACION', 'ASIGNACION'):
            if n.der is not None:              # 'complete x' sin valor no genera código
                v = self._expr(n.der)
                self._emitir(OP_COPIA, v, "", n.izq.valor)

        elif tipo == 'CONDICIONAL':
            ramas = n.der
            cuerpo_si = ramas.izq if ramas else None
            cuerpo_sino = ramas.der if ramas else None
            c = self._expr(n.izq)
            l_fin = self._etiqueta()
            if cuerpo_sino is not None:
                l_sino = self._etiqueta()
                self._emitir(OP_IF_FALSO, c, "", l_sino)
                self._sentencia(cuerpo_si)
                self._emitir(OP_GOTO, "", "", l_fin)
                self._emitir(OP_ETIQUETA, "", "", l_sino)
                self._sentencia(cuerpo_sino)
            else:
                self._emitir(OP_IF_FALSO, c, "", l_fin)
                self._sentencia(cuerpo_si)
            self._emitir(OP_ETIQUETA, "", "", l_fin)

        elif tipo == 'CICLO':
            l_ini = self._etiqueta()
            l_fin = self._etiqueta()
            self._emitir(OP_ETIQUETA, "", "", l_ini)
            c = self._expr(n.izq)
            self._emitir(OP_IF_FALSO, c, "", l_fin)
            self._sentencia(n.der)
            self._emitir(OP_GOTO, "", "", l_ini)
            self._emitir(OP_ETIQUETA, "", "", l_fin)

        elif tipo == 'IMPRESION':
            v = self._expr(n.izq)
            self._emitir(OP_IMPRIMIR, v, "", "")

        elif tipo == 'OP_ESPECIAL':
            var = n.izq.valor
            self._emitir(OP_REVERSE, var, "", var)

        else:                                   # expresión suelta como sentencia
            self._expr(n)

    def generar(self, ast_raiz):
        self._sentencia(ast_raiz)
        return numerar(self.codigo)


def generar_cuadruplos_desde_ast(ast_raiz):
    """Punto de entrada: AST -> lista de Cuadruplo (con 'origen' numerado)."""
    return GeneradorIR().generar(ast_raiz)
