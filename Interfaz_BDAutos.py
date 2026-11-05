
import copy
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk

from Logica_BDAutos import LogicaAutos, LogicaCrearConsulta, codigo_mongodb

ROJO = "#B64D54"
ROJO_OSCURO = "#963B45"
AZUL = "#62374D"
AZUL_ACTIVO = "#432637"
NARANJA = "#EBA972"
BLANCO = "#FFFFFF"
LETRA = "#273443"
GRIS = "#657384"
FONDO = "#F4F6F9"
BORDE = "#DEE5EB"
SUAVE = "#F8FAFC"
ROJO_SUAVE = "#FCEFF0"
FUENTE = "Segoe UI"

class Panel(tk.Frame):
    """Tarjeta blanca, con borde delicado y sin alterar el contenido."""

    def __init__(self, padre, **kwargs):
        super().__init__(padre, bg=BORDE, **kwargs)
        self.interior = tk.Frame(self, bg=BLANCO)
        self.interior.pack(fill="both", expand=True, padx=1, pady=1)

class BarraVisual(tk.Canvas):
    """Barra decorativa desplazable, como en el boceto original."""

    def __init__(self, padre, canvas_contenido):
        super().__init__(padre, bg=ROJO, width=19, highlightthickness=0, bd=0,
                         cursor="hand2")
        self.contenido = canvas_contenido
        self.fracciones = (0.0, 1.0)
        self.medidas = (0, 0, 0)
        self.bind("<Configure>", lambda _: self.dibujar())
        self.bind("<Button-1>", self.arrastrar)
        self.bind("<B1-Motion>", self.arrastrar)

    def marcar(self, primero, ultimo):
        self.fracciones = (float(primero), float(ultimo))
        self.dibujar()

    def rectangulo_redondeado(self, x1, y1, x2, y2, radio, color):
        radio = min(radio, (x2-x1)/2, (y2-y1)/2)
        if radio <= 0:
            return
        self.create_rectangle(x1+radio, y1, x2-radio, y2, fill=color, outline="")
        self.create_rectangle(x1, y1+radio, x2, y2-radio, fill=color, outline="")
        for cx, cy in ((x1+radio,y1+radio), (x2-radio,y1+radio),
                       (x1+radio,y2-radio), (x2-radio,y2-radio)):
            self.create_oval(cx-radio, cy-radio, cx+radio, cy+radio,
                             fill=color, outline="")

    def dibujar(self):
        alto, ancho = self.winfo_height(), self.winfo_width()
        self.delete("all")
        if alto < 10 or ancho < 10:
            return
        x1, x2 = 4, ancho-4
        y1, y2 = 4, alto-4
        self.rectangulo_redondeado(x1, y1, x2, y2, 5, "#E9B4B7")
        primero, ultimo = self.fracciones
        visible = min(1.0, max(0.01, ultimo-primero))
        longitud = y2-y1
        tam = min(longitud, max(46, longitud*visible))
        inicio = y1 + ((longitud-tam)*primero/(1-visible) if visible < 1 else 0)
        self.medidas = (y1, longitud, tam)
        self.rectangulo_redondeado(x1, inicio, x2, inicio+tam, 5, AZUL_ACTIVO)

    def arrastrar(self, evento):
        y1, alto, tam = self.medidas
        rango = alto-tam
        if rango <= 0:
            return
        proporcion = max(0, min(1, (evento.y-y1-tam/2) / rango))
        self.contenido.yview_moveto(proporcion)

class CrearConsulta(LogicaCrearConsulta, tk.Toplevel):

    def __init__(self, app):
        super().__init__(app.raiz)
        self.app = app
        self.title("Crear consulta | BDAutos")
        self.geometry("900x760")
        self.minsize(760, 620)
        self.configure(bg="#E8EAED")
        self.transient(app.raiz)
        self.grab_set()
        self.resultado = None

        cabecera = tk.Frame(self, bg=ROJO, height=100)
        cabecera.pack(fill="x")
        cabecera.pack_propagate(False)
        tk.Label(
            cabecera, text="NUEVA CONSULTA", bg=ROJO, fg=BLANCO,
            font=(FUENTE, 26, "bold"), anchor="w"
        ).pack(fill="x", padx=34, pady=(26, 0))

        contenedor = tk.Frame(self, bg=BLANCO, highlightbackground="#8D8D8D", highlightthickness=1)
        contenedor.pack(fill="both", expand=True, padx=26, pady=24)

        formulario = tk.Frame(contenedor, bg=BLANCO)
        formulario.pack(fill="both", expand=True, padx=34, pady=28)

        tk.Label(formulario, text="Nombre de la consulta", bg=BLANCO, fg=LETRA,
                 font=(FUENTE, 12, "bold")).pack(anchor="w")
        self.nombre = tk.Entry(
            formulario, font=(FUENTE, 12), fg=LETRA, bg="#F6F7F9",
            relief="flat", highlightbackground="#B9B9B9", highlightthickness=1,
            insertbackground=LETRA
        )
        self.nombre.pack(fill="x", ipady=10, pady=(8, 20))

        tk.Label(formulario, text="Descripción de la consulta", bg=BLANCO, fg=LETRA,
                 font=(FUENTE, 12, "bold")).pack(anchor="w")
        self.descripcion = tk.Entry(
            formulario, font=(FUENTE, 12), fg=LETRA, bg="#F6F7F9",
            relief="flat", highlightbackground="#D5D9DE", highlightthickness=1,
            insertbackground=LETRA
        )
        self.descripcion.pack(fill="x", ipady=10, pady=(8, 16))

        opciones = tk.Frame(formulario, bg=BLANCO)
        opciones.pack(fill="x", pady=(0, 14))
        opciones.grid_columnconfigure(1, weight=1)
        opciones.grid_columnconfigure(3, weight=1)
        tk.Label(opciones, text="Colección", bg=BLANCO, fg=LETRA,
                 font=(FUENTE, 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.coleccion = ttk.Combobox(
            opciones, state="readonly", values=["autos", "fabricantes", "continentes"],
            font=(FUENTE, 10), width=18
        )
        self.coleccion.set("autos")
        self.coleccion.grid(row=0, column=1, sticky="w", padx=(0, 26), ipady=4)
        tk.Label(opciones, text="Tipo", bg=BLANCO, fg=LETRA,
                 font=(FUENTE, 10, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.tipo = ttk.Combobox(
            opciones, state="readonly", values=["aggregate", "find", "countDocuments"],
            font=(FUENTE, 10), width=18
        )
        self.tipo.set("aggregate")
        self.tipo.grid(row=0, column=3, sticky="w", ipady=4)
        self.tipo.bind("<<ComboboxSelected>>", self.cambiar_ejemplo)

        tk.Label(formulario, text="Consulta", bg=BLANCO, fg=LETRA,
                 font=(FUENTE, 12, "bold")).pack(anchor="w", pady=(4, 8))
        caja_editor = tk.Frame(formulario, bg="#D5D9DE", padx=1, pady=1)
        caja_editor.pack(fill="both", expand=True)
        self.json_editor = tk.Text(
            caja_editor, font=("Consolas", 12), undo=True, relief="flat", bd=0,
            wrap="none", padx=18, pady=16, bg="#F6F7F9", fg=LETRA,
            insertbackground=LETRA
        )
        scroll = tk.Scrollbar(caja_editor, command=self.json_editor.yview)
        self.json_editor.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.json_editor.pack(side="left", fill="both", expand=True)
        self.json_editor.insert("1.0", "[\n  {\"$match\": {\"especificaciones.year\": {\"$gte\": 2024}}},\n  {\"$limit\": 10}\n]")

        pie = tk.Frame(formulario, bg="#F3F3F3", height=126)
        pie.pack(fill="x", pady=(16, 0))
        pie.pack_propagate(False)
        self.estado_dialogo = tk.Label(
            pie,
            text="Escribe la consulta y presiona Guardar y ejecutar.",
            bg=ROJO, fg=BLANCO, justify="left", anchor="center",
            font=(FUENTE, 10, "bold"), padx=22, pady=12
        )
        self.estado_dialogo.pack(side="right", padx=28, pady=24)

        acciones = tk.Frame(formulario, bg=BLANCO)
        acciones.pack(fill="x", pady=(14, 0))
        tk.Button(
            acciones, text="Cancelar", command=self.destroy,
            font=(FUENTE, 10, "bold"), bg="#EAECEF", fg="#4C5866",
            activebackground="#DDE2E8", activeforeground="#4C5866",
            relief="flat", cursor="hand2", padx=18, pady=10
        ).pack(side="right", padx=(12, 0))
        tk.Button(
            acciones, text="Guardar y ejecutar", command=self.guardar,
            font=(FUENTE, 10, "bold"), bg=AZUL, fg=BLANCO,
            activebackground=AZUL_ACTIVO, activeforeground=BLANCO,
            relief="flat", cursor="hand2", padx=22, pady=10
        ).pack(side="right")

        self.bind("<Escape>", lambda _: self.destroy())
        self.nombre.focus_set()

    def _mensaje_estado(self, texto, error=False):
        self.estado_dialogo.configure(
            text=texto,
            bg="#A5484E" if not error else "#8E2F37",
            fg=BLANCO
        )


class AplicacionAutos(LogicaAutos):

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("BDAutos  •  Explorador de consultas MongoDB")
        self.raiz.geometry("1460x850")
        self.raiz.minsize(1060, 650)
        self.raiz.configure(bg=FONDO)
        self.uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.base_preferida = os.getenv("MONGODB_DB", "BDAutos")
        self.base_actual = None
        self.seleccion_actual = None
        self.folio = 0
        self.mensajes = queue.Queue()
        self.botones = {}
        self.estado_guardado = self._cargar_estado()
        self.consultas = self._consultas_visibles()
        self._crear_interfaz()
        self.raiz.bind("<Control-n>", lambda _: self.crear_consulta())
        self.raiz.after(130, self._revisar_mensajes)
        if self.consultas:
            self.raiz.after(220, lambda: self.seleccionar_consulta(self.consultas[0]["number"]))

    def crear_consulta(self):
        CrearConsulta(self)

    def _crear_interfaz(self):
        self.raiz.configure(bg=ROJO)
        cuerpo = tk.Frame(self.raiz, bg=ROJO)
        cuerpo.pack(fill="both", expand=True, padx=18, pady=18)

        lateral = tk.Frame(cuerpo, bg=ROJO, width=280)
        lateral.pack(side="left", fill="y", padx=(0, 16))
        lateral.pack_propagate(False)

        tk.Label(lateral, text="CONSULTAS", bg=ROJO, fg=BLANCO,
                 font=(FUENTE, 17, "bold"), anchor="w").pack(fill="x", padx=6, pady=(96, 18))

        tk.Button(
            lateral, text="+   Crear consulta", command=self.crear_consulta,
            bg=AZUL, fg=BLANCO, activebackground=AZUL_ACTIVO,
            activeforeground=BLANCO, font=(FUENTE, 11, "bold"),
            relief="flat", cursor="hand2", bd=0, pady=12
        ).pack(fill="x", padx=6, pady=(0, 18))

        tk.Label(lateral, text="LISTA DE CONSULTAS", bg=ROJO,
                 fg="#F7E2E4", font=(FUENTE, 9, "bold"), anchor="w").pack(fill="x", padx=6, pady=(0, 10))

        navegacion = tk.Frame(lateral, bg=ROJO)
        navegacion.pack(fill="both", expand=True, padx=(0, 0))
        self.canvas_lateral = tk.Canvas(navegacion, bg=ROJO, borderwidth=0, highlightthickness=0)
        barra = BarraVisual(navegacion, self.canvas_lateral)
        barra.pack(side="right", fill="y", padx=(8, 0))
        self.canvas_lateral.pack(side="left", fill="both", expand=True)
        self.canvas_lateral.configure(yscrollcommand=barra.marcar)
        self.contenido_lateral = tk.Frame(self.canvas_lateral, bg=ROJO)
        ventana = self.canvas_lateral.create_window((0, 0), window=self.contenido_lateral, anchor="nw")
        self.contenido_lateral.bind(
            "<Configure>", lambda _: self.canvas_lateral.configure(scrollregion=self.canvas_lateral.bbox("all"))
        )
        self.canvas_lateral.bind(
            "<Configure>", lambda e: self.canvas_lateral.itemconfigure(ventana, width=e.width)
        )

        def hacer_scroll(e):
            if getattr(e, "num", None) in (4, 5):
                unidades = -1 if e.num == 4 else 1
            else:
                unidades = -int(e.delta / 120) if e.delta else 0
            self.canvas_lateral.yview_scroll(unidades, "units")

        def activar(_):
            self.canvas_lateral.bind_all("<MouseWheel>", hacer_scroll)
            self.canvas_lateral.bind_all("<Button-4>", hacer_scroll)
            self.canvas_lateral.bind_all("<Button-5>", hacer_scroll)

        def desactivar(_):
            self.canvas_lateral.unbind_all("<MouseWheel>")
            self.canvas_lateral.unbind_all("<Button-4>")
            self.canvas_lateral.unbind_all("<Button-5>")

        navegacion.bind("<Enter>", activar)
        navegacion.bind("<Leave>", desactivar)
        self._actualizar_botones()

        pie_lateral = tk.Frame(lateral, bg=ROJO)
        pie_lateral.pack(fill="x", padx=6, pady=(14, 6))
        tk.Frame(pie_lateral, bg="#C97076", height=1).pack(fill="x", pady=(0, 12))
        tk.Button(pie_lateral, text="Restaurar 25", font=(FUENTE, 9, "bold"),
                  command=self.restaurar_originales, bg=ROJO_OSCURO, fg=BLANCO,
                  activebackground=AZUL_ACTIVO, activeforeground=BLANCO,
                  relief="flat", cursor="hand2", bd=0).pack(side="left", fill="x", expand=True, ipady=9)

        trabajo = tk.Frame(cuerpo, bg=ROJO)
        trabajo.pack(side="left", fill="both", expand=True)
        trabajo.grid_columnconfigure(0, weight=1, uniform="area")
        trabajo.grid_columnconfigure(1, weight=1, uniform="area")
        trabajo.grid_rowconfigure(0, weight=0, minsize=160)
        trabajo.grid_rowconfigure(1, weight=1)

        superior = Panel(trabajo)
        superior.grid(row=0, column=0, columnspan=2, sticky="nsew")
        encabezado_desc = tk.Frame(superior.interior, bg=BLANCO)
        encabezado_desc.pack(fill="x", padx=24, pady=(18, 8))
        self.boton_eliminar = tk.Button(
            encabezado_desc, text="Eliminar consulta", command=self.eliminar_consulta,
            bg="#F8ECEC", fg=ROJO_OSCURO, activebackground="#F1DDDE",
            activeforeground=ROJO_OSCURO, font=(FUENTE, 9, "bold"),
            relief="flat", bd=0, cursor="hand2", padx=14, pady=7
        )
        self.boton_eliminar.pack(side="right")

        self.titulo_descripcion = tk.Label(
            superior.interior, text="Descripción de la consulta", bg=BLANCO,
            fg=LETRA, font=(FUENTE, 16, "bold"), anchor="w", justify="left"
        )
        self.titulo_descripcion.pack(fill="x", padx=24, pady=(2, 6))
        self.texto_descripcion = tk.Label(
            superior.interior, text="Selecciona una consulta para ver el código y su resultado.",
            bg=BLANCO, fg=GRIS, font=(FUENTE, 10), anchor="nw",
            justify="left", wraplength=760
        )
        self.texto_descripcion.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        superior.interior.bind(
            "<Configure>", lambda e: self.texto_descripcion.configure(wraplength=max(400, e.width-55))
        )

        panel_codigo = Panel(trabajo)
        panel_codigo.grid(row=1, column=0, sticky="nsew", padx=(0, 9), pady=(16, 0))
        self.codigo = self._crear_editor(panel_codigo.interior, "Código de la consulta", self.copiar_codigo)
        self.codigo._es_codigo = True

        panel_resultado = Panel(trabajo)
        panel_resultado.grid(row=1, column=1, sticky="nsew", padx=(9, 0), pady=(16, 0))
        self.resultado = self._crear_editor(panel_resultado.interior, "Resultado de la consulta", self.copiar_resultado)
        self.resultado._es_codigo = False

    def _actualizar_botones(self):
        if not hasattr(self, "contenido_lateral"):
            return
        for boton in self.botones.values():
            boton.destroy()
        self.botones.clear()
        for consulta in self.consultas:
            numero = consulta["number"]
            titulo = consulta["title"]
            if len(titulo) > 39:
                titulo = titulo[:36].rstrip() + "…"
            seleccionado = numero == self.seleccion_actual
            boton = tk.Button(
                self.contenido_lateral,
                text=f"CONSULTA {numero:02d}\n{titulo}",
                font=(FUENTE, 10, "bold" if seleccionado else "normal"),
                fg=BLANCO,
                bg=AZUL_ACTIVO if seleccionado else "#C15E65",
                activebackground=AZUL_ACTIVO, activeforeground=BLANCO,
                relief="flat", bd=0, anchor="w", justify="left",
                padx=13, pady=8, cursor="hand2",
                command=lambda n=numero: self.seleccionar_consulta(n)
            )
            boton.pack(fill="x", padx=(2, 0), pady=(0, 7))
            self.botones[numero] = boton
        self.canvas_lateral.update_idletasks()
        self.canvas_lateral.configure(scrollregion=self.canvas_lateral.bbox("all"))
        if hasattr(self, "cuenta_consultas"):
            self.cuenta_consultas.configure(text=f"{len(self.consultas)} en total")

    def _crear_editor(self, padre, titulo, copiar, subtitulo=""):
        superior = tk.Frame(padre, bg=BLANCO)
        superior.pack(fill="x", padx=22, pady=(20, 14))
        tk.Label(superior, text=titulo, bg=BLANCO, fg=LETRA,
                 font=(FUENTE, 13, "bold"), anchor="w").pack(side="left")
        tk.Button(superior, text="Copiar", bg="#F1E3E8", fg=AZUL_ACTIVO,
                  activebackground="#E8D7DF", activeforeground=AZUL_ACTIVO,
                  relief="flat", bd=0, font=(FUENTE, 9, "bold"),
                  command=copiar, cursor="hand2", padx=14, pady=7
                  ).pack(side="right")
        linea = tk.Frame(padre, bg="#E8ECEF", height=1)
        linea.pack(fill="x", padx=22, pady=(0, 14))
        caja = tk.Frame(padre, bg="#D8DDE3", highlightbackground="#D8DDE3",
                        highlightthickness=1)
        caja.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        caja.grid_columnconfigure(0, weight=1)
        caja.grid_rowconfigure(0, weight=1)
        editor = tk.Text(
            caja, font=("Consolas", 10), bg="#F5F7FA", fg=LETRA,
            wrap="none", bd=0, relief="flat", padx=13, pady=13,
            insertbackground=LETRA, selectbackground="#E2C9D5",
            spacing1=2, spacing3=2
        )
        vertical = tk.Scrollbar(caja, command=editor.yview, orient="vertical",
                                relief="flat", bd=0)
        horizontal = tk.Scrollbar(caja, command=editor.xview, orient="horizontal",
                                  relief="flat", bd=0)
        editor.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        editor.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        editor.configure(state="disabled")
        return editor

    @staticmethod
    def _escribir(editor, contenido):
        editor.configure(state="normal")
        editor.delete("1.0", "end")
        editor.insert("1.0", contenido)
        # Sintaxis coloreada, únicamente visual.
        import re
        editor.tag_configure("cadena", foreground="#18704F")
        editor.tag_configure("operador", foreground="#874260")
        editor.tag_configure("numero", foreground="#A75B30")
        for etiqueta in ("cadena", "operador", "numero"):
            editor.tag_remove(etiqueta, "1.0", "end")
        for match in re.finditer(r'"(?:\\.|[^"\\])*"', contenido):
            ini = f"1.0+{match.start()}c"
            fin = f"1.0+{match.end()}c"
            etiqueta = "operador" if match.group().startswith('"$') else "cadena"
            editor.tag_add(etiqueta, ini, fin)
        for match in re.finditer(r'(?<![\w"])\b\d+(?:\.\d+)?\b', contenido):
            editor.tag_add("numero", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        editor.configure(state="disabled")
        editor.yview_moveto(0)
        editor.xview_moveto(0)

    def seleccionar_consulta(self, numero):
        consulta = next((q for q in self.consultas if q["number"] == numero), None)
        if consulta is None:
            return
        self.seleccion_actual = numero
        self.texto_descripcion.configure(text=consulta["descripcion"])
        self.titulo_descripcion.configure(text=consulta["title"])
        self._escribir(self.codigo, codigo_mongodb(consulta))
        self._escribir(self.resultado, "Ejecutando consulta en MongoDB...")
        for n, boton in self.botones.items():
            seleccionado = n == numero
            boton.configure(bg=AZUL_ACTIVO if seleccionado else "#C15E65",
                            font=(FUENTE, 10, "bold" if seleccionado else "normal"))
        self.folio += 1
        folio = self.folio
        hilo = threading.Thread(
            target=self._consultar,
            args=(copy.deepcopy(consulta), folio, self.uri, self.base_preferida),
            daemon=True
        )
        hilo.start()


def iniciar():
    ventana = tk.Tk()
    AplicacionAutos(ventana)
    ventana.mainloop()


if __name__ == "__main__":
    iniciar()
