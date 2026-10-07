# -*- coding: utf-8 -*-
"""
motor_formal.py
===============
Capa lógica / de cómputo formal de la práctica de Teoría Matemática de la
Computación.  NO importa Tkinter: la interfaz gráfica (app_tk.py) solo
consume las funciones de este módulo.

Módulo A : compilador de un DSL de recetario técnico
           (léxico -> sintaxis -> semántica -> generación de ensamblador)
Módulo B : álgebra de conjuntos, clases numéricas (N, Z, Q, símbolos)
           y clausura de Kleene con su gramática regular derecha.
"""
from __future__ import annotations

import itertools
import re
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Tuple, Union

# =====================================================================
#  MÓDULO A  ·  COMPILADOR DE RECETARIO TÉCNICO (DSL)
# =====================================================================

# --- A.1  Definición léxica: (nombre, expresión regular, descripción) ---
_ID = r"[^\W\d]\w*"
TABLA_TOKENS: List[Tuple[str, str, str]] = [
    ("COMENTARIO",     r"\#[^\n]*",                                   "Comentario hasta fin de línea"),
    ("ESPACIO",        r"[ \t\r]+",                                   "Espacios en blanco (se descartan)"),
    ("V_AGREGAR",      r"(?<!\w)AGREGAR(?!\w)",                       "Verbo de dispensado"),
    ("V_CORTE",        r"(?<!\w)(?:PICAR|CORTAR)(?!\w)",              "Verbo de corte"),
    ("V_MEZCLAR",      r"(?<!\w)MEZCLAR(?!\w)",                       "Verbo de homogenización"),
    ("V_CALOR",        r"(?<!\w)(?:CALENTAR|HORNEAR)(?!\w)",          "Verbo de aplicación térmica"),
    ("V_SERVIR",       r"(?<!\w)SERVIR(?!\w)",                        "Verbo de término"),
    ("PREP_DE",        r"(?<!\w)DE(?!\w)",                            "Preposición DE"),
    ("PREP_EN",        r"(?<!\w)EN(?!\w)",                            "Preposición EN"),
    ("PREP_POR",       r"(?<!\w)POR(?!\w)",                           "Preposición POR (duración)"),
    ("PREP_COMO",      r"(?<!\w)COMO(?!\w)",                          "Preposición COMO (nombre del resultado)"),
    ("PREP_A",         r"(?<!\w)A(?!\w)",                             "Preposición A (temperatura)"),
    ("PREP_Y",         r"(?<!\w)Y(?!\w)",                             "Conjunción Y"),
    ("NUM",            r"\d+(?:\.\d+)?",                              "Cantidad numérica (entera o decimal)"),
    ("UNIDAD_TIEMPO",  r"(?:segundos?|seg|minutos?|min|horas?|h)(?!\w)", "Unidad de tiempo"),
    ("UNIDAD_MED",     r"(?:mg|kg|g|ml|lt|l|tazas?|cucharaditas?|cucharadas?|piezas?|pizcas?|dientes?)(?!\w)",
                                                                      "Unidad de medida"),
    ("GRADOS",         r"(?:°\s*[Cc]?|grados?(?!\w))",                "Unidad de temperatura"),
    ("COMA",           r",",                                          "Separador de lista"),
    ("ID",             _ID,                                           "Identificador (ingrediente / forma)"),
    ("DESCONOCIDO",    r".",                                          "Carácter fuera del alfabeto del lenguaje"),
]
_MAESTRA = re.compile("|".join(f"(?P<{n}>{p})" for n, p, _ in TABLA_TOKENS),
                      re.IGNORECASE | re.UNICODE)

# Gramática formal G = (VN, VT, P, S) del recetario
GRAMATICA_RECETARIO = {
    "VN": ["RECETA", "SENT", "AGR", "PIC", "MEZ", "CAL", "SER",
           "LISTA", "SEP", "OPC_EN", "OPC_COMO", "OPC_POR", "OPC_ID"],
    "VT": ["AGREGAR", "PICAR", "CORTAR", "MEZCLAR", "CALENTAR", "HORNEAR", "SERVIR",
           "DE", "EN", "Y", ",", "COMO", "POR", "A", "NUM", "UNIDAD_MED",
           "UNIDAD_TIEMPO", "GRADOS", "ID", "NL"],
    "S": "RECETA",
    "P": [
        "RECETA   → SENT NL RECETA | ε",
        "SENT     → AGR | PIC | MEZ | CAL | SER",
        "AGR      → AGREGAR NUM UNIDAD_MED DE ID",
        "PIC      → (PICAR | CORTAR) ID OPC_EN",
        "OPC_EN   → EN ID | ε",
        "MEZ      → MEZCLAR ID LISTA OPC_COMO OPC_POR",
        "LISTA    → SEP ID LISTA | ε",
        "SEP      → Y | ,",
        "OPC_COMO → COMO ID | ε",
        "OPC_POR  → POR NUM UNIDAD_TIEMPO | ε",
        "CAL      → (CALENTAR | HORNEAR) ID A NUM GRADOS OPC_POR",
        "SER      → SERVIR OPC_ID",
        "OPC_ID   → ID | ε",
    ],
}


def texto_gramatica() -> str:
    g = GRAMATICA_RECETARIO
    out = ["G = (VN, VT, P, S)", "",
           "VN = { " + ", ".join(g["VN"]) + " }", "",
           "VT = { " + ", ".join(g["VT"]) + " }", "",
           f"S  = {g['S']}", "", "P:"]
    out += ["   " + p for p in g["P"]]
    out += ["", "Tabla de expresiones regulares del analizador léxico", "-" * 60]
    for n, p, d in TABLA_TOKENS:
        out.append(f"{n:<14} {p}")
        out.append(f"{'':<14} ↳ {d}")
    out.append("")
    out.append("Nota: las palabras reservadas no distinguen mayúsculas/minúsculas.")
    return "\n".join(out)


@dataclass
class Token:
    tipo: str
    lexema: str
    linea: int
    col: int


@dataclass
class Diagnostico:
    nivel: str      # "ERROR" | "ADVERTENCIA"
    linea: int
    col: int
    mensaje: str


@dataclass
class Sentencia:
    op: str
    linea: int
    texto: str
    datos: dict


@dataclass
class Resultado:
    tokens: List[Token] = field(default_factory=list)
    diagnosticos: List[Diagnostico] = field(default_factory=list)
    sentencias: List[Sentencia] = field(default_factory=list)
    asm: str = ""

    @property
    def errores(self) -> List[Diagnostico]:
        return [d for d in self.diagnosticos if d.nivel == "ERROR"]

    @property
    def advertencias(self) -> List[Diagnostico]:
        return [d for d in self.diagnosticos if d.nivel == "ADVERTENCIA"]


def tokenizar_linea(linea: str, nlin: int) -> Tuple[List[Token], List[Diagnostico]]:
    toks, errs = [], []
    for m in _MAESTRA.finditer(linea):
        tipo, lex = m.lastgroup, m.group()
        if tipo == "DESCONOCIDO":
            errs.append(Diagnostico("ERROR", nlin, m.start() + 1,
                                    f"Error léxico: carácter no reconocido '{lex}'"))
        else:
            toks.append(Token(tipo, lex, nlin, m.start() + 1))
    return toks, errs


# --- A.2  Análisis sintáctico (descenso recursivo) -------------------
class ErrorSintactico(Exception):
    def __init__(self, col: int, mensaje: str):
        super().__init__(mensaje)
        self.col, self.mensaje = col, mensaje


_UNIDADES_MED_TXT = "g, mg, kg, ml, l, tazas, cucharadas, cucharaditas, piezas, pizca, dientes"


class _Parser:
    def __init__(self, toks: List[Token], col_fin: int):
        self.t, self.i, self.col_fin = toks, 0, col_fin

    def peek(self) -> Optional[Token]:
        return self.t[self.i] if self.i < len(self.t) else None

    def tomar(self, tipo: str, desc: str) -> Token:
        tk = self.peek()
        if tk is None:
            raise ErrorSintactico(self.col_fin, f"Línea incompleta: se esperaba {desc}")
        if tk.tipo != tipo:
            raise ErrorSintactico(tk.col, f"Se esperaba {desc}, pero se encontró '{tk.lexema}'")
        self.i += 1
        return tk

    def si(self, tipo: str) -> Optional[Token]:
        tk = self.peek()
        if tk and tk.tipo == tipo:
            self.i += 1
            return tk
        return None

    def fin(self):
        tk = self.peek()
        if tk:
            raise ErrorSintactico(tk.col, f"Símbolo inesperado '{tk.lexema}': la sentencia ya estaba completa")

    # -- no terminales ------------------------------------------------
    def opc_por(self) -> float:
        if self.si("PREP_POR"):
            n = float(self.tomar("NUM", "una duración numérica después de POR").lexema)
            u = self.tomar("UNIDAD_TIEMPO", "una unidad de tiempo (seg, min, h)").lexema.lower()
            if n <= 0:
                raise ErrorSintactico(self.t[self.i - 2].col, "Error semántico: la duración debe ser mayor que 0")
            return n * (3600 if u.startswith("h") else 60 if u.startswith("min") else 1)
        return 0

    def sentencia(self) -> dict:
        v = self.peek()
        if v.tipo == "V_AGREGAR":
            self.i += 1
            q = self.tomar("NUM", "una cantidad numérica")
            u = self.tomar("UNIDAD_MED", f"una unidad de medida ({_UNIDADES_MED_TXT})")
            self.tomar("PREP_DE", "la preposición DE")
            ing = self.tomar("ID", "el nombre del ingrediente")
            self.fin()
            if float(q.lexema) <= 0:
                raise ErrorSintactico(q.col, "Error semántico: la cantidad debe ser mayor que 0")
            return dict(op="AGREGAR", cantidad=float(q.lexema), unidad=u.lexema, ing=ing.lexema, cols={"ing": ing.col})

        if v.tipo == "V_CORTE":
            self.i += 1
            ing = self.tomar("ID", "el ingrediente a cortar")
            forma = None
            if self.si("PREP_EN"):
                forma = self.tomar("ID", "la forma de corte (p. ej. cubos, tiras)").lexema
            self.fin()
            return dict(op=v.lexema.upper(), ing=ing.lexema, forma=forma, cols={"ing": ing.col})

        if v.tipo == "V_MEZCLAR":
            self.i += 1
            ings = [self.tomar("ID", "el primer ingrediente a mezclar")]
            while self.peek() and self.peek().tipo in ("PREP_Y", "COMA"):
                self.i += 1
                ings.append(self.tomar("ID", "un ingrediente después del separador"))
            como = None
            if self.si("PREP_COMO"):
                como = self.tomar("ID", "el nombre del resultado después de COMO").lexema
            seg = self.opc_por()
            self.fin()
            return dict(op="MEZCLAR", ings=[t.lexema for t in ings], cols=[t.col for t in ings],
                        como=como, seg=seg)

        if v.tipo == "V_CALOR":
            self.i += 1
            ing = self.tomar("ID", "el ingrediente/preparación a calentar")
            self.tomar("PREP_A", "la preposición A seguida de la temperatura")
            n = self.tomar("NUM", "una temperatura numérica")
            self.tomar("GRADOS", "la unidad GRADOS (o °C)")
            seg = self.opc_por()
            self.fin()
            if not (0 < float(n.lexema) <= 500):
                raise ErrorSintactico(n.col, "Error semántico: temperatura fuera de rango (1–500 °C)")
            return dict(op=v.lexema.upper(), ing=ing.lexema, temp=float(n.lexema), seg=seg,
                        cols={"ing": ing.col})

        if v.tipo == "V_SERVIR":
            self.i += 1
            ing = self.si("ID")
            self.fin()
            return dict(op="SERVIR", ing=ing.lexema if ing else None,
                        cols={"ing": ing.col if ing else 0})

        raise ErrorSintactico(
            v.col,
            f"Sentencia no válida: se esperaba un verbo (AGREGAR, PICAR, CORTAR, MEZCLAR, "
            f"CALENTAR, HORNEAR, SERVIR) y se encontró '{v.lexema}'")


# --- A.3  Generación de código ensamblador ---------------------------
_UNIDADES_COD = ["MG", "G", "KG", "ML", "L", "TAZA", "CUCHARADA", "CUCHARADITA", "PIEZA", "PIZCA", "DIENTE"]


def _norm_unidad(u: str) -> str:
    u = u.lower()
    if u in ("lt", "l"):
        return "L"
    for base in ("taza", "cucharadita", "cucharada", "pieza", "pizca", "diente"):
        if u.startswith(base):
            return base.upper()
    return u.upper()


def _etq(nombre: str) -> str:
    s = unicodedata.normalize("NFD", nombre)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\W", "_", s).upper()


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def generar_asm(res: Resultado) -> str:
    ing: Dict[str, int] = {}
    formas: Dict[str, int] = {}
    unis: List[str] = []
    cuerpo: List[str] = []

    def I(nombre: str) -> str:
        ing.setdefault(nombre.lower(), len(ing) + 1)
        return "ING_" + _etq(nombre)

    def F(nombre: Optional[str]) -> str:
        if not nombre:
            return "0"
        formas.setdefault(nombre.lower(), len(formas) + 1)
        return "FORMA_" + _etq(nombre)

    for s in res.sentencias:
        d = s.datos
        cuerpo.append(f"; L{s.linea}: {s.texto}")
        if d["op"] == "AGREGAR":
            u = _norm_unidad(d["unidad"])
            if u not in unis:
                unis.append(u)
            cuerpo += [f"    MOV  R1, {I(d['ing'])}",
                       f"    MOV  R2, {_num(d['cantidad'])}",
                       f"    MOV  R3, UNI_{u}",
                       "    CALL sys_dispensar"]
        elif d["op"] in ("PICAR", "CORTAR"):
            cuerpo += [f"    MOV  R1, {I(d['ing'])}",
                       f"    MOV  R2, {F(d['forma'])}",
                       "    CALL sys_cortar"]
        elif d["op"] == "MEZCLAR":
            for n in d["ings"]:
                cuerpo.append(f"    PUSH {I(n)}")
            cuerpo += [f"    MOV  R1, {len(d['ings'])}",
                       f"    MOV  R2, {I(d['como']) if d['como'] else '0'}",
                       f"    MOV  R3, {_num(d['seg'])}",
                       "    CALL sys_mezclar"]
        elif d["op"] in ("CALENTAR", "HORNEAR"):
            cuerpo += [f"    MOV  R1, {I(d['ing'])}",
                       f"    MOV  R2, {_num(d['temp'])}",
                       f"    MOV  R3, {_num(d['seg'])}",
                       f"    CALL sys_{'calentar' if d['op'] == 'CALENTAR' else 'hornear'}"]
        elif d["op"] == "SERVIR":
            cuerpo += [f"    MOV  R1, {I(d['ing']) if d['ing'] else '0'}",
                       "    CALL sys_servir"]
    cuerpo.append("    HALT")

    cab = ["; ===== Ensamblador generado por el Compilador de Recetario =====",
           "; Máquina abstracta: registros R1..R3, pila y subrutinas CALL sys_*"]
    n_err = len(res.errores)
    if n_err:
        cab.append(f"; AVISO: {n_err} línea(s) con errores fueron omitidas de la traducción")
    cab += [".data"]
    cab += [f"    ING_{_etq(n):<16} EQU {k}" for n, k in ing.items()]
    cab += [f"    UNI_{u:<16} EQU {_UNIDADES_COD.index(u) + 1}" for u in unis if u in _UNIDADES_COD]
    cab += [f"    FORMA_{_etq(n):<14} EQU {k}" for n, k in formas.items()]
    cab += [".text", "main:"]
    return "\n".join(cab + cuerpo) + "\n"


# --- Orquestación ----------------------------------------------------
def compilar(texto: str) -> Resultado:
    res = Resultado()
    definidos = set()
    for nlin, linea in enumerate(texto.splitlines(), start=1):
        toks, errs_lex = tokenizar_linea(linea, nlin)
        res.diagnosticos += errs_lex
        utiles = [t for t in toks if t.tipo not in ("ESPACIO", "COMENTARIO")]
        res.tokens += utiles
        if errs_lex or not utiles:
            continue
        try:
            datos = _Parser(utiles, len(linea) + 1).sentencia()
        except ErrorSintactico as e:
            res.diagnosticos.append(Diagnostico("ERROR", nlin, e.col, e.mensaje))
            continue
        # comprobación semántica ligera: uso de ingredientes no declarados
        usados = []
        if datos["op"] == "MEZCLAR":
            usados = list(zip(datos["ings"], datos["cols"]))
        elif datos.get("ing") and datos["op"] != "AGREGAR":
            usados = [(datos["ing"], datos["cols"]["ing"])]
        for nombre, col in usados:
            if nombre.lower() not in definidos:
                res.diagnosticos.append(Diagnostico(
                    "ADVERTENCIA", nlin, col, f"'{nombre}' se usa sin haber sido agregado/definido antes"))
        if datos["op"] == "AGREGAR":
            definidos.add(datos["ing"].lower())
        if datos["op"] == "MEZCLAR" and datos["como"]:
            definidos.add(datos["como"].lower())
        res.sentencias.append(Sentencia(datos["op"], nlin, linea.split("#")[0].strip(), datos))
    res.asm = generar_asm(res)
    return res


# =====================================================================
#  MÓDULO B  ·  CONJUNTOS, NÚMEROS Y LENGUAJES FORMALES
# =====================================================================
Elemento = Union[Fraction, str]

_RE_INT = re.compile(r"^[+-]?\d+$")
_RE_FRAC = re.compile(r"^([+-]?\d+)\s*/\s*(\d+)$")
_RE_DEC = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+)$")


def parsear_elemento(txt: str) -> Tuple[Elemento, Optional[str]]:
    """Convierte texto en Fraction (numérico exacto) o str (símbolo)."""
    t = txt.strip().replace("−", "-")
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        return t[1:-1], None                      # entre comillas -> símbolo literal
    if _RE_INT.match(t):
        return Fraction(int(t)), None
    m = _RE_FRAC.match(t)
    if m:
        if int(m.group(2)) == 0:
            return t, f"'{t}' tiene denominador 0: se trata como símbolo"
        return Fraction(int(m.group(1)), int(m.group(2))), None
    if _RE_DEC.match(t):
        return Fraction(t), None
    return t, None


def _clave(e: Elemento):
    return (0, e, "") if isinstance(e, Fraction) else (1, 0, e.lower())


def parsear_conjunto(texto: str) -> Tuple[List[Elemento], List[str]]:
    t = texto.strip()
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1]
    avisos: List[str] = []
    vistos: Dict[Elemento, int] = {}
    for crudo in re.split(r"[,;]", t):
        if not crudo.strip():
            continue
        e, av = parsear_elemento(crudo)
        if av:
            avisos.append(av)
        vistos[e] = vistos.get(e, 0) + 1
    repetidos = [fmt_elem(e) for e, c in vistos.items() if c > 1]
    if repetidos:
        avisos.append("Elementos repetidos (o equivalentes, p. ej. 0.5 = 1/2) fusionados: " + ", ".join(repetidos))
    return sorted(vistos, key=_clave), avisos


def fmt_elem(e: Elemento) -> str:
    if isinstance(e, Fraction):
        return str(e.numerator) if e.denominator == 1 else f"{e.numerator}/{e.denominator}"
    return e


def fmt_conjunto(c: List[Elemento]) -> str:
    return "∅" if not c else "{" + ", ".join(fmt_elem(e) for e in c) + "}"


# --- B.1 Álgebra de conjuntos ---------------------------------------
def algebra(A: List[Elemento], B: List[Elemento]) -> dict:
    a, b = set(A), set(B)
    s = lambda x: sorted(x, key=_clave)
    return {
        "|A|": len(a), "|B|": len(b),
        "union": s(a | b), "interseccion": s(a & b),
        "A-B": s(a - b), "B-A": s(b - a), "dif_sim": s(a ^ b),
        "A⊆B": a <= b, "B⊆A": b <= a,
        "A=B": a == b, "A⊂B": a < b, "B⊂A": b < a, "disjuntos": not (a & b),
    }


# --- B.2 Clasificación numérica (colecciones disjuntas) -------------
def clasificar(C: List[Elemento]) -> Dict[str, List[Elemento]]:
    r = {"Naturales (ℕ)": [], "Enteros negativos (ℤ \\ ℕ)": [],
         "Racionales no enteros (ℚ \\ ℤ)": [], "Símbolos no numéricos": []}
    for e in C:
        if isinstance(e, str):
            r["Símbolos no numéricos"].append(e)
        elif e.denominator != 1:
            r["Racionales no enteros (ℚ \\ ℤ)"].append(e)
        elif e >= 0:
            r["Naturales (ℕ)"].append(e)
        else:
            r["Enteros negativos (ℤ \\ ℕ)"].append(e)
    return r


# --- B.3 Clausura de Kleene -----------------------------------------
LIMITE_CADENAS = 50_000


def parsear_alfabeto(texto: str) -> List[str]:
    t = texto.strip()
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1]
    partes = [p for p in re.split(r"[,;\s]+", t) if p]
    if len(partes) == 1 and len(partes[0]) > 1:      # "01" -> ['0','1']
        partes = list(partes[0])
    sigma = list(dict.fromkeys(partes))
    if not sigma:
        raise ValueError("El alfabeto Σ no puede estar vacío.")
    if "ε" in sigma:
        raise ValueError("ε no puede pertenecer al alfabeto Σ.")
    return sigma


def cerradura_kleene(sigma: List[str], n: int = 3) -> Dict[int, List[str]]:
    if n < 0:
        raise ValueError("La longitud máxima debe ser ≥ 0.")
    total = sum(len(sigma) ** k for k in range(n + 1))
    if total > LIMITE_CADENAS:
        raise ValueError(f"Se generarían {total} cadenas (límite {LIMITE_CADENAS}). Reduce |Σ| o la longitud.")
    out: Dict[int, List[str]] = {0: ["ε"]}
    for k in range(1, n + 1):
        out[k] = ["".join(p) for p in itertools.product(sigma, repeat=k)]
    return out


def gramatica_regular_derecha(sigma: List[str], n: int = 3) -> dict:
    """G∞ para Σ* y G≤n para el lenguaje finito Σ^{≤n}."""
    inf = {"VN": ["S"], "VT": sigma, "S": "S",
           "P": ["S → " + " | ".join(f"{a}S" for a in sigma) + " | ε"]}
    vn = [f"S{i}" for i in range(n + 1)]
    p = []
    for i in range(n):
        p.append(f"S{i} → " + " | ".join(f"{a}S{i + 1}" for a in sigma) + " | ε")
    p.append(f"S{n} → ε")
    return {"inf": inf, "fin": {"VN": vn, "VT": sigma, "S": "S0", "P": p}}


def derivacion(palabra: List[str]) -> str:
    """Derivación por la izquierda de una palabra en G∞ (S → aS | ε)."""
    pasos = ["S"]
    for i in range(len(palabra)):
        pasos.append("".join(palabra[: i + 1]) + "S")
    pasos.append("".join(palabra) or "ε")
    return " ⇒ ".join(pasos)