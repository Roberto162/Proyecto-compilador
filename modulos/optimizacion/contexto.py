"""
modulos/optimizacion/contexto.py
================================
Estado compartido entre los pases: variables de salida, bitácora de
transformaciones (traza) e instrucciones eliminadas con su motivo.
"""


class ContextoOptimizacion:
    def __init__(self, salidas):
        self.salidas = set(salidas)      # variables vivas al final del programa
        self.mensajes = []               # mensajes del pase en curso
        self.eliminadas = {}             # origen -> (pase, motivo, cuadruplo)
        self.pase_actual = ""
        self._contador_etiquetas = 0

    def log(self, mensaje):
        self.mensajes.append(mensaje)

    def eliminar(self, q, motivo):
        """Registra la eliminación de una instrucción (para la tabla comparativa)."""
        self.log(f"✘ elimina {q.tac():<24} ({motivo})")
        if q.origen is not None:
            self.eliminadas[q.origen] = (self.pase_actual, motivo, q)

    def nueva_etiqueta(self, existentes, prefijo="L_PRE"):
        while True:
            self._contador_etiquetas += 1
            nombre = f"{prefijo}{self._contador_etiquetas}"
            if nombre not in existentes:
                return nombre
