# Compilador — Motor de Optimización de Código Intermedio

Módulo de optimización **independiente de la máquina** que recibe el código intermedio
(cuádruplos) generado por las fases previas del compilador, lo divide en bloques básicos,
aplica pases de optimización locales, globales, de ciclos y de mirilla, y valida que el
programa optimizado produce **los mismos resultados** que el original.

```
[ Léxico ] -> [ Sintáctico (AST) ] -> [ Semántico ] -> [ Generador IR ] -> [ Cuádruplos originales ]
                                                                                   │
                                                                                   ▼
                                                     ┌──────────────────────────────────────────┐
                                                     │ OPTIMIZADOR                              │
                                                     │ 1. Líderes, bloques básicos y CFG        │
                                                     │ 2. Pases (se repiten hasta punto fijo)   │
                                                     │ 3. Reensamblado                          │
                                                     └──────────────────────────────────────────┘
                                                                                   │
                                                                                   ▼
                                        [ Cuádruplos optimizados ] -> [ Validador + Métricas ]
```

## Requisitos

- Python **3.8 o superior** (sin librerías externas).
- `tkinter` para la interfaz gráfica (ya viene con Python en Windows y macOS; en Linux: `sudo apt install python3-tk`).

## Estructura

```
proyecto/
├── main.py                     # Menú CLI / GUI (incluye los submenús de optimización)
├── config.py                   # Configuración global (+ parámetros del optimizador)
├── css.py                      # Estilos de la GUI
├── interfaz/
│   └── gui.py                  # GUI con la pestaña "🛠 Optimización"
├── modulos/
│   ├── lexico.py  sintactico.py  semantico.py  codigo_intermedio.py
│   └── optimizacion/
│       ├── __init__.py         # API pública del módulo
│       ├── cuadruplo.py        # Clase Cuadruplo (IR formal), conversión desde el generador y lector .cuad
│       ├── bloques.py          # FASE 1: líderes, bloques básicos, CFG, dominadores, ciclos
│       ├── pases_locales.py    # FASE 2 · Nivel 1: plegado, simplificación algebraica, CSE
│       ├── pases_globales.py   # FASE 2 · Nivel 2: propagación, código muerto, LICM
│       ├── mirilla.py          # FASE 2 · Nivel 3: saltos y cargas/almacenamientos redundantes
│       ├── validador.py        # FASE 3: intérprete y verificación de equivalencia
│       ├── optimizador.py      # Pipeline de pases + cálculo de métricas
│       ├── reporte.py          # Formato de tablas, comparación, traza y métricas
│       └── contexto.py         # Bitácora compartida entre pases
└── tests/
    ├── caso1_plegado_algebraica.cuad   # expresiones aritméticas intensivas
    ├── caso2_cse.cuad                  # subexpresiones comunes
    ├── caso3_propagacion_dce.cuad      # condicional con código muerto
    ├── caso4_licm.cuad                 # ciclo con código invariante
    ├── caso5_anidado.cuad              # ciclos anidados + condicional
    ├── caso6_ejercicios_clase.cuad     # ejercicios 1-3 de C3D de la presentación (aritmética)
    ├── estres_condicionales.txt        # prueba de estrés de si / sino anidados
    ├── fuente1_aritmetica.txt          # mismas categorías escritas en el lenguaje fuente
    ├── fuente2_condicional_muerto.txt
    ├── fuente3_ciclo_invariante.txt
    └── fuente4_anidado.txt
```

## Generador de código intermedio

Las cuatro representaciones (Notación Polaca, Código P, Triplos y Cuádruplos) se obtienen del
mismo AST. Están pensadas para expresiones algebraicas; los `si` / `sino` / `mientras` se
traducen a etiquetas y saltos. El optimizador toma como entrada los **cuádruplos** de este generador.

## Ejecución

```bash
python main.py                 # menú principal (CLI o GUI)
```

### Desde la terminal (CLI)

`main.py → 1. Modo Terminal`:

| Opción | Qué hace |
|---|---|
| 1 / 2 / 3 | Analiza código fuente (pruebas, archivo .txt o manual). En el **menú de resultados**, la opción **5. Optimización de Código Intermedio** abre el submenú del optimizador. |
| 4. Optimizar un caso de prueba de cuádruplos (.cuad) | Optimiza directamente un archivo de cuádruplos (p. ej. los casos de `/tests`). |

Submenú de optimización:

```
1. Ver código intermedio original (cuádruplos)
2. Fase 1: Líderes, bloques básicos y CFG
3. Fase 2: Traza de pases de optimización (paso a paso)
4. Ver código intermedio optimizado          (con la columna "Transformación aplicada")
5. Comparación original vs optimizado         (qué le pasó a cada instrucción + vista lado a lado)
6. Fase 3: Métricas y validación semántica
7. Reporte completo
8. Configurar pases activos y re-optimizar   (activar/desactivar pases para ver su efecto)
9. Exportar reporte (.txt) y CFG (.dot de Graphviz)
10. Volver
```

### Desde la GUI

Al presionar **🚀 Analizar y Generar Código** se optimiza automáticamente y se llena la pestaña
**🛠 Optimización**, que contiene:

- Casillas para activar/desactivar cada pase y botón **🔁 Re-optimizar**.
- **Casos:** lista de los casos `.cuad` de `/tests` (al elegir uno se optimiza), **📄 Abrir otro .cuad** y **💾 Exportar reporte**.
- **⚙ Pases:** muestra los pases agrupados por tipo (locales, globales, ciclos, mirilla) con lo que hace cada uno.
- Sub-pestañas: *Original vs Optimizado* (coloreado: rojo = eliminada, amarillo = modificada,
  azul = movida por LICM), *Transformaciones*, *Bloques Básicos / CFG*, *Traza de Pases*,
  *Métricas y Validación*.

## Formato de los archivos de prueba

### Cuádruplos (`.cuad`)

Una instrucción por línea: `operador arg1 arg2 resultado` (separados por espacios, tabs o comas;
`_` = campo vacío).

```
# Caso 1: Plegado de constantes          <- la primera línea de comentario es el título
@salida res                              <- variables vivas al final del programa
@entrada x=3, y=4                        <- (opcional) valores fijos para el validador

*   4    10   t1
+   t1   2    t2
=   t7   _    res
label _  _    L1          (también: label L1)
ifFalse t2 _  L1          (también: ifFalse t2 L1)
goto  _  _    L2          (también: goto L2)
print x  _    _

@esperado                                <- (opcional) salida esperada, se compara automáticamente
+   x    y    t6
=   t6   _    res
```

Operadores: `+ - * /  == != < > <= >=  =  label  goto  ifFalse  ifTrue  print  reverse`.

### Lenguaje fuente (`.txt`)

Código normal del lenguaje. La directiva opcional `# salida: a, b` (es un comentario, el léxico
la ignora) indica qué variables son el resultado del programa; sin ella se conservan todas.

```
# salida: costo
complete debug = 0
complete base = 7
complete factor = 5
complete costo = 0
si debug == 1:
    costo = base * 100
sino:
    costo = base * factor * 2
```

## Pases implementados

| Nivel | Pase | Ejemplo |
|---|---|---|
| 1 · Local | Plegado de constantes | `t1 = 4 * 10` → `t1 = 40`; `ifFalse 0 goto L1` → `goto L1` |
| 1 · Local | Simplificación algebraica / reducción de fuerza | `x*1→x`, `x+0→x`, `x*0→0`, `x-x→0`, `x*2→x+x` |
| 1 · Local | Subexpresiones comunes aritméticas (tabla de expresiones disponibles ≈ DAG) | `t3 = a + b` → `t3 = t1` |
| 2 · Global | Propagación de constantes (flujo de datos sobre el CFG) | `debug = 10 … debug == 0` → `10 == 0` |
| 2 · Global | Propagación de copias (hacia temporales) | `t3 = x; t6 = t3 + t4` → `t6 = x + t4` |
| 2 · Global | Código inalcanzable y código muerto (análisis de vida) | elimina ramas que nunca se ejecutan y asignaciones que no se leen |
| 2 · Ciclos | Movimiento de código invariante (LICM, sólo aritmética y copias) | `t2 = ancho * escala` sale del ciclo al pre-header |
| 3 · Mirilla | Saltos y cargas/almacenamientos redundantes | salto a salto, salto a la siguiente, etiquetas sin uso, `a=b; b=a` |

**Alcance:** las transformaciones se centran en las operaciones aritméticas (`+ - * /`) y las
asignaciones. Lo único no aritmético que se evalúa es una comparación entre dos constantes que
controla un salto (y la rama que por ello nunca se ejecuta), porque lo exige el Caso 3 del proyecto.
Comparaciones con variables, `print` y `reverse` se conservan tal cual.

Los pases se ejecutan en rondas hasta que ninguno cambia el código (punto fijo, máximo
`OPT_MAX_RONDAS` en `config.py`).

## Validación semántica

El validador ejecuta el código **original** y el **optimizado** en un intérprete de cuádruplos y
compara variables de salida, lo impreso y los errores. Las variables de entrada (leídas antes de
asignarse, como `x` o `limite`) se detectan automáticamente y se prueban con 5 juegos de valores
aleatorios con semilla fija (reproducible). También mide las **instrucciones ejecutadas**, lo que
evidencia el ahorro de LICM aunque el número estático de instrucciones no cambie.

## Limitaciones conocidas

- La propagación de copias sólo reemplaza **temporales** (`t1 = x`), para conservar los nombres de
  las variables del programa (igual que en las salidas esperadas de los casos de prueba).
- LICM no mueve divisiones que podrían ser entre cero si el ciclo no se ejecuta, ni instrucciones
  cuyo resultado se use después del ciclo cuando su bloque no domina todas las salidas.
- La división `/` siempre produce decimal (regla del semántico), por eso `112 / 4` se pliega a `28.0`.
- Los temporales se reconocen por el prefijo `t` + número (`PREFIJO_TEMPORALES`); una variable del
  usuario llamada `t1` se trataría como temporal.
- En el lenguaje fuente, todas las variables se inicializan con constantes, por lo que la
  propagación de constantes suele resolver todo el programa; los archivos `.cuad` con variables
  de entrada muestran mejor cada pase por separado.