# -*- coding: utf-8 -*-
"""
app_tk.py
=========
Capa de presentación (solo Tkinter / ttk de la biblioteca estándar).
Toda la lógica formal vive en motor_formal.py.

Ejecutar:  python app_tk.py
"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import motor_formal as mf

EJEMPLO_OK = """# Receta: pan casero (8 pasos)
AGREGAR 500 g DE harina
AGREGAR 300 ml DE agua
AGREGAR 10 g DE sal
MEZCLAR harina Y agua Y sal COMO masa POR 10 min
CALENTAR masa A 40 GRADOS POR 60 min
CORTAR masa EN porciones
HORNEAR masa A 220 GRADOS POR 35 min
SERVIR masa
"""

EJEMPLO_ERRORES = """# Receta con errores sintácticos
AGREGAR 200 g harina
AGREGAR dos tazas DE agua
MEZCLAR
BATIR huevos
CALENTAR agua A 100
HORNEAR pan A 200 GRADOS POR 20
AGREGAR 2 piezas DE huevo @
AGREGAR 1 kg DE azucar
SERVIR azucar
"""


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Compilador de Recetario Técnico y Lenguajes Formales — TMC")
        self.geometry("1240x780")
        self.minsize(1000, 640)

        st = ttk.Style(self)
        if "clam" in st.theme_names():
            st.theme_use("clam")
        st.configure("TNotebook.Tab", padding=(12, 6), font=("TkDefaultFont", 10, "bold"))
        st.configure("Treeview", rowheight=24)
        st.configure("Accion.TButton", font=("TkDefaultFont", 10, "bold"), padding=6)

        self.mono = tkfont.nametofont("TkFixedFont").copy()
        self.mono.configure(size=11)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_a, self.tab_b = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(self.tab_a, text="Módulo A · Compilador de Recetario")
        nb.add(self.tab_b, text="Módulo B · Conjuntos, Números y Lenguajes")
        self._construir_a()
        self._construir_b()

        self.bind("<F5>", lambda e: self.compilar())
        self.bind("<Control-Return>", lambda e: self.compilar())
        self.cargar_ejemplo(EJEMPLO_OK)
        self.compilar()
        self.calcular_conjuntos()
        self.generar_kleene()

    # ------------------------------------------------------------------
    #  Utilidades de widgets
    # ------------------------------------------------------------------
    def _texto_ro(self, parent):
        fr = ttk.Frame(parent)
        t = tk.Text(fr, wrap="word", font=self.mono, state="disabled", padx=8, pady=6,
                    background="#fbfbfb", relief="flat", borderwidth=1)
        sb = ttk.Scrollbar(fr, command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        return fr, t

    def _tabla(self, parent, columnas):
        fr = ttk.Frame(parent)
        tv = ttk.Treeview(fr, columns=[c[0] for c in columnas], show="headings", selectmode="browse")
        for cid, titulo, ancho, *resto in columnas:
            tv.heading(cid, text=titulo)
            tv.column(cid, width=ancho, anchor=resto[0] if resto else "w", stretch=(cid == columnas[-1][0]))
        sb = ttk.Scrollbar(fr, command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(side="left", fill="both", expand=True)
        return fr, tv

    @staticmethod
    def _escribir(txt, contenido):
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.insert("1.0", contenido)
        txt.configure(state="disabled")

    # ------------------------------------------------------------------
    #  MÓDULO A
    # ------------------------------------------------------------------
    def _construir_a(self):
        barra = ttk.Frame(self.tab_a)
        barra.pack(fill="x", padx=6, pady=(8, 4))
        ttk.Button(barra, text="▶ Compilar (F5)", style="Accion.TButton", command=self.compilar).pack(side="left")
        ttk.Button(barra, text="Ejemplo válido", command=lambda: self._ejemplo(EJEMPLO_OK)).pack(side="left", padx=(12, 2))
        ttk.Button(barra, text="Ejemplo con errores", command=lambda: self._ejemplo(EJEMPLO_ERRORES)).pack(side="left", padx=2)
        ttk.Button(barra, text="Abrir…", command=self.abrir).pack(side="left", padx=(12, 2))
        ttk.Button(barra, text="Guardar .asm…", command=self.guardar_asm).pack(side="left", padx=2)
        ttk.Button(barra, text="Limpiar", command=lambda: self.cargar_ejemplo("")).pack(side="left", padx=2)
        self.estado_a = ttk.Label(barra, text="", font=("TkDefaultFont", 10, "bold"))
        self.estado_a.pack(side="right", padx=8)

        pan = ttk.PanedWindow(self.tab_a, orient="horizontal")
        pan.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # --- editor con numeración de líneas ---
        izq = ttk.LabelFrame(pan, text=" Editor del recetario ")
        pan.add(izq, weight=1)
        cont = ttk.Frame(izq)
        cont.pack(fill="both", expand=True, padx=4, pady=4)
        self.ln = tk.Text(cont, width=4, font=self.mono, state="disabled", background="#eceff1",
                          foreground="#607d8b", relief="flat", padx=4, pady=6, cursor="arrow")
        self.editor = tk.Text(cont, wrap="none", font=self.mono, undo=True, padx=6, pady=6,
                              background="white", insertbackground="#222", relief="flat")
        sb = ttk.Scrollbar(cont, command=self._yview_ambos)
        self.editor.configure(yscrollcommand=lambda a, b: (sb.set(a, b), self.ln.yview_moveto(a)))
        self.ln.pack(side="left", fill="y")
        sb.pack(side="right", fill="y")
        self.editor.pack(side="left", fill="both", expand=True)
        self.ln.bind("<MouseWheel>", lambda e: "break")
        self.editor.bind("<KeyRelease>", lambda e: self._numerar())
        self.editor.bind("<<Paste>>", lambda e: self.after(10, self._numerar))
        self.editor.tag_configure("err", background="#ffd6d6")
        self.editor.tag_configure("warn", background="#fff1c2")

        # --- resultados ---
        der = ttk.Notebook(pan)
        pan.add(der, weight=1)
        f_asm, self.txt_asm = self._texto_ro(der)
        f_diag, self.tv_diag = self._tabla(der, [("nivel", "Tipo", 110), ("linea", "Línea", 60, "center"),
                                                 ("col", "Col.", 55, "center"), ("msg", "Diagnóstico", 520)])
        f_tok, self.tv_tok = self._tabla(der, [("linea", "Línea", 60, "center"), ("col", "Col.", 55, "center"),
                                               ("tipo", "Token", 140), ("lex", "Lexema", 200)])
        f_gram, self.txt_gram = self._texto_ro(der)
        der.add(f_asm, text="Ensamblador")
        der.add(f_diag, text="Diagnósticos")
        der.add(f_tok, text="Tokens")
        der.add(f_gram, text="Gramática y Regex")
        self._escribir(self.txt_gram, mf.texto_gramatica())
        self.tv_diag.tag_configure("ERROR", foreground="#c62828")
        self.tv_diag.tag_configure("ADVERTENCIA", foreground="#b26a00")
        self.tv_diag.bind("<Double-1>", self._ir_a_linea)
        self.nb_res = der

    def _yview_ambos(self, *a):
        self.editor.yview(*a)
        self.ln.yview(*a)

    def _numerar(self):
        n = int(self.editor.index("end-1c").split(".")[0])
        self.ln.configure(state="normal")
        self.ln.delete("1.0", "end")
        self.ln.insert("1.0", "\n".join(str(i) for i in range(1, n + 1)))
        self.ln.configure(state="disabled")
        self.ln.yview_moveto(self.editor.yview()[0])

    def cargar_ejemplo(self, texto):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", texto)
        self._numerar()

    def _ejemplo(self, texto):
        self.cargar_ejemplo(texto)
        self.compilar()

    def abrir(self):
        ruta = filedialog.askopenfilename(filetypes=[("Recetas / texto", "*.txt *.receta"), ("Todos", "*.*")])
        if ruta:
            with open(ruta, encoding="utf-8") as f:
                self._ejemplo(f.read())

    def guardar_asm(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".asm", filetypes=[("Ensamblador", "*.asm")])
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(self.txt_asm.get("1.0", "end-1c"))

    def _ir_a_linea(self, _evt):
        sel = self.tv_diag.selection()
        if sel:
            linea = self.tv_diag.item(sel[0], "values")[1]
            self.editor.see(f"{linea}.0")
            self.editor.mark_set("insert", f"{linea}.0")
            self.editor.focus_set()

    def compilar(self):
        res = mf.compilar(self.editor.get("1.0", "end-1c"))
        self._escribir(self.txt_asm, res.asm)
        for tv in (self.tv_diag, self.tv_tok):
            tv.delete(*tv.get_children())
        for t in ("err", "warn"):
            self.editor.tag_remove(t, "1.0", "end")
        for d in res.diagnosticos:
            self.tv_diag.insert("", "end", values=(d.nivel, d.linea, d.col, d.mensaje), tags=(d.nivel,))
            self.editor.tag_add("err" if d.nivel == "ERROR" else "warn", f"{d.linea}.0", f"{d.linea}.end")
        for t in res.tokens:
            self.tv_tok.insert("", "end", values=(t.linea, t.col, t.tipo, t.lexema))
        ne, na, ns = len(res.errores), len(res.advertencias), len(res.sentencias)
        self.estado_a.configure(
            text=f"{ns} sentencia(s) válida(s) · {ne} error(es) · {na} advertencia(s)",
            foreground="#2e7d32" if ne == 0 else "#c62828")
        if ne or na:
            self.nb_res.select(1)
        else:
            self.nb_res.select(0)

    # ------------------------------------------------------------------
    #  MÓDULO B
    # ------------------------------------------------------------------
    def _construir_b(self):
        top = ttk.LabelFrame(self.tab_b, text=" Conjuntos de entrada (separar con comas; admite enteros, 3/4, 0.5, símbolos) ")
        top.pack(fill="x", padx=8, pady=(8, 4))
        top.columnconfigure(1, weight=1)
        self.var_a = tk.StringVar(value="1, 2, 3, -4, 1/2, 0.75, a, b, hola")
        self.var_b = tk.StringVar(value="2, 3, 5, 1/2, 3/4, a, c, -4")
        for i, (lbl, var) in enumerate((("A =", self.var_a), ("B =", self.var_b))):
            ttk.Label(top, text=lbl, font=("TkDefaultFont", 10, "bold")).grid(row=i, column=0, padx=8, pady=4, sticky="e")
            ttk.Entry(top, textvariable=var, font=self.mono).grid(row=i, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(top, text="Calcular", style="Accion.TButton", command=self.calcular_conjuntos).grid(
            row=0, column=2, rowspan=2, padx=10, pady=4, sticky="ns")

        sub = ttk.Notebook(self.tab_b)
        sub.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        f1, self.txt_alg = self._texto_ro(sub)
        f2, self.tv_cls = self._tabla(sub, [("conj", "Conjunto", 80, "center"), ("clase", "Clase", 260),
                                            ("elems", "Elementos", 620)])
        sub.add(f1, text="Álgebra de conjuntos")
        sub.add(f2, text="Clases numéricas")
        self.txt_alg.tag_configure("h", font=(self.mono.actual("family"), 11, "bold"), foreground="#1a237e")
        self.txt_alg.tag_configure("aviso", foreground="#b26a00")

        # --- Kleene ---
        f3 = ttk.Frame(sub)
        sub.add(f3, text="Clausura de Kleene Σ*")
        ctl = ttk.Frame(f3)
        ctl.pack(fill="x", padx=6, pady=6)
        ttk.Label(ctl, text="Σ =", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self.var_sigma = tk.StringVar(value="a, b")
        ttk.Entry(ctl, textvariable=self.var_sigma, width=28, font=self.mono).pack(side="left", padx=6)
        ttk.Label(ctl, text="Longitud máx. |w| ≤").pack(side="left", padx=(12, 4))
        self.var_n = tk.StringVar(value="3")
        ttk.Spinbox(ctl, from_=0, to=6, width=4, textvariable=self.var_n).pack(side="left")
        ttk.Button(ctl, text="Generar Σ*", style="Accion.TButton", command=self.generar_kleene).pack(side="left", padx=12)
        for txt, val in (("{a,b}", "a, b"), ("{0,1,2}", "0, 1, 2")):
            ttk.Button(ctl, text=txt, width=8, command=lambda v=val: (self.var_sigma.set(v), self.generar_kleene())).pack(side="left", padx=2)
        fk, self.txt_kl = self._texto_ro(f3)
        fk.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.txt_kl.tag_configure("h", font=(self.mono.actual("family"), 11, "bold"), foreground="#1a237e")

    def _add(self, txt, s, tag=None):
        txt.insert("end", s, tag) if tag else txt.insert("end", s)

    def calcular_conjuntos(self):
        A, av_a = mf.parsear_conjunto(self.var_a.get())
        B, av_b = mf.parsear_conjunto(self.var_b.get())
        r = mf.algebra(A, B)
        yn = lambda b: "Verdadero" if b else "Falso"
        t = self.txt_alg
        t.configure(state="normal")
        t.delete("1.0", "end")
        self._add(t, "Conjuntos\n", "h")
        self._add(t, f"  A = {mf.fmt_conjunto(A)}      |A| = {r['|A|']}\n")
        self._add(t, f"  B = {mf.fmt_conjunto(B)}      |B| = {r['|B|']}\n\n")
        self._add(t, "Operaciones\n", "h")
        self._add(t, f"  A ∪ B = {mf.fmt_conjunto(r['union'])}\n")
        self._add(t, f"  A ∩ B = {mf.fmt_conjunto(r['interseccion'])}\n")
        self._add(t, f"  A \\ B = {mf.fmt_conjunto(r['A-B'])}\n")
        self._add(t, f"  B \\ A = {mf.fmt_conjunto(r['B-A'])}\n")
        self._add(t, f"  A △ B = {mf.fmt_conjunto(r['dif_sim'])}\n\n")
        self._add(t, "Relaciones de contención\n", "h")
        self._add(t, f"  A ⊆ B : {yn(r['A⊆B'])}\n")
        self._add(t, f"  B ⊆ A : {yn(r['B⊆A'])}\n")
        rel = ("A = B" if r["A=B"] else "A ⊂ B (contención propia)" if r["A⊂B"]
               else "B ⊂ A (contención propia)" if r["B⊂A"] else "ninguna contención entre A y B")
        self._add(t, f"  Resultado: {rel}; ¿disjuntos? {yn(r['disjuntos'])}\n")
        if av_a or av_b:
            self._add(t, "\nAvisos\n", "h")
            for a in av_a:
                self._add(t, f"  [A] {a}\n", "aviso")
            for a in av_b:
                self._add(t, f"  [B] {a}\n", "aviso")
        self._add(t, "\nNota: los números se comparan por valor exacto (0.75 ≡ 3/4 ≡ 6/8; 2 ≡ 2.0).\n")
        t.configure(state="disabled")

        self.tv_cls.delete(*self.tv_cls.get_children())
        for nombre, C in (("A", A), ("B", B)):
            for clase, elems in mf.clasificar(C).items():
                self.tv_cls.insert("", "end", values=(nombre, f"{clase}  ({len(elems)})", mf.fmt_conjunto(elems)))

    def generar_kleene(self):
        try:
            sigma = mf.parsear_alfabeto(self.var_sigma.get())
            n = int(self.var_n.get())
            pal = mf.cerradura_kleene(sigma, n)
        except ValueError as e:
            messagebox.showerror("Entrada no válida", str(e))
            return
        g = mf.gramatica_regular_derecha(sigma, n)
        t = self.txt_kl
        t.configure(state="normal")
        t.delete("1.0", "end")
        self._add(t, f"Σ = {{{', '.join(sigma)}}}      |Σ| = {len(sigma)}      Cadenas con |w| ≤ {n}\n\n", "h")
        total = 0
        for k, ws in pal.items():
            total += len(ws)
            self._add(t, f"|w| = {k}  ({len(ws)} cadena{'s' if len(ws) != 1 else ''}):\n", "h")
            self._add(t, "   " + ", ".join(ws) + "\n\n")
        suma = " + ".join(f"{len(sigma)}^{k}" for k in range(n + 1))
        self._add(t, f"Total = {suma} = {total} cadenas  (incluye la palabra vacía ε)\n\n")
        for clave, titulo in (("inf", "Gramática regular derecha de Σ*"),
                              ("fin", f"Gramática regular derecha del fragmento Σ^≤{n} (lenguaje finito)")):
            gg = g[clave]
            self._add(t, titulo + "\n", "h")
            self._add(t, f"  G = (VN, VT, P, S)\n  VN = {{{', '.join(gg['VN'])}}}\n"
                         f"  VT = {{{', '.join(gg['VT'])}}}\n  S  = {gg['S']}\n  P:\n")
            for p in gg["P"]:
                self._add(t, f"     {p}\n")
            self._add(t, "\n")
        if n >= 1:
            w = [sigma[-1]] * (n - 1) + [sigma[0]]
            self._add(t, f"Derivación de ejemplo (w = {''.join(w)}):\n", "h")
            self._add(t, "  " + mf.derivacion(w) + "\n")
        t.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()