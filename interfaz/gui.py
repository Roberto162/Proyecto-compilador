"""
interfaz/gui.py
===============
Interfaz gráfica del compilador: análisis léxico, sintáctico, semántico,
generación de código intermedio y optimización.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from css import aplicar_estilo_oscuro, TEXT_AREA_ARGS

from config import EXPRESIONES_PRUEBA_OBLIGATORIAS, DIRECTORIO_TESTS
from modulos.lexico import obtener_tabla_tokens_str, analizar_codigo
from modulos.sintactico import preparar_tokens, AnalizadorSintactico
from modulos.semantico import ejecutar_pipeline_completo
from modulos.codigo_intermedio import (
    obtener_polaca_str,
    obtener_codigo_p_str,
    obtener_triplos_str,
    obtener_cuadruplos_str
)

# Módulo de optimización de código intermedio
from modulos.optimizacion import (
    PASES, NIVELES, optimizar_desde_ast, optimizar_texto_cuadruplos, reoptimizar, reporte
)

ESPACIOS_POR_TAB = 4


class EditorCodigo(ttk.Frame):
    """
    Componente personalizado de área de código con numeración de líneas
    y línea separadora vertical estilo IDE.
    """
    def __init__(self, parent, height=5, *args, **kwargs):
        super().__init__(parent)

        # Canvas lateral izquierdo para renderizar los números de línea
        self.canvas_lineas = tk.Canvas(self, width=42, bg="#1e1e1e", highlightthickness=0)
        self.canvas_lineas.pack(side="left", fill="y")

        # Área principal de texto con barra de desplazamiento (ttk: respeta el tema oscuro)
        self.vbar = ttk.Scrollbar(self, orient="vertical")
        self.vbar.pack(side="right", fill="y")
        self.txt = tk.Text(
            self,
            height=height,
            font=("Consolas", 11),
            bg="#252526",
            fg="#d4d4d4",
            insertbackground="white",
            bd=0,
            highlightthickness=0,
            undo=True,
            *args, **kwargs
        )
        self.txt.pack(side="right", fill="both", expand=True)

        # La numeración se actualiza también al arrastrar la barra de desplazamiento
        self.vbar.configure(command=self.txt.yview)
        self.txt.configure(yscrollcommand=self._al_desplazar)

        # Eventos para actualizar la numeración en tiempo real
        self.txt.bind("<KeyRelease>", self.actualizar_lineas)
        self.txt.bind("<MouseWheel>", self.actualizar_lineas)
        self.txt.bind("<Button-1>", self.actualizar_lineas)
        self.txt.bind("<Configure>", self.actualizar_lineas)
        # La sangría define los bloques: TAB inserta espacios (el léxico cuenta un tab como 1 columna)
        self.txt.bind("<Tab>", self._insertar_espacios)

        self.actualizar_lineas()

    def _al_desplazar(self, *args):
        self.vbar.set(*args)
        self.actualizar_lineas()

    def _insertar_espacios(self, event=None):
        self.txt.insert("insert", " " * ESPACIOS_POR_TAB)
        return "break"

    def actualizar_lineas(self, event=None):
        self.canvas_lineas.delete("all")

        # Dibujar la línea separadora vertical (estilo VS Code / PyCharm)
        self.canvas_lineas.create_line(41, 0, 41, self.winfo_height(), fill="#333333")

        # Calcular y renderizar los números visibles
        i = self.txt.index("@0,0")
        while True:
            dline = self.txt.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            num_linea = str(i).split(".")[0]
            self.canvas_lineas.create_text(
                34, y, anchor="ne", text=num_linea, fill="#858585", font=("Consolas", 10)
            )
            i = self.txt.index(f"{i}+1line")

    # Métodos proxy para usar el editor como un widget Text normal
    def get(self, *args, **kwargs):
        return self.txt.get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        res = self.txt.delete(*args, **kwargs)
        self.after(10, self.actualizar_lineas)
        return res

    def insert(self, *args, **kwargs):
        res = self.txt.insert(*args, **kwargs)
        self.after(10, self.actualizar_lineas)
        return res


def crear_area_texto(parent, wrap="none"):
    """Área de texto con barras de desplazamiento vertical y horizontal (para tablas anchas)."""
    marco = ttk.Frame(parent)
    txt = tk.Text(marco, wrap=wrap, **TEXT_AREA_ARGS)
    sy = ttk.Scrollbar(marco, orient="vertical", command=txt.yview)
    sx = ttk.Scrollbar(marco, orient="horizontal", command=txt.xview)
    txt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    txt.grid(row=0, column=0, sticky="nsew")
    sy.grid(row=0, column=1, sticky="ns")
    sx.grid(row=1, column=0, sticky="ew")
    marco.rowconfigure(0, weight=1)
    marco.columnconfigure(0, weight=1)
    return marco, txt


class InterfazCompilador:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilador de Código (FASE DE OPTIMIZACION)")
        # El tamaño se adapta a la pantalla (en pantallas pequeñas no se corta la parte de abajo)
        ancho = min(1150, self.root.winfo_screenwidth() - 60)
        alto = min(820, self.root.winfo_screenheight() - 100)
        self.root.geometry(f"{ancho}x{alto}")
        self.root.minsize(800, 500)
        self.resultado_opt = None

        # Se aplica el estilo oscuro y se inicializan todos los componentes
        aplicar_estilo_oscuro(self.root)
        self._crear_componentes()

    # =====================================================================
    # CONSTRUCCIÓN DE LA INTERFAZ
    # =====================================================================
    def _crear_componentes(self):
        # La barra de estado se coloca primero para que nunca quede fuera de la ventana
        self.lbl_estado = ttk.Label(self.root, text="Estado: Listo.", relief="sunken", anchor="w")
        self.lbl_estado.pack(side="bottom", fill="x")

        # Panel dividido: arrastra la línea entre el editor y los resultados para cambiar sus tamaños
        self.panel_principal = ttk.PanedWindow(self.root, orient="vertical")
        self.panel_principal.pack(fill="both", expand=True, padx=10, pady=5)

        # Frame superior
        frame_top = ttk.LabelFrame(self.panel_principal, text=" Código Fuente de Entrada ", padding=8)
        self.panel_principal.add(frame_top, weight=1)

        # La fila de botones se coloca ANTES que el editor (abajo del recuadro) para que nunca
        # quede oculta al hacer pequeño el panel superior
        frame_btn = ttk.Frame(frame_top, style="Panel.TFrame")
        frame_btn.pack(side="bottom", fill="x", pady=(5, 0))

        self.txt_entrada = EditorCodigo(frame_top, height=6)
        self.txt_entrada.pack(side="top", fill="both", expand=True)

        ttk.Button(frame_btn, text="📁 Cargar Archivo (.txt)", command=self.cargar_archivo).pack(side="left", padx=2)
        ttk.Button(frame_btn, text="🚀 Analizar y Generar Código", command=self.procesar_codigo).pack(side="left", padx=2)
        ttk.Button(frame_btn, text="🧹 Limpiar", style="Secundario.TButton", command=self.limpiar_campos).pack(side="left", padx=2)

        lbl_pruebas = ttk.Label(frame_btn, text=" Casos de Prueba:", style="Panel.TLabel")
        lbl_pruebas.pack(side="left", padx=(15, 2))

        # Casos de prueba: (nombre visible, texto, es_cuadruplos)
        #   - PRUEBA_n / ERROR_n : código fuente definido en config.py
        #   - OPT_n              : casos de optimización (.cuad de /tests), ya escritos en cuádruplos
        self.casos_prueba = [(f"{p['id']}: {p['descripcion']}", p['expresion'], False)
                             for p in EXPRESIONES_PRUEBA_OBLIGATORIAS]
        self.casos_prueba += self._casos_de_optimizacion()
        self.modo_cuadruplos = False      # True cuando el editor contiene cuádruplos en vez de código fuente

        self.cb_pruebas = ttk.Combobox(frame_btn, state="readonly", width=48)
        self.cb_pruebas['values'] = [nombre for nombre, _, _ in self.casos_prueba]
        self.cb_pruebas.pack(side="left", padx=2)
        self.cb_pruebas.bind("<<ComboboxSelected>>", self.cargar_prueba_seleccionada)

        # Notebook Principal
        frame_bottom = ttk.LabelFrame(self.panel_principal, text=" Resultados del Análisis y Generación ", padding=8)
        self.panel_principal.add(frame_bottom, weight=4)

        self.notebook = ttk.Notebook(frame_bottom)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: Léxico
        self.tab_lexico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_lexico, text=" 🔤 Análisis Léxico ")
        marco, self.txt_lexico = crear_area_texto(self.tab_lexico)
        marco.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 2: Sintáctico
        self.tab_sintactico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sintactico, text=" 🌲 Análisis Sintáctico ")
        marco, self.txt_sintactico = crear_area_texto(self.tab_sintactico)
        marco.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 3: Semántico
        self.tab_semantico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_semantico, text=" 📊 Tabla de Símbolos & Semántica ")
        marco, self.txt_semantico = crear_area_texto(self.tab_semantico)
        marco.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 4: Código Intermedio con Sub-Notebook
        self.tab_codigo_intermedio = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_codigo_intermedio, text=" ⚡ Código Intermedio ")

        self.sub_notebook = ttk.Notebook(self.tab_codigo_intermedio)
        self.sub_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.txt_polaca = self._sub_tab(self.sub_notebook, " Notación Polaca ")
        self.txt_codigo_p = self._sub_tab(self.sub_notebook, " Código P (Pila) ")
        self.txt_triplos = self._sub_tab(self.sub_notebook, " Triplos ")
        self.txt_cuadruplos = self._sub_tab(self.sub_notebook, " Cuádruplos ")

        # Tab 5: Optimización de Código Intermedio
        self._crear_tab_optimizacion()

    def _alternar_pases(self):
        """Muestra u oculta las casillas de los pases para dejar más espacio a los resultados."""
        self._pases_visibles = not self._pases_visibles
        if self._pases_visibles:
            self.frame_pases.pack(fill="x", pady=(6, 0))
        else:
            self.frame_pases.pack_forget()
        self._actualizar_boton_pases()

    def _actualizar_boton_pases(self):
        activos = sum(v.get() for v in self.vars_pases.values())
        flecha = "▾" if self._pases_visibles else "▸"
        self.btn_pases.config(text=f"⚙ Pases ({activos}/{len(self.vars_pases)}) {flecha}")

    def _sub_tab(self, notebook, titulo):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=titulo)
        marco, txt = crear_area_texto(frame)
        marco.pack(fill="both", expand=True, padx=5, pady=5)
        return txt

    def _crear_tab_optimizacion(self):
        self.tab_optimizacion = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_optimizacion, text=" 🛠 Optimización ")

        # Barra de control: una sola fila de botones; las casillas de pases se muestran/ocultan
        frame_ctrl = ttk.Frame(self.tab_optimizacion, style="Panel.TFrame", padding=4)
        frame_ctrl.pack(fill="x", padx=5, pady=(5, 0))

        frame_acc = ttk.Frame(frame_ctrl, style="Panel.TFrame")
        frame_acc.pack(fill="x")
        self.btn_pases = ttk.Button(frame_acc, style="Secundario.TButton", command=self._alternar_pases)
        self.btn_pases.pack(side="left", padx=2)

        # Casillas de pases agrupadas por tipo (local, global, ciclos, mirilla) con su explicación
        self.frame_pases = ttk.Frame(frame_ctrl, style="Panel.TFrame")      # oculto al inicio
        self.vars_pases = {}
        for fila, (nivel, explicacion) in enumerate(NIVELES.items()):
            grupo = ttk.LabelFrame(self.frame_pases, text=f" {nivel} ", padding=4)
            grupo.grid(row=fila // 2, column=fila % 2, sticky="nsew", padx=3, pady=2)
            ttk.Label(grupo, text=explicacion, style="Panel.TLabel", foreground="#90A4AE",
                      wraplength=430, justify="left").pack(anchor="w")
            for clave, (nombre, nivel_pase, _) in PASES.items():
                if nivel_pase == nivel:
                    var = tk.BooleanVar(value=True)
                    self.vars_pases[clave] = var
                    ttk.Checkbutton(grupo, text=nombre, variable=var,
                                    command=self._actualizar_boton_pases).pack(anchor="w")
        self.frame_pases.columnconfigure(0, weight=1)
        self.frame_pases.columnconfigure(1, weight=1)
        self._pases_visibles = False
        self._actualizar_boton_pases()

        # Vuelve a optimizar el mismo código usando sólo los pases marcados en "⚙ Pases"
        ttk.Button(frame_acc, text="🔁 Re-optimizar", command=self.reoptimizar_actual).pack(side="left", padx=2)


        self.sub_notebook_opt = ttk.Notebook(self.tab_optimizacion)
        self.sub_notebook_opt.pack(fill="both", expand=True, padx=5, pady=5)

        # Sub-tab: Comparación lado a lado
        tab_cmp = ttk.Frame(self.sub_notebook_opt)
        self.sub_notebook_opt.add(tab_cmp, text=" Original vs Optimizado ")
        panel = ttk.PanedWindow(tab_cmp, orient="horizontal")
        panel.pack(fill="both", expand=True)
        izq, der = ttk.Frame(panel), ttk.Frame(panel)
        panel.add(izq, weight=1)
        panel.add(der, weight=1)
        self.lbl_opt_original = ttk.Label(izq, text=" Código original")
        self.lbl_opt_original.pack(anchor="w")
        marco, self.txt_opt_original = crear_area_texto(izq)
        marco.pack(fill="both", expand=True, padx=2, pady=2)
        self.lbl_opt_optimizado = ttk.Label(der, text=" Código optimizado")
        self.lbl_opt_optimizado.pack(anchor="w")
        marco, self.txt_opt_optimizado = crear_area_texto(der)
        marco.pack(fill="both", expand=True, padx=2, pady=2)
        for txt in (self.txt_opt_original, self.txt_opt_optimizado):
            txt.tag_configure("eliminada", foreground="#EF5350", overstrike=True)
            txt.tag_configure("modificada", foreground="#FFCA28")
            txt.tag_configure("movida", foreground="#4FC3F7")
            txt.tag_configure("nota", foreground="#81C784")

        self.txt_opt_transf = self._sub_tab(self.sub_notebook_opt, " Transformaciones ")
        self.txt_opt_bloques = self._sub_tab(self.sub_notebook_opt, " Bloques Básicos / CFG ")
        self.txt_opt_metricas = self._sub_tab(self.sub_notebook_opt, " Métricas y Validación ")

    # =====================================================================
    # ENTRADA DE CÓDIGO
    # =====================================================================
    def _leer_codigo(self):
        # "end-1c" quita sólo el salto final que agrega Tk; NO se hace strip() para que
        # los números de línea de los errores coincidan con los del editor
        return self.txt_entrada.get("1.0", "end-1c")

    def _poner_codigo(self, texto):
        self.txt_entrada.delete("1.0", tk.END)
        self.txt_entrada.insert(tk.END, texto)

    def cargar_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de código fuente o de cuádruplos",
            filetypes=[("Código fuente o cuádruplos", "*.txt *.cuad"), ("Código fuente", "*.txt"),
                       ("Cuádruplos", "*.cuad"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    self._poner_codigo(f.read())
                self.modo_cuadruplos = ruta.lower().endswith(".cuad")
                self.cb_pruebas.set("")
                tipo = "cuádruplos (va directo al optimizador)" if self.modo_cuadruplos else "código fuente"
                self.lbl_estado.config(text=f"Estado: Archivo '{ruta}' cargado como {tipo}.")
            except Exception as e:
                messagebox.showerror("Error de Lectura", f"No se pudo leer el archivo:\n{e}")

    def cargar_prueba_seleccionada(self, event):
        idx = self.cb_pruebas.current()
        if idx >= 0:
            nombre, codigo, es_cuadruplos = self.casos_prueba[idx]
            self._poner_codigo(codigo)
            self.modo_cuadruplos = es_cuadruplos
            if es_cuadruplos:
                self.procesar_codigo()          # los casos de optimización se muestran de inmediato
            else:
                self.lbl_estado.config(text=f"Estado: Cargado {nombre}")

    def _limpiar_resultados(self):
        for txt in (self.txt_lexico, self.txt_sintactico, self.txt_semantico, self.txt_polaca,
                    self.txt_codigo_p, self.txt_triplos, self.txt_cuadruplos):
            txt.delete("1.0", tk.END)
        self._limpiar_optimizacion()

    def limpiar_campos(self):
        self.txt_entrada.delete("1.0", tk.END)
        self._limpiar_resultados()
        self.cb_pruebas.set("")
        self.resultado_opt = None
        self.modo_cuadruplos = False
        self.lbl_estado.config(text="Estado: Campos limpiados.")

    # =====================================================================
    # ANÁLISIS COMPLETO
    # =====================================================================
    def procesar_codigo(self):
        codigo = self._leer_codigo()
        if not codigo.strip():
            messagebox.showwarning("Atención", "El cuadro de código fuente está vacío.")
            return

        # Sólo se limpian los resultados: el código del editor no se toca
        self._limpiar_resultados()

        if self.modo_cuadruplos:
            self._procesar_cuadruplos(codigo)
            return

        # 1. Léxico (errores y tabla de tokens)
        tokens_lex, err_lex = analizar_codigo(codigo)
        if err_lex:
            self.txt_lexico.insert(tk.END, "❌ ERRORES LÉXICOS DETECTADOS:\n" + "-" * 50 + "\n")
            for e in err_lex:
                self.txt_lexico.insert(tk.END, f"-> {e}\n")
            self.txt_lexico.insert(tk.END, "\n")
        self.txt_lexico.insert(tk.END, obtener_tabla_tokens_str(tokens_lex))

        # 2. Sintáctico
        parser = AnalizadorSintactico(preparar_tokens(tokens_lex))
        parser.analizar()

        self.txt_sintactico.insert(tk.END, "==================================================\n")
        self.txt_sintactico.insert(tk.END, "    TRAZA DE DERIVACIÓN SINTÁCTICA (MATCHES)      \n")
        self.txt_sintactico.insert(tk.END, "==================================================\n\n")
        for paso in parser.traza:
            self.txt_sintactico.insert(tk.END, f"{paso}\n")

        if parser.errores:
            self.txt_sintactico.insert(tk.END, "\n" + "=" * 50 + "\n")
            self.txt_sintactico.insert(tk.END, "❌ ERRORES SINTÁCTICOS DETECTADOS:\n")
            self.txt_sintactico.insert(tk.END, "=" * 50 + "\n")
            for e in parser.errores:
                self.txt_sintactico.insert(tk.END, f"-> {e}\n")

        # 3. Semántico (el pipeline completo determina si el programa es válido)
        valido, _, _, rep_sem, tabla_rep, ast_raiz = ejecutar_pipeline_completo(codigo)
        self.txt_semantico.insert(tk.END, f"{tabla_rep}\n\n{rep_sem}")

        # 4. Código intermedio y 5. Optimización (sólo si no hay errores)
        if valido and ast_raiz:
            self.txt_polaca.insert(tk.END, obtener_polaca_str(ast_raiz))
            self.txt_codigo_p.insert(tk.END, obtener_codigo_p_str(ast_raiz))
            self.txt_triplos.insert(tk.END, obtener_triplos_str(ast_raiz))
            self.txt_cuadruplos.insert(tk.END, obtener_cuadruplos_str(ast_raiz))

            res = optimizar_desde_ast(ast_raiz, codigo, self._pases_seleccionados(), titulo="Código fuente")
            self.mostrar_resultado_optimizacion(res)

            self.notebook.select(self.tab_codigo_intermedio)
            m = res.metricas
            self.lbl_estado.config(
                text=f"Estado: Código Intermedio Generado ✅ · Optimización: {m['instr_antes']} -> "
                     f"{m['instr_despues']} instrucciones ({m['reduccion_pct']:.1f}%)")
        else:
            msg = "🚫 GENERACIÓN ABORTADA:\nNo se genera Código Intermedio si la expresión contiene errores."
            for txt in (self.txt_polaca, self.txt_codigo_p, self.txt_triplos, self.txt_cuadruplos):
                txt.insert(tk.END, msg)
            self.resultado_opt = None
            self._limpiar_optimizacion("🚫 OPTIMIZACIÓN ABORTADA:\nNo se optimiza código intermedio si la expresión contiene errores.")
            # Se muestra la primera pestaña con errores
            if err_lex:
                self.notebook.select(self.tab_lexico)
            elif parser.errores:
                self.notebook.select(self.tab_sintactico)
            else:
                self.notebook.select(self.tab_semantico)
            self.lbl_estado.config(text="Estado: Proceso completado con errores ❌")

    # =====================================================================
    # OPTIMIZACIÓN
    # =====================================================================
    def _pases_seleccionados(self):
        return [k for k, v in self.vars_pases.items() if v.get()]

    def _limpiar_optimizacion(self, mensaje=""):
        for txt in (self.txt_opt_original, self.txt_opt_optimizado, self.txt_opt_transf,
                    self.txt_opt_bloques, self.txt_opt_metricas):
            txt.delete("1.0", tk.END)
            if mensaje:
                txt.insert(tk.END, mensaje)

    def mostrar_resultado_optimizacion(self, res):
        self.resultado_opt = res
        self._limpiar_optimizacion()
        estados = {num: estado for num, _, estado, _, _ in reporte.estado_instrucciones(res)}

        # Panel izquierdo: original coloreado según lo que le ocurrió a cada instrucción
        encabezado = f"{'#':>3}  {'OP':<8}{'ARG 1':<10}{'ARG 2':<10}{'RES':<9}  TAC\n" + "-" * 60 + "\n"
        self.txt_opt_original.insert(tk.END, encabezado)
        self.txt_opt_optimizado.insert(tk.END, encabezado)

        def fila(i, q):
            op, a1, a2, r = q.campos_visibles()
            return f"{i:>3}  {op:<8}{a1:<10}{a2:<10}{r:<9}  {q.tac()}\n"

        for i, q in enumerate(res.original, 1):
            estado = estados.get(q.origen, "igual")
            self.txt_opt_original.insert(tk.END, fila(i, q), () if estado == "igual" else (estado,))
        # Panel derecho: optimizado con la transformación aplicada
        for i, q in enumerate(res.optimizado, 1):
            tag = "movida" if any(n.startswith("LICM") for n in q.notas) else ("modificada" if q.notas else ())
            self.txt_opt_optimizado.insert(tk.END, fila(i, q), tag)
            if q.notas:
                self.txt_opt_optimizado.insert(tk.END, f"      ↳ {'; '.join(q.notas)}\n", "nota")

        m = res.metricas
        self.lbl_opt_original.config(
            text=f" Código original ({m['instr_antes']} instr.)  —  rojo: eliminada · amarillo: modificada · azul: movida")
        self.lbl_opt_optimizado.config(
            text=f" Código optimizado ({m['instr_despues']} instr., -{m['reduccion_pct']:.1f}%)")

        self.txt_opt_transf.insert(tk.END, reporte.comparacion(res) + "\n\n" +
                                   reporte.tabla_cuadruplos(res.optimizado, "CÓDIGO OPTIMIZADO", con_notas=True))
        if res.esperado is not None:
            self.txt_opt_transf.insert(tk.END, "\n\n" + reporte.tabla_cuadruplos(res.esperado, "SALIDA ESPERADA DEL CASO"))
        self.txt_opt_bloques.insert(tk.END, reporte.bloques(res))
        self.txt_opt_metricas.insert(tk.END, reporte.metricas(res))

        valido = "EQUIVALENTE ✅" if m.get("equivalente") else "NO EQUIVALENTE ❌"
        self.lbl_estado.config(text=f"Estado: Optimización '{res.titulo}': {m['instr_antes']} -> "
                                    f"{m['instr_despues']} instrucciones ({m['reduccion_pct']:.1f}%) · {valido}")

    def reoptimizar_actual(self):
        """Vuelve a optimizar el MISMO código usando sólo los pases marcados en '⚙ Pases'.
        Sirve para comparar el resultado con y sin un pase y ver qué aporta cada uno."""
        if self.resultado_opt is None:
            messagebox.showinfo("Optimización", "Primero analiza un caso de prueba o un código.")
            return
        self.mostrar_resultado_optimizacion(reoptimizar(self.resultado_opt, self._pases_seleccionados()))

    def _casos_de_optimizacion(self):
        """Lee los casos .cuad de /tests y los nombra OPT_n con el título de su primera línea."""
        casos = []
        if not os.path.isdir(DIRECTORIO_TESTS):
            return casos
        archivos = sorted(f for f in os.listdir(DIRECTORIO_TESTS) if f.endswith(".cuad"))
        for n, nombre in enumerate(archivos, 1):
            with open(os.path.join(DIRECTORIO_TESTS, nombre), "r", encoding="utf-8") as f:
                texto = f.read()
            primera = next((l.lstrip("# ").strip() for l in texto.splitlines() if l.startswith("#")), nombre)
            titulo = primera.split(":", 1)[1].strip() if ":" in primera else primera
            casos.append((f"OPT_{n}: {titulo} (cuádruplos)", texto, True))
        return casos

    def _procesar_cuadruplos(self, texto):
        """Un caso de cuádruplos ya es código intermedio: no pasa por léxico, sintáctico,
        semántico ni por el generador; se optimiza directamente."""
        aviso = ("ℹ Este caso está escrito directamente en CUÁDRUPLOS (código intermedio).\n"
                 "No pasa por el análisis léxico, sintáctico ni semántico, ni por el generador:\n"
                 "va directo al optimizador. Revisa la pestaña '🛠 Optimización'.")
        for txt in (self.txt_lexico, self.txt_sintactico, self.txt_semantico, self.txt_polaca,
                    self.txt_codigo_p, self.txt_triplos, self.txt_cuadruplos):
            txt.insert(tk.END, aviso)
        try:
            res = optimizar_texto_cuadruplos(texto, self._pases_seleccionados())
        except Exception as e:
            self.resultado_opt = None
            messagebox.showerror("Error en cuádruplos", f"No se pudo leer los cuádruplos:\n{e}")
            self.lbl_estado.config(text="Estado: Error al leer los cuádruplos ❌")
            return
        self.mostrar_resultado_optimizacion(res)
        self.notebook.select(self.tab_optimizacion)
        self.sub_notebook_opt.select(0)

def ejecutar_interfaz_grafica():
    root = tk.Tk()
    InterfazCompilador(root)
    root.mainloop()


if __name__ == "__main__":
    ejecutar_interfaz_grafica()