"""
interfaz/gui.py
===============
Interfaz gráfica con sub-pestañas selectoras para Código Intermedio.
"""

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from css import aplicar_estilo_oscuro, TEXT_AREA_ARGS

from config import EXPRESIONES_PRUEBA_OBLIGATORIAS
from modulos.lexico import obtener_tabla_tokens_str, analizar_codigo
from modulos.sintactico import preparar_tokens, AnalizadorSintactico
from modulos.semantico import ejecutar_pipeline_completo
from modulos.codigo_intermedio import (
    obtener_polaca_str,
    obtener_codigo_p_str,
    obtener_triplos_str,
    obtener_cuadruplos_str
)

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
        
        # Área principal de texto con barra de desplazamiento
        self.txt = scrolledtext.ScrolledText(
            self, 
            height=height, 
            font=("Consolas", 11), 
            bg="#252526", 
            fg="#d4d4d4", 
            insertbackground="white",
            bd=0, 
            highlightthickness=0,
            *args, **kwargs
        )
        self.txt.pack(side="right", fill="both", expand=True)
        
        # Eventos para actualizar la numeración en tiempo real
        self.txt.bind("<KeyRelease>", self.actualizar_lineas)
        self.txt.bind("<MouseWheel>", self.actualizar_lineas)
        self.txt.bind("<Button-1>", self.actualizar_lineas)
        self.txt.bind("<Configure>", self.actualizar_lineas)
        
        self.actualizar_lineas()

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

    # Métodos proxy para mantener 100% la compatibilidad con tu gui.py actual
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
    
class InterfazCompilador:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilador & Generador de Código Intermedio")
        self.root.geometry("1020x760")
        self.root.minsize(850, 620)

        # Se aplica el estilo oscuro y se inicializan todos los componentes
        aplicar_estilo_oscuro(self.root)
        self._crear_componentes()
        
    def _crear_componentes(self):
        # Frame superior
        frame_top = ttk.LabelFrame(self.root, text=" Código Fuente de Entrada ", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)

        self.txt_entrada = EditorCodigo(frame_top, height=6)
        self.txt_entrada.pack(fill="both", expand=True, pady=(0, 5))

        frame_btn = ttk.Frame(frame_top)
        frame_btn.pack(fill="x")

        ttk.Button(frame_btn, text="📁 Cargar Archivo (.txt)", command=self.cargar_archivo).pack(side="left", padx=2)
        ttk.Button(frame_btn, text="🚀 Analizar y Generar Código", command=self.procesar_codigo).pack(side="left", padx=2)
        # 1. Cambio: Estilo oscuro para el botón de limpiar
        ttk.Button(frame_btn, text="🧹 Limpiar", style="Secundario.TButton", command=self.limpiar_campos).pack(side="left", padx=2)

        lbl_pruebas = ttk.Label(frame_btn, text=" Casos de Prueba:")
        lbl_pruebas.pack(side="left", padx=(15, 2))

        self.cb_pruebas = ttk.Combobox(frame_btn, state="readonly", width=38)
        self.cb_pruebas['values'] = [f"{p['id']}: {p['descripcion']}" for p in EXPRESIONES_PRUEBA_OBLIGATORIAS]
        self.cb_pruebas.pack(side="left", padx=2)
        self.cb_pruebas.bind("<<ComboboxSelected>>", self.cargar_prueba_seleccionada)

        # Notebook Principal
        frame_bottom = ttk.LabelFrame(self.root, text=" Resultados del Análisis y Generación ", padding=10)
        frame_bottom.pack(fill="both", expand=True, padx=10, pady=5)

        self.notebook = ttk.Notebook(frame_bottom)
        self.notebook.pack(fill="both", expand=True)

        # 2. Cambios: Reemplazo de los colores claros por **TEXT_AREA_ARGS en cada pestaña

        # Tab 1: Léxico
        self.tab_lexico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_lexico, text=" 🔤 Análisis Léxico ")
        self.txt_lexico = scrolledtext.ScrolledText(self.tab_lexico, **TEXT_AREA_ARGS)
        self.txt_lexico.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 2: Sintáctico
        self.tab_sintactico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sintactico, text=" 🌲 Análisis Sintáctico ")
        self.txt_sintactico = scrolledtext.ScrolledText(self.tab_sintactico, **TEXT_AREA_ARGS)
        self.txt_sintactico.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 3: Semántico
        self.tab_semantico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_semantico, text=" 📊 Tabla de Símbolos & Semántica ")
        self.txt_semantico = scrolledtext.ScrolledText(self.tab_semantico, **TEXT_AREA_ARGS)
        self.txt_semantico.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 4: Código Intermedio con Sub-Notebook
        self.tab_codigo_intermedio = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_codigo_intermedio, text=" ⚡ Código Intermedio ")

        self.sub_notebook = ttk.Notebook(self.tab_codigo_intermedio)
        self.sub_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Sub-tab: Polaca
        self.sub_tab_polaca = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.sub_tab_polaca, text=" Notación Polaca ")
        self.txt_polaca = scrolledtext.ScrolledText(self.sub_tab_polaca, **TEXT_AREA_ARGS)
        self.txt_polaca.pack(fill="both", expand=True, padx=5, pady=5)

        # Sub-tab: Código P
        self.sub_tab_p = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.sub_tab_p, text=" Código P (Pila) ")
        self.txt_codigo_p = scrolledtext.ScrolledText(self.sub_tab_p, **TEXT_AREA_ARGS)
        self.txt_codigo_p.pack(fill="both", expand=True, padx=5, pady=5)

        # Sub-tab: Triplos
        self.sub_tab_triplos = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.sub_tab_triplos, text=" Triplos ")
        self.txt_triplos = scrolledtext.ScrolledText(self.sub_tab_triplos, **TEXT_AREA_ARGS)
        self.txt_triplos.pack(fill="both", expand=True, padx=5, pady=5)

        # Sub-tab: Cuádruplos
        self.sub_tab_cuadruplos = ttk.Frame(self.sub_notebook)
        self.sub_notebook.add(self.sub_tab_cuadruplos, text=" Cuádruplos ")
        self.txt_cuadruplos = scrolledtext.ScrolledText(self.sub_tab_cuadruplos, **TEXT_AREA_ARGS)
        self.txt_cuadruplos.pack(fill="both", expand=True, padx=5, pady=5)

        self.lbl_estado = ttk.Label(self.root, text="Estado: Listo.", relief="sunken", anchor="w")
        self.lbl_estado.pack(side="bottom", fill="x")

    def cargar_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de código fuente",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    self.txt_entrada.delete("1.0", tk.END)
                    self.txt_entrada.insert(tk.END, contenido)
                    self.lbl_estado.config(text=f"Estado: Archivo '{ruta}' cargado con éxito.")
            except Exception as e:
                messagebox.showerror("Error de Lectura", f"No se pudo leer el archivo:\n{e}")

    def cargar_prueba_seleccionada(self, event):
        idx = self.cb_pruebas.current()
        if idx >= 0:
            prueba = EXPRESIONES_PRUEBA_OBLIGATORIAS[idx]
            self.txt_entrada.delete("1.0", tk.END)
            self.txt_entrada.insert(tk.END, prueba['expresion'])
            self.lbl_estado.config(text=f"Estado: Cargada {prueba['id']} - {prueba['descripcion']}")

    def limpiar_campos(self):
        self.txt_entrada.delete("1.0", tk.END)
        self.txt_lexico.delete("1.0", tk.END)
        self.txt_sintactico.delete("1.0", tk.END)
        self.txt_semantico.delete("1.0", tk.END)
        self.txt_polaca.delete("1.0", tk.END)
        self.txt_codigo_p.delete("1.0", tk.END)
        self.txt_triplos.delete("1.0", tk.END)
        self.txt_cuadruplos.delete("1.0", tk.END)
        self.lbl_estado.config(text="Estado: Campos limpiados.")

    def procesar_codigo(self):
        codigo = self.txt_entrada.get("1.0", tk.END).strip()
        if not codigo:
            messagebox.showwarning("Atención", "El cuadro de código fuente está vacío.")
            return

        self.limpiar_campos()
        self.txt_entrada.insert(tk.END, codigo)

        # 1. Léxico
        tokens_lex, err_lex = analizar_codigo(codigo)
        if err_lex:
            self.txt_lexico.insert(tk.END, "❌ ERRORES LÉXICOS DETECTADOS:\n" + "-" * 50 + "\n")
            for e in err_lex:
                self.txt_lexico.insert(tk.END, f"-> {e}\n")
        else:
            self.txt_lexico.insert(tk.END, obtener_tabla_tokens_str(tokens_lex))

        # 2. Sintáctico
        tokens_sint = preparar_tokens(tokens_lex)
        parser = AnalizadorSintactico(tokens_sint)
        valido_sint, ast_raiz = parser.analizar()

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

        # 3. Semántico
        valido, _, _, rep_sem, tabla_rep, _ = ejecutar_pipeline_completo(codigo)
        self.txt_semantico.insert(tk.END, f"{tabla_rep}\n\n{rep_sem}")

        # 4. Generación de Código Intermedio por Selección
        if valido and ast_raiz:
            self.txt_polaca.insert(tk.END, obtener_polaca_str(ast_raiz))
            self.txt_codigo_p.insert(tk.END, obtener_codigo_p_str(ast_raiz))
            self.txt_triplos.insert(tk.END, obtener_triplos_str(ast_raiz))
            self.txt_cuadruplos.insert(tk.END, obtener_cuadruplos_str(ast_raiz))

            self.notebook.select(self.tab_codigo_intermedio)
            self.lbl_estado.config(text="Estado: Código Intermedio Generado Exitosamente ✅")
        else:
            msg = "🚫 GENERACIÓN ABORTADA:\nNo se genera Código Intermedio si la expresión contiene errores."
            self.txt_polaca.insert(tk.END, msg)
            self.txt_codigo_p.insert(tk.END, msg)
            self.txt_triplos.insert(tk.END, msg)
            self.txt_cuadruplos.insert(tk.END, msg)
            self.lbl_estado.config(text="Estado: Proceso completado con observaciones.")


def ejecutar_interfaz_grafica():
    root = tk.Tk()
    app = InterfazCompilador(root)
    root.mainloop()


if __name__ == "__main__":
    ejecutar_interfaz_grafica()