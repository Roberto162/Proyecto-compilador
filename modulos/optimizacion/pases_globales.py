"""
modulos/optimizacion/pases_globales.py
======================================
FASE 2 — NIVEL 2: Optimizaciones globales y de ciclos (entre bloques básicos).

  * Propagación de constantes global (análisis de flujo de datos sobre el CFG,
    retícula  INDEFINIDO > constante > NO-CONSTANTE, algoritmo de Kildall).
  * Propagación de copias global (copias disponibles, sólo hacia temporales).
  * Eliminación de código inalcanzable (bloques sin camino desde la entrada).
  * Eliminación de código muerto (análisis de variables vivas).
  * Movimiento de código invariante de ciclo (LICM) hacia el pre-header.
"""

from modulos.optimizacion.cuadruplo import (
    Cuadruplo, es_constante, es_temporal, es_variable, OP_COPIA, OP_ETIQUETA
)
from modulos.optimizacion.bloques import (
    particionar, reensamblar, alcanzables, analisis_vida, dominadores, ciclos_naturales
)
from modulos.optimizacion.pases_locales import plegar


# ---------------------------------------------------------------------------
# Marco genérico de análisis hacia adelante
# ---------------------------------------------------------------------------
def _flujo_adelante(bloques, transferir_bloque, reunir):
    """
    Resuelve un análisis hacia adelante. Un predecesor aún no procesado (None)
    representa el elemento superior de la retícula y no participa en la reunión.
    El bloque de entrada siempre recibe el estado vacío (nada se sabe al iniciar).
    """
    entrada = {b.id: None for b in bloques}
    salida = {b.id: None for b in bloques}
    cambio = True
    while cambio:
        cambio = False
        for b in bloques:
            estados = [salida[p] for p in b.predecesores if salida[p] is not None]
            if b.id == 0:
                estados.append({})
            if not estados:
                continue
            inn = reunir(estados)
            out = transferir_bloque(b, dict(inn))
            if inn != entrada[b.id] or out != salida[b.id]:
                entrada[b.id], salida[b.id], cambio = inn, out, True
    return entrada


def _reunir_iguales(estados):
    """Intersección: se conserva var->valor sólo si todos los caminos coinciden."""
    base = dict(estados[0])
    for e in estados[1:]:
        base = {k: v for k, v in base.items() if e.get(k) == v}
    return base


# ---------------------------------------------------------------------------
# Propagación de constantes
# ---------------------------------------------------------------------------
def _reescribir_const(q, estado):
    """Sustituye operandos constantes conocidos y pliega. Devuelve (nueva|None, notas)."""
    q2, cambio = q.sustituir_usos(estado)
    notas = []
    if cambio:
        reemplazos = ", ".join(dict.fromkeys(f"{getattr(q, p)}={getattr(q2, p)}" for p in q.posiciones_uso()
                                             if getattr(q, p) != getattr(q2, p)))
        q2 = q2.con(nota=f"Prop. constantes: {reemplazos}")
        notas.append(f"Prop. constantes: {reemplazos}")
    plegado = plegar(q2)
    if plegado is not None:
        q3, desc = plegado
        notas.append(desc)
        return q3, notas
    return q2, notas


def _transferir_const(q, estado):
    d = q.definicion()
    if d is None:
        return
    if q.es_copia() and es_constante(q.arg1):
        estado[d] = q.arg1
    else:
        estado.pop(d, None)


def pase_propagacion_constantes(codigo, ctx):
    bloques = particionar(codigo)

    def transferir_bloque(b, estado):
        for q in b.instrucciones:
            q2, _ = _reescribir_const(q, estado)
            if q2 is not None:
                _transferir_const(q2, estado)
        return estado

    entrada = _flujo_adelante(bloques, transferir_bloque, _reunir_iguales)

    for b in bloques:
        estado = dict(entrada[b.id] or {})
        nuevas = []
        for q in b.instrucciones:
            q2, notas = _reescribir_const(q, estado)
            if q2 is None:
                ctx.eliminar(q, notas[-1])
                continue
            if q2.tupla() != q.tupla():
                ctx.log(f"{q.tac():<24} ->  {q2.tac():<20} [{'; '.join(notas)}]")
            _transferir_const(q2, estado)
            nuevas.append(q2)
        b.instrucciones = nuevas
    return reensamblar(bloques)


# ---------------------------------------------------------------------------
# Propagación de copias (sólo se propagan copias hacia temporales: t := y)
# ---------------------------------------------------------------------------
def _transferir_copia(q, estado):
    d = q.definicion()
    if d is None:
        return
    for k in [k for k, v in estado.items() if k == d or v == d]:
        del estado[k]
    if q.es_copia() and es_temporal(d) and es_variable(q.arg1) and q.arg1 != d:
        estado[d] = q.arg1


def pase_propagacion_copias(codigo, ctx):
    bloques = particionar(codigo)

    def transferir_bloque(b, estado):
        for q in b.instrucciones:
            q2, _ = q.sustituir_usos(estado)
            _transferir_copia(q2, estado)
        return estado

    entrada = _flujo_adelante(bloques, transferir_bloque, _reunir_iguales)

    for b in bloques:
        estado = dict(entrada[b.id] or {})
        nuevas = []
        for q in b.instrucciones:
            q2, cambio = q.sustituir_usos(estado)
            if cambio:
                reemplazos = ", ".join(dict.fromkeys(f"{getattr(q, p)}->{getattr(q2, p)}" for p in q.posiciones_uso()
                                                     if getattr(q, p) != getattr(q2, p)))
                q2 = q2.con(nota=f"Prop. copias: {reemplazos}")
                ctx.log(f"{q.tac():<24} ->  {q2.tac():<20} [Prop. copias: {reemplazos}]")
            _transferir_copia(q2, estado)
            nuevas.append(q2)
        b.instrucciones = nuevas
    return reensamblar(bloques)


# ---------------------------------------------------------------------------
# Código inalcanzable + código muerto
# ---------------------------------------------------------------------------
def pase_codigo_muerto(codigo, ctx):
    # 1) Bloques inalcanzables desde la entrada
    bloques = particionar(codigo)
    alc = alcanzables(bloques)
    for b in bloques:
        if b.id not in alc:
            for q in b.instrucciones:
                ctx.eliminar(q, f"código inalcanzable ({b.nombre})")
    codigo = reensamblar(bloques, omitir=set(range(len(bloques))) - alc)

    # 2) Asignaciones cuyo valor nunca se vuelve a leer (iterativo)
    while True:
        bloques = particionar(codigo)
        _, live_out = analisis_vida(bloques, ctx.salidas)
        hubo = False
        for b in bloques:
            vivas = set(live_out[b.id])
            conservadas = []
            for q in reversed(b.instrucciones):
                d = q.definicion()
                if d and not q.tiene_efecto_lateral() and d not in vivas:
                    ctx.eliminar(q, f"código muerto: '{d}' no se vuelve a leer")
                    hubo = True
                    continue
                if d:
                    vivas.discard(d)
                vivas |= set(q.usos())
                conservadas.append(q)
            b.instrucciones = list(reversed(conservadas))
        codigo = reensamblar(bloques)
        if not hubo:
            return codigo


# ---------------------------------------------------------------------------
# Movimiento de código invariante de ciclo (LICM)
# ---------------------------------------------------------------------------
def _buscar_invariantes(bloques, ciclo, dom, live_in, salidas_programa):
    """Devuelve la lista (en orden) de instrucciones del ciclo que pueden moverse."""
    cuerpo = sorted(ciclo.cuerpo)
    defs = {}
    for i in cuerpo:
        for q in bloques[i].instrucciones:
            d = q.definicion()
            if d:
                defs[d] = defs.get(d, 0) + 1

    salidas = ciclo.salidas(bloques)
    bloques_salida = {b for b, _ in salidas}
    destinos_salida = {s for _, s in salidas}
    vivas_tras_ciclo = set()
    for s in destinos_salida:
        vivas_tras_ciclo |= live_in[s]
    if not salidas:                     # ciclo sin salida: lo vivo al final del programa
        vivas_tras_ciclo |= set(salidas_programa)

    invariantes, marcadas = [], set()
    cambio = True
    while cambio:
        cambio = False
        for i in cuerpo:
            for q in bloques[i].instrucciones:
                # Se mueven expresiones (t = a op b) y copias (x = a) con operandos invariantes
                if id(q) in marcadas or not (q.es_expresion() or q.es_copia()):
                    continue
                d = q.resultado
                operandos = [getattr(q, pos) for pos in q.posiciones_uso()]
                operandos_ok = all(
                    es_constante(x) or defs.get(x, 0) == 0 or
                    any(id(p) in marcadas and p.resultado == x for p in invariantes)
                    for x in operandos
                )
                if not operandos_ok or defs.get(d, 0) != 1:
                    continue
                if d in live_in[ciclo.cabecera]:          # se usa antes de definirse en el ciclo
                    continue
                domina_salidas = all(i in dom.get(bs, set()) for bs in bloques_salida)
                if not domina_salidas and d in vivas_tras_ciclo:
                    continue
                if q.op == '/' and not (es_constante(q.arg2) and float(q.arg2) != 0) and not domina_salidas:
                    continue                               # no especular divisiones
                invariantes.append(q)
                marcadas.add(id(q))
                cambio = True
    # conservar el orden original de aparición
    orden = [q for i in cuerpo for q in bloques[i].instrucciones if id(q) in marcadas]
    return orden


def pase_licm(codigo, ctx):
    for _ in range(20):                                  # un ciclo a la vez hasta estabilizar
        bloques = particionar(codigo)
        dom = dominadores(bloques)
        live_in, _ = analisis_vida(bloques, ctx.salidas)
        movido = False
        for ciclo in ciclos_naturales(bloques, dom):
            mover = _buscar_invariantes(bloques, ciclo, dom, live_in, ctx.salidas)
            if not mover:
                continue
            cab = bloques[ciclo.cabecera]
            etiqueta_cab = cab.etiqueta
            # El pre-header se inserta físicamente antes de la cabecera: si el bloque anterior
            # pertenece al ciclo y cae directo en ella, no es seguro (se ejecutaría cada vuelta).
            anterior = bloques[cab.id - 1] if cab.id > 0 else None
            if (anterior is not None and anterior.id in ciclo.cuerpo
                    and not (anterior.ultima and anterior.ultima.es_salto_incondicional())):
                ctx.log(f"LICM omitido en {cab.nombre}: no se puede insertar un pre-header seguro")
                continue
            ids = {id(q) for q in mover}
            for i in ciclo.cuerpo:
                bloques[i].instrucciones = [q for q in bloques[i].instrucciones if id(q) not in ids]

            preheader = [q.con(nota=f"LICM: movido al pre-header de {etiqueta_cab or cab.nombre}")
                         for q in mover]
            for q in mover:
                ctx.log(f"↑ {q.tac():<22} sale del ciclo {etiqueta_cab or cab.nombre} (invariante)")

            # ¿Hay saltos desde FUERA del ciclo hacia la cabecera? -> nueva etiqueta de pre-header
            externos = [p for p in cab.predecesores if p not in ciclo.cuerpo
                        and bloques[p].ultima is not None and bloques[p].ultima.es_salto()
                        and bloques[p].ultima.destino == etiqueta_cab]
            if externos and etiqueta_cab:
                existentes = {q.resultado for b in bloques for q in b.instrucciones if q.es_etiqueta()}
                nueva = ctx.nueva_etiqueta(existentes)
                preheader.insert(0, Cuadruplo(OP_ETIQUETA, "", "", nueva, notas=["Nueva etiqueta de pre-header"]))
                for p in externos:
                    ult = bloques[p].instrucciones[-1]
                    bloques[p].instrucciones[-1] = ult.con(nota=f"Redirigido al pre-header {nueva}", resultado=nueva)
                ctx.log(f"Se crea la etiqueta de pre-header {nueva}")

            nuevo = []
            for b in bloques:
                if b.id == ciclo.cabecera:
                    nuevo.extend(preheader)
                nuevo.extend(b.instrucciones)
            codigo = nuevo
            movido = True
            break
        if not movido:
            return codigo
    return codigo
