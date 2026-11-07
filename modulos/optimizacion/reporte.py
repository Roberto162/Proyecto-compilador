"""
modulos/optimizacion/reporte.py
===============================
Funciones de formato (texto) para CLI y GUI: tablas de cuádruplos,
comparación original vs. optimizado, traza de pases, métricas y validación.
"""

from modulos.optimizacion.bloques import formatear_bloques
from modulos.optimizacion.cuadruplo import tuplas
from modulos.optimizacion.optimizador import NIVELES, DESCRIPCION_PASES

SEP = "=" * 92


def tabla_cuadruplos(codigo, titulo="CUÁDRUPLOS", con_notas=False):
    lineas = [f"--- {titulo} ({len(codigo)} instrucciones) ---", ""]
    enc = f"{'#':>3}  {'OPERADOR':<9}{'ARG 1':<12}{'ARG 2':<12}{'RESULTADO':<12}{'TAC':<24}"
    if con_notas:
        enc += "TRANSFORMACIÓN APLICADA"
    lineas += [enc, "-" * (len(enc) + (20 if con_notas else 0))]
    if not codigo:
        lineas.append("  (sin instrucciones)")
    for i, q in enumerate(codigo, 1):
        op, a1, a2, r = q.campos_visibles()
        fila = f"{i:>3}  {op:<9}{a1:<12}{a2:<12}{r:<12}{q.tac():<24}"
        if con_notas:
            fila += "; ".join(q.notas) if q.notas else "—"
        lineas.append(fila)
    return "\n".join(lineas)


def estado_instrucciones(res):
    """
    Para cada instrucción del código original indica qué le ocurrió.
    Devuelve lista de (num, tac_original, estado, detalle) con estado en
    {'igual', 'modificada', 'movida', 'eliminada'}.
    """
    por_origen = {q.origen: q for q in res.optimizado if q.origen is not None}
    filas = []
    for q in res.original:
        if q.origen in por_origen:
            q2 = por_origen[q.origen]
            if any(n.startswith("LICM") for n in q2.notas):
                estado = "movida"
            elif q2.tupla() != q.tupla():
                estado = "modificada"
            else:
                estado = "igual"
            filas.append((q.origen, q.tac(), estado, q2.tac() if estado != "igual" else "",
                          "; ".join(q2.notas)))
        else:
            pase, motivo, _ = res.eliminadas.get(q.origen, ("", "eliminada", None))
            filas.append((q.origen, q.tac(), "eliminada", "", f"{motivo} [{pase}]" if pase else motivo))
    return filas


ICONOS = {"igual": "  =", "modificada": "  ✎", "movida": "  ↑", "eliminada": "  ✘"}


def comparacion(res):
    lineas = [f"--- COMPARACIÓN: ORIGINAL vs OPTIMIZADO — {res.titulo} ---", ""]
    lineas.append(f"{'#':>3} {'':3} {'ORIGINAL':<26} {'RESULTADO':<26} DETALLE")
    lineas.append("-" * 92)
    for num, tac, estado, nuevo, detalle in estado_instrucciones(res):
        destino = {"igual": "(sin cambio)", "eliminada": "(eliminada)"}.get(estado, nuevo)
        lineas.append(f"{num:>3} {ICONOS[estado]} {tac:<26} {destino:<26} {detalle}")
    lineas.append("")
    lineas.append("Leyenda:  = sin cambio   ✎ modificada   ↑ movida (LICM)   ✘ eliminada")
    lineas.append("")
    lineas.append(lado_a_lado(res))
    return "\n".join(lineas)


def lado_a_lado(res, ancho=40):
    izq = [f"({i}) {q.tac()}" for i, q in enumerate(res.original, 1)]
    der = [f"({i}) {q.tac()}" for i, q in enumerate(res.optimizado, 1)]
    lineas = [f"{'ORIGINAL (' + str(len(izq)) + ')':<{ancho}} │ OPTIMIZADO ({len(der)})",
              "─" * ancho + "─┼─" + "─" * ancho]
    for k in range(max(len(izq), len(der))):
        a = izq[k] if k < len(izq) else ""
        b = der[k] if k < len(der) else ""
        lineas.append(f"{a:<{ancho}} │ {b}")
    return "\n".join(lineas)


def traza(res):
    lineas = [f"--- TRAZA DE PASES DE OPTIMIZACIÓN — {res.titulo} ---", ""]
    lineas.append(f"Variables de salida (vivas al final): {', '.join(sorted(res.salidas)) or '—'}")
    lineas.append(f"Pases activos: {', '.join(res.pases_activos)}")
    lineas.append(f"Rondas hasta punto fijo: {res.rondas}")
    lineas.append("")
    if not res.traza:
        lineas.append("Ningún pase modificó el código (ya estaba optimizado).")
    for k, p in enumerate(res.traza, 1):
        lineas.append(SEP)
        lineas.append(f"Paso {k} · Ronda {p.ronda} · [{p.nivel}] {p.nombre}   "
                      f"({len(p.antes)} -> {len(p.despues)} instrucciones)")
        lineas.append(SEP)
        lineas.append(f"   Tipo de pase : {NIVELES.get(p.nivel, '')}")
        lineas.append(f"   Qué hace     : {DESCRIPCION_PASES.get(p.clave, '')}")
        lineas.append("   Cambios:")
        for m in p.mensajes:
            lineas.append(f"   • {m}")
        lineas.append("   Código resultante:")
        for i, q in enumerate(p.despues, 1):
            lineas.append(f"      ({i:>2}) {q.tac()}")
        lineas.append("")
    return "\n".join(lineas)


def metricas(res):
    m = res.metricas
    def fila(nombre, a, b, extra=""):
        return f"  {nombre:<38}{str(a):>10}{str(b):>12}   {extra}"
    lineas = [f"--- MÉTRICAS DE OPTIMIZACIÓN — {res.titulo} ---", ""]
    lineas.append(f"  {'MÉTRICA':<38}{'ANTES':>10}{'DESPUÉS':>12}")
    lineas.append("  " + "-" * 64)
    lineas.append(fila("Total de instrucciones (cuádruplos)", m["instr_antes"], m["instr_despues"],
                       f"reducción {m['reduccion_pct']:.1f}%"))
    lineas.append(fila("Variables temporales", m["temporales_antes"], m["temporales_despues"],
                       f"eliminados {m['temporales_antes'] - m['temporales_despues']}"))
    lineas.append(fila("Operaciones (aritm. + relacionales)", m["ops_antes"], m["ops_despues"]))
    lineas.append(fila("Operaciones aritméticas", m["arit_antes"], m["arit_despues"]))
    lineas.append(fila("Saltos (goto / ifFalse)", m["saltos_antes"], m["saltos_despues"]))
    lineas.append(fila("Etiquetas", m["etiquetas_antes"], m["etiquetas_despues"]))
    lineas.append(fila("Bloques básicos", m["bloques_antes"], m["bloques_despues"]))
    if "dinamicas_antes" in m:
        lineas.append(fila("Instrucciones EJECUTADAS (promedio)", f"{m['dinamicas_antes']:.1f}",
                           f"{m['dinamicas_despues']:.1f}", f"reducción {m['reduccion_dinamica_pct']:.1f}%"))
        lineas.append(fila("Op. aritméticas EJECUTADAS (prom.)", f"{m['dinamicas_arit_antes']:.1f}",
                           f"{m['dinamicas_arit_despues']:.1f}"))
    lineas.append("")
    lineas.append(f"  Temporales eliminados : {', '.join(m['temporales_eliminados']) or '—'}")
    lineas.append(f"  Variables eliminadas  : {', '.join(m['variables_eliminadas']) or '—'}")
    if res.coincide_esperado is not None:
        lineas.append(f"  Coincide con la salida esperada del caso: "
                      f"{'SÍ ✅' if res.coincide_esperado else 'NO ❌'}")
    lineas.append("")
    lineas.append(validacion(res))
    return "\n".join(lineas)


def validacion(res):
    v = res.validacion
    if v is None:
        return ""
    lineas = ["--- VALIDACIÓN SEMÁNTICA (ejecución original vs optimizado) ---", ""]
    lineas.append(f"  Resultado: {'EQUIVALENTE ✅' if v.equivalente else 'NO EQUIVALENTE ❌'}")
    lineas.append(f"  Variables comparadas: {', '.join(v.variables_comparadas) or '—'}")
    lineas.append(f"  Variables de entrada: {', '.join(v.entradas) or '(ninguna)'}  "
                  f"-> {len(v.corridas)} corrida(s)")
    for k, c in enumerate(v.corridas, 1):
        ent = ", ".join(f"{a}={b}" for a, b in c["entradas"].items()) or "sin entradas"
        estado = "✔" if not c["diferencias"] else "✘ " + " | ".join(c["diferencias"])
        lineas.append(f"   Corrida {k}: [{ent}]  pasos {c['pasos'][0]} -> {c['pasos'][1]}  {estado}")
        vals = ", ".join(f"{a}={b}" for a, b in c["optimizado"].items())
        lineas.append(f"      salidas: {vals}")
        if c["impresiones"][0]:
            lineas.append(f"      print: {c['impresiones'][0]}")
        if c["errores"][0]:
            lineas.append(f"      error (ambos): {c['errores'][0]}")
    for o in v.observaciones:
        lineas.append(f"  ⚠ {o}")
    return "\n".join(lineas)


def bloques(res):
    return (formatear_bloques(res.original, "BLOQUES BÁSICOS · CÓDIGO ORIGINAL")
            + "\n\n" + SEP + "\n\n" +
            formatear_bloques(res.optimizado, "BLOQUES BÁSICOS · CÓDIGO OPTIMIZADO"))


def reporte_completo(res):
    partes = [
        tabla_cuadruplos(res.original, f"CÓDIGO INTERMEDIO ORIGINAL — {res.titulo}"),
        bloques(res),
        traza(res),
        tabla_cuadruplos(res.optimizado, "CÓDIGO INTERMEDIO OPTIMIZADO", con_notas=True),
        comparacion(res),
        metricas(res),
    ]
    if res.esperado is not None:
        partes.insert(4, tabla_cuadruplos(res.esperado, "SALIDA ESPERADA DEL CASO"))
    return ("\n\n" + SEP + "\n\n").join(partes)