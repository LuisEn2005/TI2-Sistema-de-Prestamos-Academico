"""Renderiza la estructura de un reporte a un PDF (bytes) con fpdf2.

Usa las fuentes núcleo (Helvetica), que codifican en latin-1; el texto se sanea a
ese juego para no fallar con caracteres fuera de rango."""

from datetime import timezone
from zoneinfo import ZoneInfo

from fpdf import FPDF

_LIMA = ZoneInfo("America/Lima")

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
    return str(valor or "").encode("latin-1", "replace").decode("latin-1")


def generar_pdf(datos) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 7, _txt("Sistema de Préstamos - Escuela de Computación"),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    titulo = ("Reporte de acciones por usuario" if datos["tipo"] == "usuario"
              else "Reporte de acciones por recurso")
    pdf.multi_cell(0, 6, _txt(f"{titulo}: {datos['sujeto']}"),
                   new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    generado = datos["generado_en"]
    if generado.tzinfo is None:
        generado = generado.replace(tzinfo=timezone.utc)
    generado_local = generado.astimezone(_LIMA).strftime("%Y-%m-%d %H:%M")
    pdf.multi_cell(0, 5, _txt(
        f"Rango: {datos['desde'].isoformat()} a {datos['hasta'].isoformat()}  "
        f"(máximo 90 días)"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5, _txt(
        f"Generado por {datos['generado_por'] or 'Sistema'} el {generado_local} "
        f"(America/Lima)"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Resumen
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 6, _txt("Resumen"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for clave, etiqueta in RESUMEN_ETIQUETAS:
        pdf.multi_cell(0, 5, _txt(f"  {etiqueta}: {datos['resumen'].get(clave, 0)}"),
                       new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Acciones
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 6, _txt("Detalle de acciones"), new_x="LMARGIN", new_y="NEXT")
    if not datos["acciones"]:
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _txt("No hay acciones registradas en este rango."),
                       new_x="LMARGIN", new_y="NEXT")
    for a in datos["acciones"]:
        pdf.set_font("Helvetica", "B", 9)
        cuando = a.fecha + (f" {a.hora}" if a.hora else "")
        pdf.multi_cell(0, 5, _txt(f"{cuando}  -  {a.accion}"),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        partes = [p for p in (a.item, a.responsable, a.detalle) if p]
        if partes:
            pdf.multi_cell(0, 5, _txt("     " + "   |   ".join(partes)),
                           new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    return bytes(pdf.output())
