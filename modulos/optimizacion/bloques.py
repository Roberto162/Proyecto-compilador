"""
modulos/optimizacion/bloques.py
===============================
FASE 1 — Análisis del flujo de control.

  1. Detección de líderes:
       a) la primera instrucción,
       b) toda etiqueta (destino potencial de un salto),
       c) toda instrucción inmediatamente posterior a un salto.
  2. Partición en Bloques Básicos (una sola entrada, una sola salida).
  3. Construcción del Grafo de Flujo de Control (CFG)  [puntos extra].
  4. Utilidades de análisis: alcanzabilidad, dominadores, ciclos naturales,
     vida de variables (liveness) y exportación a Graphviz (.dot).
"""

from dataclasses import dataclass, field


@dataclass
class BloqueBasico:
    id: int
    instrucciones: list
    sucesores: list = field(default_factory=list)
    predecesores: list = field(default_factory=list)

    @property
    def nombre(self):
        return f"B{self.id}"

    @property
    def etiqueta(self):
        """Nombre de la etiqueta con la que inicia el bloque (si la hay)."""
        if self.instrucciones and self.instrucciones[0].es_etiqueta():
            return self.instrucciones[0].resultado
        return None

    @property
    def ultima(self):
        return self.instrucciones[-1] if self.instrucciones else None


# ---------------------------------------------------------------------------
# Líderes y partición
# ---------------------------------------------------------------------------
def detectar_lideres(codigo):
    """Devuelve {indice: motivo} con las instrucciones líderes."""
    lideres = {}
    if not codigo:
        return lideres
    lideres[0] = "primera instrucción"
    for i, q in enumerate(codigo):
        if q.es_etiqueta() and i not in lideres:
            lideres[i] = f"destino de salto ({q.resultado})"
        if q.es_salto() and i + 1 < len(codigo) and (i + 1) not in lideres:
            lideres[i + 1] = f"sigue a un salto ({codigo[i].op})"
    return dict(sorted(lideres.items()))


def particionar(codigo):
    """Agrupa el código en bloques básicos y construye el CFG."""
    lideres = sorted(detectar_lideres(codigo))
    bloques = []
    for k, ini in enumerate(lideres):
        fin = lideres[k + 1] if k + 1 < len(lideres) else len(codigo)
        bloques.append(BloqueBasico(k, list(codigo[ini:fin])))
    construir_cfg(bloques)
    return bloques


def construir_cfg(bloques):
    """Calcula sucesores y predecesores de cada bloque."""
    por_etiqueta = {}
    for b in bloques:
        for q in b.instrucciones:
            if q.es_etiqueta():
                por_etiqueta[q.resultado] = b.id
    for b in bloques:
        b.sucesores, b.predecesores = [], []
    for b in bloques:
        ult = b.ultima
        sig = b.id + 1 if b.id + 1 < len(bloques) else None
        succ = []
        if ult is not None and ult.es_salto():
            if ult.destino in por_etiqueta:
                succ.append(por_etiqueta[ult.destino])
            if ult.es_salto_condicional() and sig is not None:
                succ.append(sig)
        elif sig is not None:
            succ.append(sig)
        b.sucesores = list(dict.fromkeys(succ))
    for b in bloques:
        for s in b.sucesores:
            bloques[s].predecesores.append(b.id)
    return bloques


def reensamblar(bloques, omitir=None):
    """Concatena los bloques (en su orden original) para volver a una lista lineal."""
    omitir = omitir or set()
    codigo = []
    for b in bloques:
        if b.id not in omitir:
            codigo.extend(b.instrucciones)
    return codigo


# ---------------------------------------------------------------------------
# Análisis sobre el CFG
# ---------------------------------------------------------------------------
def alcanzables(bloques):
    if not bloques:
        return set()
    vistos, pila = set(), [0]
    while pila:
        n = pila.pop()
        if n in vistos:
            continue
        vistos.add(n)
        pila.extend(bloques[n].sucesores)
    return vistos


def dominadores(bloques):
    """dom[n] = conjunto de bloques que dominan a n (algoritmo iterativo)."""
    alc = alcanzables(bloques)
    if not alc:
        return {}
    dom = {n: set(alc) for n in alc}
    dom[0] = {0}
    cambio = True
    while cambio:
        cambio = False
        for n in sorted(alc - {0}):
            preds = [p for p in bloques[n].predecesores if p in alc]
            nuevo = set.intersection(*(dom[p] for p in preds)) if preds else set()
            nuevo = nuevo | {n}
            if nuevo != dom[n]:
                dom[n], cambio = nuevo, True
    return dom


@dataclass
class Ciclo:
    cabecera: int
    cuerpo: set
    origenes_retroceso: list

    def salidas(self, bloques):
        """Pares (bloque_dentro, bloque_fuera) por donde se abandona el ciclo."""
        return [(b, s) for b in self.cuerpo for s in bloques[b].sucesores if s not in self.cuerpo]


def ciclos_naturales(bloques, dom=None):
    """Detecta ciclos naturales a partir de aristas de retroceso B -> H (H domina B)."""
    dom = dom if dom is not None else dominadores(bloques)
    por_cabecera = {}
    for b in bloques:
        if b.id not in dom:
            continue
        for h in b.sucesores:
            if h in dom[b.id]:                       # arista de retroceso
                cuerpo = {h, b.id}
                pila = [b.id] if b.id != h else []
                while pila:
                    n = pila.pop()
                    for p in bloques[n].predecesores:
                        if p not in cuerpo:
                            cuerpo.add(p)
                            pila.append(p)
                c = por_cabecera.setdefault(h, Ciclo(h, set(), []))
                c.cuerpo |= cuerpo
                c.origenes_retroceso.append(b.id)
    # primero los ciclos internos (más pequeños)
    return sorted(por_cabecera.values(), key=lambda c: len(c.cuerpo))


def uso_def_bloque(bloque):
    """USE = variables leídas antes de definirse en el bloque; DEF = variables definidas."""
    use, defs = set(), set()
    for q in bloque.instrucciones:
        for u in q.usos():
            if u not in defs:
                use.add(u)
        d = q.definicion()
        if d:
            defs.add(d)
    return use, defs


def analisis_vida(bloques, vivas_al_salir):
    """
    Análisis de variables vivas (hacia atrás).
    vivas_al_salir: variables observables al terminar el programa.
    Devuelve (live_in, live_out) como diccionarios id -> set.
    """
    ud = {b.id: uso_def_bloque(b) for b in bloques}
    live_in = {b.id: set() for b in bloques}
    live_out = {b.id: set() for b in bloques}
    cambio = True
    while cambio:
        cambio = False
        for b in reversed(bloques):
            out = set(vivas_al_salir) if not b.sucesores else set()
            for s in b.sucesores:
                out |= live_in[s]
            use, defs = ud[b.id]
            inn = use | (out - defs)
            if out != live_out[b.id] or inn != live_in[b.id]:
                live_out[b.id], live_in[b.id], cambio = out, inn, True
    return live_in, live_out


# ---------------------------------------------------------------------------
# Presentación
# ---------------------------------------------------------------------------
def formatear_bloques(codigo, titulo="BLOQUES BÁSICOS"):
    lideres = detectar_lideres(codigo)
    bloques = particionar(codigo)
    alc = alcanzables(bloques)
    lineas = [f"--- {titulo} ---", ""]
    if not codigo:
        return "\n".join(lineas + ["(código vacío)"])

    lineas.append("Líderes detectados:")
    for idx, motivo in lideres.items():
        lineas.append(f"  ({idx + 1:>2}) {codigo[idx].tac():<28} <- {motivo}")
    lineas.append("")

    pos = 0
    for b in bloques:
        marca = "" if b.id in alc else "   [INALCANZABLE]"
        lineas.append(f"┌─ {b.nombre}  ({len(b.instrucciones)} instr.){marca}")
        for q in b.instrucciones:
            pos += 1
            lineas.append(f"│  ({pos:>2}) {q.tac()}")
        succ = ", ".join(bloques[s].nombre for s in b.sucesores) or "FIN"
        lineas.append(f"└─ sucesores: {succ}")
    lineas.append("")
    lineas.append("Grafo de Flujo de Control (CFG):")
    for b in bloques:
        succ = ", ".join(bloques[s].nombre for s in b.sucesores) or "FIN"
        lineas.append(f"  {b.nombre} -> {succ}")
    ciclos = ciclos_naturales(bloques)
    if ciclos:
        lineas.append("")
        lineas.append("Ciclos naturales detectados:")
        for c in ciclos:
            cuerpo = ", ".join(bloques[i].nombre for i in sorted(c.cuerpo))
            lineas.append(f"  cabecera {bloques[c.cabecera].nombre}: {{{cuerpo}}}")
    return "\n".join(lineas)


def exportar_dot(codigo, nombre="CFG"):
    """Genera el CFG en formato Graphviz (.dot) para visualizarlo externamente."""
    bloques = particionar(codigo)
    out = [f'digraph {nombre} {{', '  node [shape=box, fontname="Consolas"];']
    for b in bloques:
        texto = "\\l".join(q.tac().replace('"', '\\"') for q in b.instrucciones) + "\\l"
        out.append(f'  {b.nombre} [label="{b.nombre}\\n{texto}"];')
    for b in bloques:
        for s in b.sucesores:
            out.append(f"  {b.nombre} -> {bloques[s].nombre};")
    out.append("}")
    return "\n".join(out)
