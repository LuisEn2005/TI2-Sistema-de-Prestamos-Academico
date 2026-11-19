"""Renderiza la estructura de un reporte a un PDF (bytes) con fpdf2.

Usa las fuentes núcleo (Helvetica), que codifican en latin-1; el texto se sanea a
ese juego para no fallar con caracteres fuera de rango. El diseño es discreto y
basado en texto: sin recuadros, con líneas finas, acentos ámbar y detalles
redondeados sutiles, en línea con la estética de la aplicación."""

from datetime import timezone
from zoneinfo import ZoneInfo

from fpdf import FPDF, FontFace

_LIMA = ZoneInfo("America/Lima")

# Paleta "Cálida académica" (RGB).
NAVY = (34, 48, 78)
AMBAR = (179, 121, 27)
AMBAR_FUERTE = (147, 95, 18)
LINEA = (227, 215, 196)
TENUE = (122, 114, 98)
FONDO_ENCABEZADO = (246, 239, 226)

RESUMEN_ETIQUETAS = [
    ("total", "Acciones en total"),
    ("reservas_solicitadas", "Reservas solicitadas"),
    ("reservas_confirmadas", "Reservas confirmadas"),
    ("prestamos_entregados", "Préstamos entregados"),
    ("devoluciones_a_tiempo", "Devoluciones a tiempo"),
    ("devoluciones_tarde", "Devoluciones con atraso"),
    ("sanciones_aplicadas", "Sanciones aplicadas"),
    ("sanciones_cerradas", "Sanciones cerradas"),
]


def _txt(valor):
    """Deja el texto en el juego latin-1 que admiten las fuentes núcleo."""
    texto = str(valor or "").replace("—", "-").replace("→", "->")
    return texto.encode("latin-1", "replace").decode("latin-1")


class _Reporte(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*LINEA)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*TENUE)
        self.cell(0, 5, _txt("Sistema de Préstamos · Escuela de Ciencia de la Computación"))
        self.cell(0, 5, _txt(f"Página {self.page_no()}"), align="R")


def _regla(pdf, grosor=0.2, color=LINEA, margen=0.0):
    pdf.set_draw_color(*color)
    pdf.set_line_width(grosor)
    y = pdf.get_y()
    pdf.line(pdf.l_margin + margen, y, pdf.w - pdf.r_margin - margen, y)


def _encabezado(pdf, datos):
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, _txt("Sistema de Préstamos · Escuela de Ciencia de la Computación"),
             new_x="LMARGIN", new_y="NEXT")
    titulo = ("Reporte de acciones por usuario" if datos["tipo"] == "usuario"
              else "Reporte de acciones por recurso")
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*TENUE)
    pdf.cell(0, 6, _txt(f"{titulo}:  {datos['sujeto']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2.5)
    _regla(pdf, 0.6, AMBAR)      # Hairline ámbar bajo el título.
    pdf.ln(4)


def _linea_meta(pdf, texto):
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TENUE)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 4.8, _txt(texto), new_x="LMARGIN", new_y="NEXT")


def _titulo_seccion(pdf, texto):
    pdf.ln(4)
    y = pdf.get_y()
    pdf.set_fill_color(*AMBAR)
    pdf.ellipse(pdf.l_margin + 0.3, y + 1.6, 2.2, 2.2, style="F")   # Punto redondeado.
    pdf.set_x(pdf.l_margin + 5)
    pdf.set_font("Helvetica", "B", 11.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, _txt(texto), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _resumen(pdf, resumen):
    """Dos columnas de texto: número ámbar + etiqueta, sin recuadros."""
    colw = pdf.epw / 2
    numw = 11
    fila_h = 7
    y = pdf.get_y()
    for i, (clave, etiqueta) in enumerate(RESUMEN_ETIQUETAS):
        col = i % 2
        if col == 0:
            y = pdf.get_y()
        pdf.set_xy(pdf.l_margin + col * colw, y)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*AMBAR_FUERTE)
        pdf.cell(numw, fila_h, _txt(str(resumen.get(clave, 0))), align="R")
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*TENUE)
        pdf.cell(colw - numw - 6, fila_h, _txt("   " + etiqueta))
        if col == 1:
            pdf.ln(fila_h)


TIPO = {"RESERVA": "Reserva", "PRESTAMO": "Préstamo", "SANCION": "Sanción"}


def _tabla(pdf, acciones, tipo):
    """Tabla de acciones con líneas horizontales finas; repite el encabezado en cada página."""
    quinta = ("Recurso", lambda a: a.item) if tipo == "usuario" else ("Usuario", lambda a: a.usuario)
    columnas = [
        ("Fecha", 17, lambda a: a.fecha),
        ("Hora", 10, lambda a: a.hora),
        ("Tipo", 15, lambda a: TIPO.get(a.categoria, a.categoria)),
        ("Acción", 30, lambda a: a.accion),
        (quinta[0], 22, quinta[1]),
        ("Responsable", 24, lambda a: a.responsable),
        ("Detalle", 56, lambda a: a.detalle),
    ]
    pdf.set_draw_color(*LINEA)
    pdf.set_fill_color(255, 255, 255)   # _titulo_seccion deja el relleno en ámbar.
    pdf.set_line_width(0.15)
    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "", 7.8)
    encabezado = FontFace(emphasis="BOLD", color=NAVY, fill_color=FONDO_ENCABEZADO)
    with pdf.table(col_widths=[c[1] for c in columnas], headings_style=encabezado,
                   borders_layout="HORIZONTAL_LINES", line_height=4.2, padding=1.2,
                   text_align="LEFT", first_row_as_headings=True) as t:
        fila = t.row()
        for nombre, _, _ in columnas:
            fila.cell(_txt(nombre))
        for a in acciones:
            fila = t.row()
            for _, _, valor in columnas:
                fila.cell(_txt(valor(a) or "—"))


def generar_pdf(datos) -> bytes:
    pdf = _Reporte(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()

    _encabezado(pdf, datos)

    _linea_meta(pdf, f"Rango: {datos['desde'].isoformat()} a {datos['hasta'].isoformat()}")
    generado = datos["generado_en"]
    if generado.tzinfo is None:
        generado = generado.replace(tzinfo=timezone.utc)
    generado_local = generado.astimezone(_LIMA).strftime("%Y-%m-%d %H:%M")
    _linea_meta(pdf, f"Generado por {datos['generado_por'] or 'Sistema'} el {generado_local}")

    _titulo_seccion(pdf, "Resumen")
    _resumen(pdf, datos["resumen"])

    _titulo_seccion(pdf, "Detalle de acciones")
    if not datos["acciones"]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*TENUE)
        pdf.multi_cell(0, 5, _txt("No hay acciones registradas en este rango."),
                       new_x="LMARGIN", new_y="NEXT")
    else:
        _tabla(pdf, datos["acciones"], datos["tipo"])

    return bytes(pdf.output())
