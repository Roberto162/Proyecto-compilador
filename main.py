"""
main.py
=======
Punto de entrada principal del compilador con submenú interactivo para Código Intermedio.
"""

import os
import sys

from config import Colores, EXPRESIONES_PRUEBA_OBLIGATORIAS
from modulos.semantico import ejecutar_pipeline_completo
from modulos.codigo_intermedio import (
    obtener_polaca_str,
    obtener_codigo_p_str,
    obtener_triplos_str,
    obtener_cuadruplos_str,
    obtener_reporte_codigo_intermedio_str
)
from modulos.lexico import obtener_tabla_tokens_str, analizar_codigo


def submenu_codigo_intermedio(ast_raiz):
    """Submenú para seleccionar el tipo específico de código intermedio a visualizar."""
    while True:
        print(f"\n{Colores.CYAN}=== SELECCIONAR TIPO DE CÓDIGO INTERMEDIO ==={Colores.RESET}")
        print("1. Notación Polaca (Prefija)")
        print("2. Código P (Máquina de Pila)")
        print("3. Triplos")
        print("4. Cuádruplos")
        print("5. Ver Todas las Representaciones")
        print("6. Volver al Menú Anterior")

        opc = input("\nSelecciona una representación (1-6): ").strip()

        if opc == "1":
            print(f"\n{obtener_polaca_str(ast_raiz)}")
        elif opc == "2":
            print(f"\n{obtener_codigo_p_str(ast_raiz)}")
        elif opc == "3":
            print(f"\n{obtener_triplos_str(ast_raiz)}")
        elif opc == "4":
            print(f"\n{obtener_cuadruplos_str(ast_raiz)}")
        elif opc == "5":
            print(f"\n{obtener_reporte_codigo_intermedio_str(ast_raiz)}")
        elif opc == "6":
            break
        else:
            print(f"{Colores.ROJO}Opción inválida.{Colores.RESET}")

        input(f"\n{Colores.AZUL}Presiona ENTER para continuar...{Colores.RESET}")


def submenu_resultados(codigo, valido, err_lex, err_sint, rep_sem, tabla_rep, ast_raiz):
    while True:
        print(f"\n{Colores.AZUL}=== MENÚ DE RESULTADOS DEL ANÁLISIS ==={Colores.RESET}")
        print("1. Ver resultado del Análisis Léxico (Tokens)")
        print("2. Ver resultado del Análisis Sintáctico (Matches y Errores)")
        print("3. Ver resultado del Análisis Semántico (Tabla de Símbolos y Reporte)")
        print("4. Ver Generación de Código Intermedio (Seleccionar representación)")
        print("5. Volver al Menú Principal")

        opcion = input("\nSelecciona una opción para consultar: ").strip()

        if opcion == "1":
            tokens, _ = analizar_codigo(codigo)
            print(obtener_tabla_tokens_str(tokens))
        elif opcion == "2":
            from modulos.sintactico import preparar_tokens, AnalizadorSintactico
            tokens_sint = preparar_tokens(analizar_codigo(codigo)[0])
            parser = AnalizadorSintactico(tokens_sint)
            parser.analizar()
            for paso in parser.traza:
                print(paso)
        elif opcion == "3":
            print(tabla_rep)
            print(rep_sem)
        elif opcion == "4":
            if valido and ast_raiz:
                submenu_codigo_intermedio(ast_raiz)
            else:
                print(f"{Colores.ROJO}Generación abortada por errores en la expresión.{Colores.RESET}")
        elif opcion == "5":
            break
        else:
            print(f"{Colores.ROJO}Opción inválida.{Colores.RESET}")


def modo_terminal():
    while True:
        print(f"\n{Colores.AZUL}=== MODO TERMINAL (CLI) ==={Colores.RESET}")
        print("1. Probar Expresiones de Prueba Obligatorias (Con declaraciones válidas)")
        print("2. Cargar código desde archivo (.txt)")
        print("3. Ingresar expresión manualmente")
        print("4. Volver")

        opc = input("Selecciona opción: ").strip()
        codigo = ""

        if opc == "1":
            print("\nCasos de prueba disponibles:")
            for idx, p in enumerate(EXPRESIONES_PRUEBA_OBLIGATORIAS, 1):
                print(f"  {idx}. {p['id']} ({p['descripcion']}):\n     {p['expresion'].replace('\n', ' | ')}")

            sel = input("\nSelecciona número de prueba (1-5): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(EXPRESIONES_PRUEBA_OBLIGATORIAS):
                codigo = EXPRESIONES_PRUEBA_OBLIGATORIAS[int(sel) - 1]['expresion']
            else:
                print(f"{Colores.ROJO}Selección inválida.{Colores.RESET}")
                continue

        elif opc == "2":
            ruta = input("Ingresa la ruta del archivo (.txt): ").strip()
            if os.path.exists(ruta):
                try:
                    with open(ruta, 'r', encoding='utf-8') as f:
                        codigo = f.read()
                except Exception as e:
                    print(f"{Colores.ROJO}Error al leer archivo: {e}{Colores.RESET}")
                    continue
            else:
                print(f"{Colores.ROJO}Archivo no encontrado.{Colores.RESET}")
                continue

        elif opc == "3":
            print("\nEscribe tu código (Escribe 'FIN' para procesar):")
            lineas = []
            while True:
                linea = sys.stdin.readline()
                if not linea or linea.strip().upper() == "FIN":
                    break
                lineas.append(linea)
            codigo = "".join(lineas)

        elif opc == "4":
            break
        else:
            print(f"{Colores.ROJO}Opción no válida.{Colores.RESET}")
            continue

        if not codigo.strip():
            print(f"{Colores.AMARILLO}Código vacío.{Colores.RESET}")
            continue

        valido, err_lex, err_sint, rep_sem, tabla_rep, ast_raiz = ejecutar_pipeline_completo(codigo)
        submenu_resultados(codigo, valido, err_lex, err_sint, rep_sem, tabla_rep, ast_raiz)


def modo_gui():
    try:
        from interfaz.gui import ejecutar_interfaz_grafica
        ejecutar_interfaz_grafica()
    except Exception as e:
        print(f"{Colores.ROJO}Error al iniciar la GUI: {e}{Colores.RESET}")


def menu_principal():
    while True:
        print(f"\n{Colores.AZUL}============================================")
        print("  GENERADOR DE CÓDIGO INTERMEDIO COMPLETO  ")
        print(f"============================================{Colores.RESET}")
        print("1. Modo Terminal (CLI)")
        print("2. Modo Interfaz Gráfica (GUI)")
        print("3. Salir")

        opcion = input("\nSelecciona opción: ").strip()

        if opcion == "1":
            modo_terminal()
        elif opcion == "2":
            modo_gui()
        elif opcion == "3":
            print(f"\n{Colores.VERDE}¡Programa finalizado exitosamente!{Colores.RESET}")
            break
        else:
            print(f"{Colores.ROJO}Opción inválida.{Colores.RESET}")


if __name__ == "__main__":
    menu_principal()