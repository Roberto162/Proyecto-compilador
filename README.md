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
├── ejecutar_pruebas.py         # Ejecuta la suite /tests y muestra la matriz de métricas
├── interfaz/
│   └── gui.py                  # GUI con la pestaña "🛠 Optimización"
├── modulos/
│   ├── lexico.py  sintactico.py  semantico.py  codigo_intermedio.py
│   └── optimizacion/
│       ├── __init__.py         # API pública del módulo
│       ├── cuadruplo.py        # Clase Cuadruplo (IR formal) + lector de archivos .cuad
│       ├── generador_ir.py     # AST -> cuádruplos con etiquetas y saltos (si/sino/mientras)
│       ├── bloques.py          # FASE 1: líderes, bloques básicos, CFG, dominadores, ciclos
│       ├── pases_locales.py    # FASE 2 · Nivel 1: plegado, simplificación algebraica, CSE
│       ├── pases_globales.py   # FASE 2 · Nivel 2: propagación, código muerto, LICM
│       ├── mirilla.py          # FASE 2 · Nivel 3: saltos y cargas/almacenamientos redundantes
│       ├── validador.py        # FASE 3: intérprete y verificación de equivalencia
│       ├── optimizador.py      # Pipeline de pases + cálculo de métricas
│       ├── reporte.py          # Formato de tablas, comparación, traza y métricas
│       ├── contexto.py         # Bitácora compartida entre pases
│       └── suite.py            # Ejecución de la carpeta /tests
└── tests/
    ├── caso1_plegado_algebraica.cuad   # expresiones aritméticas intensivas
    ├── caso2_cse.cuad                  # subexpresiones comunes
    ├── caso3_propagacion_dce.cuad      # condicional con código muerto
    ├── caso4_licm.cuad                 # ciclo con código invariante
    ├── caso5_anidado.cuad              # ciclos anidados + condicional
    ├── fuente1_aritmetica.txt          # mismas categorías escritas en el lenguaje fuente
    ├── fuente2_condicional_muerto.txt
    ├── fuente3_ciclo_invariante.txt
    └── fuente4_anidado.txt
```

## Ejecución

```bash
python main.py                 # menú principal (CLI o GUI)
python ejecutar_pruebas.py     # matriz de métricas de toda la suite /tests
python ejecutar_pruebas.py -v  # + reporte completo (traza paso a paso) de cada prueba
python ejecutar_pruebas.py tests/caso4_licm.cuad   # reporte completo de un solo archivo
```

### Desde la terminal (CLI)

`main.py → 1. Modo Terminal`:

| Opción | Qué hace |
|---|---|
| 1 / 2 / 3 | Analiza código fuente (pruebas, archivo .txt o manual). En el **menú de resultados**, la opción **5. Optimización de Código Intermedio** abre el submenú del optimizador. |
| 4. Optimizar archivo de cuádruplos (.cuad) | Optimiza directamente un archivo de cuádruplos (p. ej. los casos de `/tests`). |
| 5. Ejecutar suite de pruebas | Matriz comparativa de métricas de todos los archivos de `/tests`; se puede abrir el detalle de cualquier fila. |

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
- **📄 Optimizar archivo .cuad**, **🧪 Suite /tests** y **💾 Exportar reporte**.
- Sub-pestañas: *Original vs Optimizado* (coloreado: rojo = eliminada, amarillo = modificada,
  azul = movida por LICM), *Transformaciones*, *Bloques Básicos / CFG*, *Traza de Pases*,
  *Métricas y Validación* y *Suite de Pruebas*.

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
| 1 · Local | Subexpresiones comunes (tabla de expresiones disponibles) | `t3 = a + b` → `t3 = t1` |
| 2 · Global | Propagación de constantes (flujo de datos sobre el CFG) | `debug = 10 … debug == 0` → `10 == 0` |
| 2 · Global | Propagación de copias (hacia temporales) | `t3 = x; t6 = t3 + t4` → `t6 = x + t4` |
| 2 · Global | Código inalcanzable y código muerto (análisis de vida) | elimina ramas que nunca se ejecutan y asignaciones que no se leen |
| 2 · Ciclos | Movimiento de código invariante (LICM) | `t2 = ancho * escala` sale del ciclo al pre-header |
| 3 · Mirilla | Saltos y cargas/almacenamientos redundantes | salto a salto, salto a la siguiente, etiquetas sin uso, `a=b; b=a` |

Los pases se ejecutan en rondas hasta que ninguno cambia el código (punto fijo, máximo
`OPT_MAX_RONDAS` en `config.py`).

## Validación semántica

El validador ejecuta el código **original** y el **optimizado** en un intérprete de cuádruplos y
compara variables de salida, lo impreso y los errores. Las variables de entrada (leídas antes de
asignarse, como `x` o `limite`) se detectan automáticamente y se prueban con 5 juegos de valores
aleatorios con semilla fija (reproducible). También mide las **instrucciones ejecutadas**, lo que
evidencia el ahorro de LICM aunque el número estático de instrucciones no cambie.

## Ejemplo de salida (`python ejecutar_pruebas.py`)

```
ARCHIVO                            ANTES DESP.   RED.%  TEMP-  DIN.ANT DIN.DESP  ESPER.   VALID.
------------------------------------------------------------------------------------------------
caso1_plegado_algebraica.cuad          8     2   75.0%      6      8.0      2.0       ✅        ✅
caso2_cse.cuad                         9     7   22.2%      2      9.0      7.0       ✅        ✅
caso3_propagacion_dce.cuad            11     2   81.8%      2      7.0      2.0       ✅        ✅
caso4_licm.cuad                       11    11    0.0%      0    116.6    103.4       ✅        ✅
caso5_anidado.cuad                    31    26   16.1%      1   2884.2   1619.0       —        ✅
...
```

## Limitaciones conocidas

- La propagación de copias sólo reemplaza **temporales** (`t1 = x`), para conservar los nombres de
  las variables del programa (igual que en las salidas esperadas de los casos de prueba).
- LICM no mueve divisiones que podrían ser entre cero si el ciclo no se ejecuta, ni instrucciones
  cuyo resultado se use después del ciclo cuando su bloque no domina todas las salidas.
- Los temporales se reconocen por el prefijo `t` + número (`PREFIJO_TEMPORALES`); una variable del
  usuario llamada `t1` se trataría como temporal.
- En el lenguaje fuente, todas las variables se inicializan con constantes, por lo que la
  propagación de constantes suele resolver todo el programa; los archivos `.cuad` con variables
  de entrada muestran mejor cada pase por separado.
