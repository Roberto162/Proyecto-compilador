"""
main.py
=======
Punto de entrada principal del compilador con submenú interactivo para Código Intermedio.
"""

import os
import sys

from config import Colores, EXPRESIONES_PRUEBA_OBLIGATORIAS, DIRECTORIO_TESTS
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
    PASES, PASES_POR_DEFECTO, NIVELES, DESCRIPCION_PASES, optimizar_desde_ast, optimizar_texto_cuadruplos, reoptimizar, reporte
)

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
            continue
        _pausa()


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
        # Los pases se muestran agrupados por tipo: locales, globales, ciclos y mirilla
        for nivel, explicacion in NIVELES.items():
            print(f"\n  {Colores.AZUL}{nivel}{Colores.RESET} — {explicacion}")
            for i, clave in enumerate(claves, 1):
                nombre, nivel_pase, _ = PASES[clave]
                if nivel_pase == nivel:
                    marca = f"{Colores.VERDE}[X]{Colores.RESET}" if clave in PASES_ACTIVOS else "[ ]"
                    print(f"    {i}. {marca} {nombre}")
                    print(f"          {DESCRIPCION_PASES[clave]}")
        print()
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


def submenu_optimizacion(res):
    """Submenú del optimizador (las mismas vistas que la pestaña Optimización de la GUI)."""
    while True:
        m = res.metricas
        estado = f"{Colores.VERDE}EQUIVALENTE{Colores.RESET}" if m.get("equivalente") else f"{Colores.ROJO}NO EQUIVALENTE{Colores.RESET}"
        print(f"\n{Colores.CYAN}=== OPTIMIZACIÓN DE CÓDIGO INTERMEDIO: {res.titulo} ==={Colores.RESET}")
        print(f"    {m['instr_antes']} -> {m['instr_despues']} instrucciones "
              f"({m['reduccion_pct']:.1f}% de reducción) · validación: {estado}")
        print("1. Original vs Optimizado")
        print("2. Transformaciones (qué le pasó a cada instrucción)")
        print("3. Bloques básicos y CFG")
        print("4. Métricas y validación")
        print("5. Configurar pases y re-optimizar")
        print("6. Volver")

        opc = input("\nSelecciona una opción (1-6): ").strip()
        if opc == "1":
            print("\n" + reporte.lado_a_lado(res))
        elif opc == "2":
            print("\n" + reporte.comparacion(res))
            print("\n" + reporte.tabla_cuadruplos(res.optimizado, "CÓDIGO OPTIMIZADO", con_notas=True))
            if res.esperado is not None:
                print("\n" + reporte.tabla_cuadruplos(res.esperado, "SALIDA ESPERADA DEL CASO"))
        elif opc == "3":
            print("\n" + reporte.bloques(res))
        elif opc == "4":
            print("\n" + reporte.metricas(res))
        elif opc == "5":
            submenu_configurar_pases()
            res = reoptimizar(res, PASES_ACTIVOS)
            print(f"{Colores.VERDE}Código re-optimizado con {len(PASES_ACTIVOS)} pase(s) activo(s).{Colores.RESET}")
            continue
        elif opc == "6":
            break
        else:
            print(f"{Colores.ROJO}Opción inválida.{Colores.RESET}")
            continue
        _pausa()


def casos_de_optimizacion():
    """Casos del optimizador: archivos .cuad de /tests (ya escritos en cuádruplos).
    Se nombran OPT_1, OPT_2... con el título de la primera línea de comentario de cada archivo."""
    if not os.path.isdir(DIRECTORIO_TESTS):
        return []
    casos = []
    archivos = sorted(f for f in os.listdir(DIRECTORIO_TESTS) if f.endswith(".cuad"))
    for n, nombre in enumerate(archivos, 1):
        with open(os.path.join(DIRECTORIO_TESTS, nombre), "r", encoding="utf-8") as f:
            texto = f.read()
        primera = next((l.lstrip("# ").strip() for l in texto.splitlines() if l.startswith("#")), nombre)
        titulo = primera.split(":", 1)[1].strip() if ":" in primera else primera
        casos.append((f"OPT_{n}: {titulo} (cuádruplos)", texto, True))
    return casos


def optimizar_cuadruplos(texto, titulo=None):
    """Los cuádruplos ya son código intermedio: van directo al optimizador (sin léxico,
    sintáctico, semántico ni generador)."""
    try:
        res = optimizar_texto_cuadruplos(texto, PASES_ACTIVOS, titulo)
    except Exception as e:
        print(f"{Colores.ROJO}Error al leer los cuádruplos: {e}{Colores.RESET}")
        return
    submenu_optimizacion(res)


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
        print("1. Casos de prueba (código fuente y casos del optimizador)")
        print("2. Cargar archivo (.txt código fuente / .cuad cuádruplos)")
        print("3. Ingresar expresión manualmente")
        print("4. Volver")

        opc = input("Selecciona opción: ").strip()
        codigo = ""

        if opc == "1":
            # PRUEBA_n / ERROR_n: código fuente (config.py) · OPT_n: cuádruplos (.cuad de /tests)
            casos = [(f"{p['id']}: {p['descripcion']}", p['expresion'], False) for p in EXPRESIONES_PRUEBA_OBLIGATORIAS]
            casos += casos_de_optimizacion()
            print("\nCasos de prueba disponibles:")
            for idx, (nombre, _, _) in enumerate(casos, 1):
                print(f"  {idx:>2}. {nombre}")

            sel = input(f"\nSelecciona número de caso (1-{len(casos)}): ").strip()
            if not (sel.isdigit() and 1 <= int(sel) <= len(casos)):
                print(f"{Colores.ROJO}Selección inválida.{Colores.RESET}")
                continue
            nombre, texto, es_cuadruplos = casos[int(sel) - 1]
            if es_cuadruplos:
                optimizar_cuadruplos(texto, nombre.split(":")[0])
                continue
            codigo = texto

        elif opc == "2":
            ruta = input("Ruta del archivo (.txt o .cuad): ").strip()
            if not os.path.exists(ruta):
                print(f"{Colores.ROJO}Archivo no encontrado.{Colores.RESET}")
                continue
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    codigo = f.read()
            except Exception as e:
                print(f"{Colores.ROJO}Error al leer archivo: {e}{Colores.RESET}")
                continue
            if ruta.lower().endswith(".cuad"):
                optimizar_cuadruplos(codigo)
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