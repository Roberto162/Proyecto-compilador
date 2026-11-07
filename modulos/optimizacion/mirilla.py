"""
modulos/optimizacion/mirilla.py
===============================
FASE 2 — NIVEL 3: Optimización de mirilla (Peephole).

Se examina una ventana pequeña de instrucciones consecutivas:
  * Saltos a saltos:            goto L1 ... L1: goto L2   ->  goto L2
  * Saltos a la siguiente instrucción:  goto L1 / L1:     ->  (se elimina el goto)
  * Código después de un goto incondicional y antes de la siguiente etiqueta.
  * Etiquetas consecutivas (se fusionan) y etiquetas que nadie referencia.
  * Cargas/almacenamientos redundantes:
        x = x                         ->  (se elimina)
        a = b ; b = a                 ->  a = b
        instrucción idéntica repetida ->  se conserva sólo la primera
"""


def _mapa_etiquetas(codigo):
    return {q.resultado: i for i, q in enumerate(codigo) if q.es_etiqueta()}


def _saltos_a_saltos(codigo, ctx):
    pos = _mapa_etiquetas(codigo)
    cambio = False
    nuevo = []
    for q in codigo:
        if q.es_salto():
            destino, visitados = q.destino, set()
            while destino in pos and destino not in visitados:
                visitados.add(destino)
                j = pos[destino] + 1
                while j < len(codigo) and codigo[j].es_etiqueta():
                    j += 1
                if j < len(codigo) and codigo[j].es_salto_incondicional() and codigo[j].destino != destino:
                    destino = codigo[j].destino
                else:
                    break
            if destino != q.destino:
                ctx.log(f"{q.tac():<24} ->  salto directo a {destino} [salto a salto]")
                q = q.con(nota=f"Mirilla: salto a salto ({q.destino} -> {destino})", resultado=destino)
                cambio = True
        nuevo.append(q)
    return nuevo, cambio


def _saltos_a_siguiente(codigo, ctx):
    nuevo, cambio = [], False
    for i, q in enumerate(codigo):
        if q.es_salto():
            j = i + 1
            etiquetas = set()
            while j < len(codigo) and codigo[j].es_etiqueta():
                etiquetas.add(codigo[j].resultado)
                j += 1
            if q.destino in etiquetas:
                ctx.eliminar(q, "salto a la instrucción siguiente")
                cambio = True
                continue
        nuevo.append(q)
    return nuevo, cambio


def _codigo_tras_goto(codigo, ctx):
    nuevo, cambio, muerto = [], False, False
    for q in codigo:
        if q.es_etiqueta():
            muerto = False
        if muerto:
            ctx.eliminar(q, "inalcanzable tras goto")
            cambio = True
            continue
        nuevo.append(q)
        if q.es_salto_incondicional():
            muerto = True
    return nuevo, cambio


def _fusionar_etiquetas(codigo, ctx):
    renombrar = {}
    nuevo = []
    for q in codigo:
        if q.es_etiqueta() and nuevo and nuevo[-1].es_etiqueta():
            renombrar[q.resultado] = renombrar.get(nuevo[-1].resultado, nuevo[-1].resultado)
            ctx.eliminar(q, f"etiqueta duplicada (se usa {renombrar[q.resultado]})")
            continue
        nuevo.append(q)
    if not renombrar:
        return codigo, False
    final = []
    for q in nuevo:
        if q.es_salto() and q.destino in renombrar:
            q = q.con(nota=f"Mirilla: destino {q.destino} -> {renombrar[q.destino]}",
                      resultado=renombrar[q.destino])
        final.append(q)
    return final, True


def _etiquetas_sin_uso(codigo, ctx):
    usadas = {q.destino for q in codigo if q.es_salto()}
    nuevo, cambio = [], False
    for q in codigo:
        if q.es_etiqueta() and q.resultado not in usadas:
            ctx.eliminar(q, "etiqueta sin referencias")
            cambio = True
            continue
        nuevo.append(q)
    return nuevo, cambio


def _cargas_almacenamientos(codigo, ctx):
    nuevo, cambio = [], False
    for q in codigo:
        previo = nuevo[-1] if nuevo else None
        if q.es_copia() and q.arg1 == q.resultado:
            ctx.eliminar(q, "auto-asignación redundante")
            cambio = True
            continue
        if (previo is not None and q.es_copia() and previo.es_copia()
                and q.arg1 == previo.resultado and q.resultado == previo.arg1):
            ctx.eliminar(q, f"almacenamiento redundante (ya {previo.resultado} = {previo.arg1})")
            cambio = True
            continue
        if (previo is not None and q.tupla() == previo.tupla() and q.definicion()
                and q.definicion() not in q.usos() and not q.tiene_efecto_lateral()):
            ctx.eliminar(q, "instrucción repetida consecutiva")
            cambio = True
            continue
        nuevo.append(q)
    return nuevo, cambio


def pase_mirilla(codigo, ctx):
    reglas = [_saltos_a_saltos, _codigo_tras_goto, _saltos_a_siguiente,
              _fusionar_etiquetas, _etiquetas_sin_uso, _cargas_almacenamientos]
    for _ in range(20):
        hubo = False
        for regla in reglas:
            codigo, c = regla(codigo, ctx)
            hubo = hubo or c
        if not hubo:
            break
    return codigo
