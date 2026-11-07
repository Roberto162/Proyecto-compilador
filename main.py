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
from modulos.lexico import analizar_codigo, mostrar_tokens
from modulos.sintactico import preparar_tokens, AnalizadorSintactico

# Módulo de optimización de código intermedio
from modulos.optimizacion import (
    PASES, PASES_POR_DEFECTO, optimizar_desde_ast, optimizar_archivo_cuadruplos, reoptimizar, reporte
)
from modulos.optimizacion.bloques import exportar_dot
from modulos.optimizacion.suite import ejecutar_suite, listar_tests

# Pases activos (se pueden activar/desactivar desde el submenú)
PASES_ACTIVOS = list(PASES_POR_DEFECTO)


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


# =============================================================================
# SUBMENÚS DEL MÓDULO DE OPTIMIZACIÓN
# =============================================================================
def _pausa():
    input(f"\n{Colores.AZUL}Presiona ENTER para continuar...{Colores.RESET}")


def submenu_configurar_pases():
    """Permite activar/desactivar pases para observar el efecto de cada uno."""
    global PASES_ACTIVOS
    claves = list(PASES.keys())
    while True:
        print(f"\n{Colores.CYAN}=== CONFIGURAR PASES DE OPTIMIZACIÓN ==={Colores.RESET}")
        for i, clave in enumerate(claves, 1):
            nombre, nivel, _ = PASES[clave]
            marca = f"{Colores.VERDE}[X]{Colores.RESET}" if clave in PASES_ACTIVOS else "[ ]"
            print(f"{i}. {marca} {nivel:<18} {nombre}")
        print("T. Activar todos    N. Desactivar todos    0. Terminar")
        opc = input("\nNúmero de pase para alternar: ").strip().upper()
        if opc == "0":
            break
        if opc == "T":
            PASES_ACTIVOS = list(claves)
        elif opc == "N":
            PASES_ACTIVOS = []
        elif opc.isdigit() and 1 <= int(opc) <= len(claves):
            clave = claves[int(opc) - 1]
            if clave in PASES_ACTIVOS:
                PASES_ACTIVOS.remove(clave)
            else:
                PASES_ACTIVOS.append(clave)
        else:
            print(f"{Colores.ROJO}Opción inválida.{Colores.RESET}")


def _exportar_reporte(res):
    base = "".join(c if c.isalnum() else "_" for c in res.titulo)[:40] or "programa"
    ruta_txt = f"reporte_optimizacion_{base}.txt"
    ruta_dot = f"cfg_{base}.dot"
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(reporte.reporte_completo(res))
    with open(ruta_dot, "w", encoding="utf-8") as f:
        f.write(exportar_dot(res.original, "CFG_original") + "\n\n" + exportar_dot(res.optimizado, "CFG_optimizado"))
    print(f"{Colores.VERDE}Reporte guardado en '{ruta_txt}' y CFG (Graphviz) en '{ruta_dot}'.{Colores.RESET}")


def submenu_optimizacion(res):
    """Submenú principal del optimizador para un programa ya cargado."""
    while True:
        m = res.metricas
        estado = f"{Colores.VERDE}EQUIVALENTE{Colores.RESET}" if m.get("equivalente") else f"{Colores.ROJO}NO EQUIVALENTE{Colores.RESET}"
        print(f"\n{Colores.CYAN}=== OPTIMIZACIÓN DE CÓDIGO INTERMEDIO: {res.titulo} ==={Colores.RESET}")
        print(f"    {m['instr_antes']} -> {m['instr_despues']} instrucciones "
              f"({m['reduccion_pct']:.1f}% de reducción) · validación: {estado}")
        print("1. Ver código intermedio original (cuádruplos)")
        print("2. Fase 1: Líderes, bloques básicos y CFG")
        print("3. Fase 2: Traza de pases de optimización (paso a paso)")
        print("4. Ver código intermedio optimizado")
        print("5. Comparación original vs optimizado")
        print("6. Fase 3: Métricas y validación semántica")
        print("7. Reporte completo")
        print("8. Configurar pases activos y re-optimizar")
        print("9. Exportar reporte (.txt) y CFG (.dot)")
        print("10. Volver")

        opc = input("\nSelecciona una opción (1-10): ").strip()
        if opc == "1":
            print("\n" + reporte.tabla_cuadruplos(res.original, "CÓDIGO INTERMEDIO ORIGINAL"))
        elif opc == "2":
            print("\n" + reporte.bloques(res))
        elif opc == "3":
            print("\n" + reporte.traza(res))
        elif opc == "4":
            print("\n" + reporte.tabla_cuadruplos(res.optimizado, "CÓDIGO INTERMEDIO OPTIMIZADO", con_notas=True))
            if res.esperado is not None:
                print("\n" + reporte.tabla_cuadruplos(res.esperado, "SALIDA ESPERADA DEL CASO"))
        elif opc == "5":
            print("\n" + reporte.comparacion(res))
        elif opc == "6":
            print("\n" + reporte.metricas(res))
        elif opc == "7":
            print("\n" + reporte.reporte_completo(res))
        elif opc == "8":
            submenu_configurar_pases()
            res = reoptimizar(res, PASES_ACTIVOS)
            print(f"{Colores.VERDE}Código re-optimizado con {len(PASES_ACTIVOS)} pase(s) activo(s).{Colores.RESET}")
            continue
        elif opc == "9":
            _exportar_reporte(res)
        elif opc == "10":
            break
        else:
            print(f"{Colores.ROJO}Opción inválida.{Colores.RESET}")
            continue
        _pausa()


def menu_archivo_cuadruplos():
    """Optimiza directamente un archivo de cuádruplos (.cuad), p. ej. los casos de /tests."""
    archivos = [r for r in listar_tests() if r.endswith(".cuad")]
    print(f"\n{Colores.CYAN}Archivos de cuádruplos disponibles en /tests:{Colores.RESET}")
    for i, ruta in enumerate(archivos, 1):
        print(f"  {i}. {os.path.basename(ruta)}")
    sel = input("\nNúmero de archivo o ruta a un .cuad: ").strip()
    ruta = archivos[int(sel) - 1] if sel.isdigit() and 1 <= int(sel) <= len(archivos) else sel
    if not os.path.exists(ruta):
        print(f"{Colores.ROJO}Archivo no encontrado.{Colores.RESET}")
        return
    try:
        res = optimizar_archivo_cuadruplos(ruta, PASES_ACTIVOS)
    except Exception as e:
        print(f"{Colores.ROJO}Error al leer los cuádruplos: {e}{Colores.RESET}")
        return
    submenu_optimizacion(res)


def menu_suite_pruebas():
    """Ejecuta todos los archivos de /tests y muestra la matriz comparativa de métricas."""
    filas = ejecutar_suite(pases_activos=PASES_ACTIVOS)
    print("\n" + reporte.matriz_suite(filas))
    sel = input("\nNúmero de fila para ver su detalle (ENTER para volver): ").strip()
    if sel.isdigit() and 1 <= int(sel) <= len(filas):
        fila = filas[int(sel) - 1]
        if "resultado" in fila:
            submenu_optimizacion(fila["resultado"])
        else:
            print(f"{Colores.ROJO}{fila['error']}{Colores.RESET}")


def resumen_analisis(valido, err_lex, err_sint, rep_sem):
    """Muestra de inmediato si el código es válido y cuántos errores hubo en cada fase."""
    errores_sem = rep_sem.count("❌ Error Semántico")
    advertencias = rep_sem.count("⚠ Advertencia")
    print(f"\n{Colores.CYAN}=== RESUMEN DEL ANÁLISIS ==={Colores.RESET}")
    print(f"  Léxico     : {len(err_lex)} error(es)")
    print(f"  Sintáctico : {len(err_sint)} error(es)")
    print(f"  Semántico  : {errores_sem} error(es), {advertencias} advertencia(s)")
    if valido:
        print(f"  {Colores.VERDE}Resultado: VÁLIDO ✅ (se puede generar y optimizar el código intermedio){Colores.RESET}")
    else:
        print(f"  {Colores.ROJO}Resultado: INVÁLIDO ❌ (no se genera código intermedio){Colores.RESET}")


def submenu_resultados(codigo, valido, err_lex, err_sint, rep_sem, tabla_rep, ast_raiz):
    resumen_analisis(valido, err_lex, err_sint, rep_sem)
    while True:
        print(f"\n{Colores.AZUL}=== MENÚ DE RESULTADOS DEL ANÁLISIS ==={Colores.RESET}")
        print("1. Ver resultado del Análisis Léxico (Tokens y Errores)")
        print("2. Ver resultado del Análisis Sintáctico (Matches y Errores)")
        print("3. Ver resultado del Análisis Semántico (Tabla de Símbolos y Reporte)")
        print("4. Ver Generación de Código Intermedio (Seleccionar representación)")
        print("5. Optimización de Código Intermedio (bloques, pases, métricas)")
        print("6. Volver al Menú Principal")

        opcion = input("\nSelecciona una opción para consultar: ").strip()

        if opcion == "1":
            tokens, errores = analizar_codigo(codigo)
            mostrar_tokens(tokens, errores)
            _pausa()
        elif opcion == "2":
            parser = AnalizadorSintactico(preparar_tokens(analizar_codigo(codigo)[0]))
            parser.analizar()
            for paso in parser.traza:
                color = Colores.ROJO if paso.startswith("❌") else ""
                print(f"{color}{paso}{Colores.RESET if color else ''}")
            _pausa()
        elif opcion == "3":
            print(tabla_rep)
            print(rep_sem)
            _pausa()
        elif opcion == "4":
            if valido and ast_raiz:
                submenu_codigo_intermedio(ast_raiz)
            else:
                print(f"{Colores.ROJO}Generación abortada por errores en la expresión.{Colores.RESET}")
        elif opcion == "5":
            if valido and ast_raiz:
                res = optimizar_desde_ast(ast_raiz, codigo, PASES_ACTIVOS)
                submenu_optimizacion(res)
            else:
                print(f"{Colores.ROJO}Optimización abortada: el código tiene errores.{Colores.RESET}")
        elif opcion == "6":
            break
        else:
            print(f"{Colores.ROJO}Opción inválida.{Colores.RESET}")


def modo_terminal():
    while True:
        print(f"\n{Colores.AZUL}=== MODO TERMINAL (CLI) ==={Colores.RESET}")
        print("1. Probar Expresiones de Prueba Obligatorias (Con declaraciones válidas)")
        print("2. Cargar código desde archivo (.txt)")
        print("3. Ingresar expresión manualmente")
        print("4. Optimizar archivo de cuádruplos (.cuad)")
        print("5. Ejecutar suite de pruebas de optimización (/tests)")
        print("6. Volver")

        opc = input("Selecciona opción: ").strip()
        codigo = ""

        if opc == "1":
            print("\nCasos de prueba disponibles:")
            for idx, p in enumerate(EXPRESIONES_PRUEBA_OBLIGATORIAS, 1):
                una_linea = p['expresion'].replace('\n', ' | ')   # (fuera del f-string: compatible con Python < 3.12)
                print(f"  {idx}. {p['id']} ({p['descripcion']}):\n     {una_linea}")

            sel = input(f"\nSelecciona número de prueba (1-{len(EXPRESIONES_PRUEBA_OBLIGATORIAS)}): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(EXPRESIONES_PRUEBA_OBLIGATORIAS):
                codigo = EXPRESIONES_PRUEBA_OBLIGATORIAS[int(sel) - 1]['expresion']
            else:
                print(f"{Colores.ROJO}Selección inválida.{Colores.RESET}")
                continue

        elif opc == "2":
            fuentes = [r for r in listar_tests() if r.endswith(".txt")]
            if fuentes:
                print("\nProgramas de prueba en /tests:")
                for i, r in enumerate(fuentes, 1):
                    print(f"  {i}. {os.path.basename(r)}")
            sel = input("Número de archivo o ruta del archivo (.txt): ").strip()
            ruta = fuentes[int(sel) - 1] if sel.isdigit() and 1 <= int(sel) <= len(fuentes) else sel
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
            menu_archivo_cuadruplos()
            continue
        elif opc == "5":
            menu_suite_pruebas()
            continue
        elif opc == "6":
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