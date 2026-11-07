"""
modulos/lexico.py
=================
Módulo de Análisis Léxico.
Responsabilidades:
  - Recorrer el código fuente carácter por carácter mediante Expresiones Regulares.
  - Clasificar lexemas en tokens (identificadores, palabras clave, números, operadores, etc.).
  - Registrar números de línea y columna para cada token.
  - Detectar caracteres inválidos (Errores Léxicos) sin detener abruptamente el flujo.
"""

import re
from config import KEYWORDS, TOKEN_REGEX, Colores


def analizar_codigo(codigo: str):
    """
    Realiza el análisis léxico del código fuente.
    
    Retorna:
        tuple: (tokens, errores_lexicos)
            - tokens (list): Lista de diccionarios con la estructura
              {"tipo": str, "lexema": str, "linea": int, "columna": int}
            - errores_lexicos (list): Lista de mensajes de error encontrados.
    """
    tokens = []
    errores_lexicos = []
    linea = 1
    columna = 1
    i = 0
    longitud = len(codigo)

    while i < longitud:
        match = None

        # Probar cada patrón de Expresión Regular en orden de prioridad
        for tipo, regex in TOKEN_REGEX:
            patron = re.compile(regex)
            match = patron.match(codigo, i)

            if match:
                lexema = match.group(0)

                # Descartar espacios en blanco y comentarios para las fases posteriores
                if tipo not in ["ESPACIO", "COMENTARIO"]:
                    t_tipo = tipo

                    # Reclasificar identificadores que sean palabras reservadas
                    if tipo == "IDENTIFICADOR" and lexema in KEYWORDS:
                        t_tipo = "PALABRA_CLAVE"

                    tokens.append({
                        "tipo": t_tipo,
                        "lexema": lexema,
                        "linea": linea,
                        "columna": columna
                    })

                # Actualizar contadores de línea y columna
                if tipo == "NEWLINE":
                    linea += 1
                    columna = 1
                else:
                    columna += len(lexema)

                i = match.end(0)
                break

        # Manejo de Error Léxico (Símbolo no admitido / carácter no reconocido)
        if not match:
            char_invalido = codigo[i]
            errores_lexicos.append(
                f"Error léxico en línea {linea}, columna {columna}: Carácter no reconocido '{char_invalido}'"
            )
            i += 1
            columna += 1

    return tokens, errores_lexicos


def obtener_tabla_tokens_str(tokens):
    """
    Devuelve un string formateado con la tabla de tokens y resumen para consumo en CLI o GUI.
    """
    if not tokens:
        return "No hay tokens registrados."

    lineas_salida = []
    lineas_salida.append(f"\n{'TIPO':<20}{'LEXEMA':<20}{'LÍNEA':<10}{'COLUMNA':<10}")
    lineas_salida.append("-" * 60)

    conteo = {}
    for t in tokens:
        lexema_vis = t['lexema'].replace("\n", "\\n").replace("\t", "\\t")
        lineas_salida.append(f"{t['tipo']:<20}{lexema_vis:<20}{t['linea']:<10}{t['columna']:<10}")
        conteo[t['tipo']] = conteo.get(t['tipo'], 0) + 1

    lineas_salida.append("\n=== RESUMEN LÉXICO ===")
    for tipo, cantidad in conteo.items():
        lineas_salida.append(f"{tipo}: {cantidad}")

    return "\n".join(lineas_salida)


def mostrar_tokens(tokens, errores_lexicos=None):
    """
    Imprime en consola la tabla de tokens y los errores léxicos detectados con color.
    """
    if errores_lexicos:
        print(f"\n{Colores.ROJO}=== ERRORES LÉXICOS DETECTADOS ==={Colores.RESET}")
        for err in errores_lexicos:
            print(f"{Colores.ROJO}  -> {err}{Colores.RESET}")

    if tokens:
        print(f"\n{Colores.AZUL}=== TABLA DE TOKENS ==={Colores.RESET}")
        print(obtener_tabla_tokens_str(tokens))