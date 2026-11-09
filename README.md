# Compilador — Generador y Optimizador de Código Intermedio

Compilador para un lenguaje propio (`complete`, `bubble`, `chain`, `si`, `sino`, `mientras`,
`mostrar`, `reverse`) con análisis léxico, sintáctico y semántico, generación de código intermedio
(Notación Polaca, Código P, Triplos y Cuádruplos) y un **motor de optimización independiente de la
máquina** que divide los cuádruplos en bloques básicos, aplica pases locales, globales, de ciclos y
de mirilla, y comprueba que el programa optimizado produce **los mismos resultados** que el original.

```
[ Léxico ] -> [ Sintáctico (AST) ] -> [ Semántico ] -> [ Generador de código intermedio ]
                                                                    │  (cuádruplos)
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
├── main.py                     # Menú principal: modo terminal (CLI) o interfaz gráfica (GUI)
├── config.py                   # Configuración global, casos de prueba y parámetros del optimizador
├── css.py                      # Estilos (tema oscuro) de la GUI
├── interfaz/
│   └── gui.py                  # Interfaz gráfica, incluida la pestaña "🛠 Optimización"
├── modulos/
│   ├── lexico.py               # Análisis léxico (tokens y errores léxicos)
│   ├── sintactico.py           # Análisis sintáctico LL(1) y construcción del AST
│   ├── semantico.py            # Tabla de símbolos y verificación de tipos
│   ├── codigo_intermedio.py    # Polaca, Código P, Triplos y Cuádruplos a partir del AST
│   └── optimizacion/
│       ├── __init__.py         # Funciones que usan main.py y gui.py
│       ├── cuadruplo.py        # Clase Cuadruplo, conversión desde el generador y lector de .cuad
│       ├── bloques.py          # FASE 1: líderes, bloques básicos, CFG, ciclos y variables vivas
│       ├── pases_locales.py    # FASE 2 · Nivel 1 (locales): plegado, simplificación algebraica, CSE
│       ├── pases_globales.py   # FASE 2 · Nivel 2 (globales y ciclos): propagación, código muerto, LICM
│       ├── mirilla.py          # FASE 2 · Nivel 3 (mirilla): saltos y copias redundantes
│       ├── optimizador.py      # Repite los pases hasta que nada cambie y calcula las métricas
│       ├── validador.py        # FASE 3: ejecuta original y optimizado y compara resultados
│       ├── reporte.py          # Textos y tablas que se muestran en la GUI y la terminal
│       └── contexto.py         # Registro de qué instrucción eliminó cada pase y por qué
└── tests/
    ├── caso1_plegado_algebraica.cuad   # OPT_1: expresiones aritméticas intensivas
    ├── caso2_cse.cuad                  # OPT_2: subexpresiones comunes
    ├── caso3_propagacion_dce.cuad      # OPT_3: condicional con código muerto
    ├── caso4_licm.cuad                 # OPT_4: ciclo con código invariante
    ├── caso5_anidado.cuad              # OPT_5: ciclos anidados + condicional
    ├── caso6_ejercicios_clase.cuad     # OPT_6: ejercicios 1-3 de C3D de la presentación
    ├── estres_condicionales.txt        # programas de ejemplo en el lenguaje fuente
    ├── fuente1_aritmetica.txt          #   (se abren con "Cargar Archivo")
    ├── fuente2_condicional_muerto.txt
    ├── fuente3_ciclo_invariante.txt
    └── fuente4_anidado.txt
```

La carpeta `__pycache__` la crea Python automáticamente; no forma parte del proyecto.

## Casos de prueba

Todos aparecen en la lista **Casos de Prueba** de la GUI y en la opción **1** del modo terminal:

| Casos | Qué son | Qué pasa al elegirlos |
|---|---|---|
| `PRUEBA_1` a `PRUEBA_3` | Expresiones obligatorias del proyecto (precedencia, paréntesis, anidamiento), definidas en `config.py` | Pasan por todo el compilador: léxico, sintáctico, semántico, código intermedio y optimización |
| `ERROR_1` a `ERROR_7` | Entradas inválidas (operador colgado, variable no declarada, paréntesis desbalanceados, operador sin operandos, expresión incompleta, símbolo no admitido, `)` sin apertura) | Se muestra el error en la fase que lo detecta y no se genera código intermedio |
| `OPT_1` a `OPT_6` *(cuádruplos)* | Casos del optimizador: archivos `.cuad` de `/tests`, ya escritos en cuádruplos | Van **directo al optimizador**, porque ya son código intermedio |

## Ejecución

```bash
python main.py
```

### Interfaz gráfica (GUI)

**Parte superior**

- **📁 Cargar Archivo (.txt):** abre un archivo de código fuente (`.txt`). También acepta
  archivos de cuádruplos (`.cuad`), que van directo al optimizador.
- **🚀 Analizar y Generar Código:** procesa lo que está en el editor. Si es código fuente, hace todo
  el proceso; si son cuádruplos, sólo optimiza.
- **🧹 Limpiar:** borra el editor y los resultados.
- **Casos de Prueba:** lista con los casos de la tabla anterior.
- La línea entre el editor y los resultados se puede arrastrar para cambiar sus tamaños.

**Pestañas de resultados**

| Pestaña | Contenido |
|---|---|
| 🔤 Análisis Léxico | Errores léxicos y tabla de tokens |
| 🌲 Análisis Sintáctico | Traza de derivación (matches) y errores sintácticos |
| 📊 Tabla de Símbolos & Semántica | Tabla de símbolos y reporte de errores/advertencias |
| ⚡ Código Intermedio | Sub-pestañas: Notación Polaca, Código P (Pila), Triplos y Cuádruplos |
| 🛠 Optimización | Ver la siguiente sección |

**Pestaña 🛠 Optimización**

- **⚙ Pases (8/8):** muestra u oculta los 8 pases agrupados por tipo (Local, Global, Ciclos,
  Mirilla), con la explicación de cada tipo. Cada casilla activa o desactiva un pase.
- **🔁 Re-optimizar:** vuelve a optimizar el mismo código usando sólo los pases marcados. Sirve
  para ver qué aporta cada pase. Con **0 pases** marcados el código queda igual al original.
- Sub-pestañas:
  - **Original vs Optimizado:** ambos códigos lado a lado en formato de cuádruplo. En el original,
    rojo = eliminada, amarillo = modificada y azul = movida por LICM. Debajo de cada instrucción
    optimizada se indica la transformación que se le aplicó.
  - **Transformaciones:** qué le pasó a cada instrucción original y el código optimizado con la
    columna "Transformación aplicada". En los casos OPT que la tienen, también la salida esperada.
  - **Bloques Básicos / CFG:** líderes, bloques básicos, grafo de flujo de control y ciclos, del
    código original y del optimizado.
  - **Métricas y Validación:** instrucciones antes/después, porcentaje de reducción, temporales y
    variables eliminados, instrucciones ejecutadas y el resultado de la validación (EQUIVALENTE ✅).

### Terminal (CLI)

`main.py → 1. Modo Terminal (CLI)`:

```
1. Casos de prueba (código fuente y casos del optimizador)
2. Cargar archivo (.txt código fuente / .cuad cuádruplos)
3. Ingresar expresión manualmente
4. Volver
```

Al analizar código fuente se muestra un resumen de errores por fase y el **menú de resultados**:

```
1. Ver resultado del Análisis Léxico (Tokens y Errores)
2. Ver resultado del Análisis Sintáctico (Matches y Errores)
3. Ver resultado del Análisis Semántico (Tabla de Símbolos y Reporte)
4. Ver Generación de Código Intermedio (Seleccionar representación)
5. Optimización de Código Intermedio (bloques, pases, métricas)
6. Volver al Menú Principal
```

Submenú de optimización (las mismas vistas que la pestaña de la GUI). Los casos `OPT_n` y los
archivos `.cuad` entran directamente aquí:

```
1. Original vs Optimizado
2. Transformaciones (qué le pasó a cada instrucción)
3. Bloques básicos y CFG
4. Métricas y validación
5. Configurar pases y re-optimizar   (número de pase para activarlo/desactivarlo,
                                      T = todos, N = ninguno, 0 = terminar)
6. Volver
```

## Formato de los archivos

### Cuádruplos (`.cuad`)

Una instrucción por línea: `operador arg1 arg2 resultado` (separados por espacios, tabs o comas;
`_` = campo vacío).

```
# Caso 1: Plegado de constantes          <- la primera línea de comentario es el título (nombre OPT_n)
@salida res                              <- variables que son el resultado del programa
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

Las variables se declaran con `complete` (entero), `bubble` (decimal) o `chain` (cadena). Los bloques
de `si`, `sino` y `mientras` se marcan con **sangría** (4 espacios). La línea opcional
`# salida: a, b` (es un comentario, el léxico la ignora) indica qué variables son el resultado del
programa; sin ella el optimizador conserva todas.

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

## Pases de optimización

| Tipo | Qué significa |
|---|---|
| **Nivel 1 · Local** | Trabaja dentro de un solo bloque básico, sin cruzar etiquetas ni saltos. |
| **Nivel 2 · Global** | Usa el grafo de flujo (CFG) para seguir los valores entre bloques, por todos los caminos posibles. |
| **Nivel 2 · Ciclos** | Detecta los ciclos y saca de ellos los cálculos que dan lo mismo en cada vuelta. |
| **Nivel 3 · Mirilla** | Revisa pocas instrucciones seguidas para quitar saltos, etiquetas y copias redundantes. |

| Tipo | Pase | Ejemplo |
|---|---|---|
| Local | Plegado de constantes | `t1 = 4 * 10` → `t1 = 40`; `ifFalse 0 goto L1` → `goto L1` |
| Local | Simplificación algebraica / reducción de fuerza | `x*1→x`, `x+0→x`, `x*0→0`, `x-x→0`, `x*2→x+x` |
| Local | Eliminación de subexpresiones comunes (CSE) | `t3 = a + b` → `t3 = t1` |
| Global | Propagación de constantes | `debug = 10 … debug == 0` → `10 == 0` |
| Global | Propagación de copias (hacia temporales) | `t3 = x; t6 = t3 + t4` → `t6 = x + t4` |
| Global | Eliminación de código muerto / inalcanzable | elimina ramas que nunca se ejecutan y asignaciones que no se leen |
| Ciclos | Movimiento de código invariante (LICM) | `t2 = ancho * escala` sale del ciclo antes de su etiqueta |
| Mirilla | Saltos y cargas redundantes | salto a la línea siguiente, salto a salto, etiquetas sin uso, `a=b; b=a` |

**Alcance:** las transformaciones se centran en las operaciones aritméticas (`+ - * /`) y las
asignaciones. Lo único no aritmético que se evalúa es una comparación entre dos constantes que
controla un salto (y la rama que por ello nunca se ejecuta), porque lo exige el Caso 3 del proyecto.
Comparaciones con variables, `print` y `reverse` se conservan tal cual.

Los pases se ejecutan en rondas hasta que ninguno cambia el código (máximo `OPT_MAX_RONDAS` en
`config.py`).

## Validación semántica

El validador ejecuta el código **original** y el **optimizado** en un intérprete de cuádruplos y
compara las variables de salida, lo impreso y los errores. Las variables de entrada (leídas antes de
asignarse, como `x` o `limite` en los `.cuad`) se detectan automáticamente y se prueban con
`OPT_PRUEBAS_VALIDACION` (5) juegos de valores aleatorios con semilla fija, así que el resultado es
reproducible. También cuenta las **instrucciones ejecutadas**, lo que muestra el ahorro de LICM
aunque el número de instrucciones escritas no cambie.

## Limitaciones conocidas

- La propagación de copias sólo reemplaza **temporales** (`t1 = x`), para conservar los nombres de
  las variables del programa (igual que en las salidas esperadas de los casos de prueba).
- LICM no mueve divisiones que podrían ser entre cero si el ciclo no se ejecuta, ni instrucciones
  cuyo resultado se use después del ciclo cuando su bloque no domina todas las salidas.
- La división `/` siempre produce decimal (regla del semántico), por eso `112 / 4` se pliega a `28.0`.
- Los temporales se reconocen por el prefijo `t` + número (`PREFIJO_TEMPORALES`); una variable del
  usuario llamada `t1` se trataría como temporal.
- En el lenguaje fuente todas las variables se inicializan con constantes, por lo que la
  propagación de constantes suele resolver casi todo el programa (por ejemplo, `ancho * escala` se
  convierte en `12` en lugar de moverse fuera del ciclo). Los casos `OPT_n` tienen variables de
  entrada y muestran mejor cada pase por separado.