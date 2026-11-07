"""
css.py
======
Módulo de estilos y paleta de colores para la interfaz gráfica.
Estilo Oscuro: Negro, Azul y Blanco.
"""

import tkinter as tk
from tkinter import ttk

# Paleta global de colores
BG_DARK = "#0B0B0E"
FRAME_BG = "#14141A"
BLUE_ACCENT = "#1565C0"
BLUE_HOVER = "#1E88E5"
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#90A4AE"

TEXT_AREA_ARGS = {
    "font": ("Consolas", 10),
    "bg": "#121218",
    "fg": "#E0E0E0",
    "insertbackground": "#00B0FF",
    "selectbackground": "#0D47A1",
    "selectforeground": "#FFFFFF",
    "bd": 0,
    "relief": "flat"
}


def aplicar_estilo_oscuro(root):
    """Configura los estilos globales de Tkinter/ttk para la ventana principal."""
    style = ttk.Style()
    style.theme_use('clam')
    
    root.configure(bg=BG_DARK)
    
    style.configure(".", background=BG_DARK, foreground=TEXT_WHITE, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG_DARK)
    
    # Contenedores (LabelFrames)
    style.configure("TLabelframe", background=FRAME_BG, bordercolor="#1E88E5", relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=FRAME_BG, foreground="#64B5F6", font=("Segoe UI", 10, "bold"))
    
    # Botones Principales
    style.configure(
        "TButton", 
        background=BLUE_ACCENT, 
        foreground=TEXT_WHITE, 
        bordercolor="#1E88E5", 
        borderwidth=1, 
        focusthickness=0, 
        padding=6, 
        font=("Segoe UI", 9, "bold")
    )
    style.map(
        "TButton", 
        background=[("active", BLUE_HOVER), ("disabled", "#2C3E50")], 
        foreground=[("disabled", "#7F8C8D")]
    )
    
    # Botón Secundario
    style.configure(
        "Secundario.TButton", 
        background="#21212B", 
        foreground=TEXT_WHITE, 
        bordercolor="#37474F"
    )
    style.map("Secundario.TButton", background=[("active", "#2E2E3D")])
    
    # Pestañas (Notebook)
    style.configure("TNotebook", background=BG_DARK, borderwidth=0)
    style.configure(
        "TNotebook.Tab", 
        background="#14141A", 
        foreground=TEXT_MUTED, 
        padding=[14, 7], 
        font=("Segoe UI", 9, "bold"),
        borderwidth=0
    )
    style.map(
        "TNotebook.Tab", 
        background=[("selected", "#0D47A1")], 
        foreground=[("selected", TEXT_WHITE)]
    )
    
    # Desplegable (Combobox)
    style.configure(
        "TCombobox", 
        fieldbackground="#181820", 
        background=BLUE_ACCENT, 
        foreground=TEXT_WHITE, 
        arrowcolor=TEXT_WHITE,
        bordercolor="#1E88E5",
        borderwidth=1
    )
    style.map("TCombobox", fieldbackground=[("readonly", "#181820")], foreground=[("readonly", TEXT_WHITE)])
    
    # Etiquetas y marcos que van DENTRO de un LabelFrame (mismo fondo que el contenedor)
    style.configure("Panel.TFrame", background=FRAME_BG)
    style.configure("Panel.TLabel", background=FRAME_BG, foreground=TEXT_WHITE)
    # Etiquetas sobre el fondo general (barra de estado, títulos de paneles)
    style.configure("TLabel", background=BG_DARK, foreground=TEXT_WHITE)

    # Lista desplegable del Combobox (ttk no la estiliza: se configura con option_add)
    root.option_add("*TCombobox*Listbox.background", "#181820")
    root.option_add("*TCombobox*Listbox.foreground", TEXT_WHITE)
    root.option_add("*TCombobox*Listbox.selectBackground", BLUE_ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT_WHITE)

    # Barras de desplazamiento oscuras (las de ScrolledText son nativas y no aceptan tema)
    style.configure("Vertical.TScrollbar", background="#21212B", troughcolor=BG_DARK,
                    bordercolor=BG_DARK, arrowcolor=TEXT_MUTED, gripcount=0)
    style.configure("Horizontal.TScrollbar", background="#21212B", troughcolor=BG_DARK,
                    bordercolor=BG_DARK, arrowcolor=TEXT_MUTED, gripcount=0)
    style.map("Vertical.TScrollbar", background=[("active", BLUE_ACCENT)])
    style.map("Horizontal.TScrollbar", background=[("active", BLUE_ACCENT)])

    # Casillas de selección de pases (pestaña Optimización) y panel dividido
    style.configure("TCheckbutton", background=FRAME_BG, foreground=TEXT_WHITE, font=("Segoe UI", 9))
    style.map("TCheckbutton", background=[("active", FRAME_BG)],
              indicatorcolor=[("selected", BLUE_HOVER), ("!selected", "#181820")])
    style.configure("TPanedwindow", background=BG_DARK)