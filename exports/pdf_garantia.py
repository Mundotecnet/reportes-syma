import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import EMPRESA_NOMBRE

# ── Registrar fuentes DejaVu (soporte Unicode completo, incluye ₡) ──────────
_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
try:
    pdfmetrics.registerFont(TTFont("DejaVu",      f"{_FONT_DIR}/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{_FONT_DIR}/DejaVuSans-Bold.ttf"))
    FONT_NORMAL = "DejaVu"
    FONT_BOLD   = "DejaVu-Bold"
except Exception:
    FONT_NORMAL = "Helvetica"
    FONT_BOLD   = "Helvetica-Bold"

AZUL     = colors.HexColor("#1E4E8C")
AZUL_CLR = colors.HexColor("#EEF4FF")
VERDE    = colors.HexColor("#27ae60")
GRIS     = colors.HexColor("#F4F6FB")
BORDE    = colors.HexColor("#CCCCCC")

ESTADO_COLOR = {
    'Nuevo':    colors.HexColor("#6c757d"),
    'Proceso':  colors.HexColor("#e67e22"),
    'Enviado':  colors.HexColor("#2980b9"),
    'Resuelto': colors.HexColor("#27ae60"),
}


def exportar_garantia_pdf(g: dict, notas: list) -> bytes:
    """
    Genera el PDF del informe de garantía.
    g    → dict con todos los campos de M_GARANTIAS + datos de ORDEN_SERVICIO
    notas → lista de dicts de M_GARANTIAS_BITACORA
    """
    buf    = io.BytesIO()
    styles = getSampleStyleSheet()

    # Estilos personalizados
    s_empresa = ParagraphStyle("emp", fontSize=14, textColor=AZUL,
                                fontName=FONT_BOLD, alignment=TA_CENTER)
    s_titulo  = ParagraphStyle("tit", fontSize=12, fontName=FONT_BOLD,
                                alignment=TA_CENTER, spaceAfter=2)
    s_sub     = ParagraphStyle("sub", fontSize=8, textColor=colors.grey,
                                fontName=FONT_NORMAL, alignment=TA_CENTER, spaceAfter=6)
    s_seccion = ParagraphStyle("sec", fontSize=9, fontName=FONT_BOLD,
                                textColor=AZUL, spaceBefore=10, spaceAfter=4)
    s_normal  = ParagraphStyle("nor", fontSize=8, leading=12, fontName=FONT_NORMAL)
    s_nota    = ParagraphStyle("not", fontSize=8, leading=11, leftIndent=6, fontName=FONT_NORMAL)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=f"Informe Garantía Orden #{g['no_orden']}"
    )

    elems = []

    # ── Encabezado ──────────────────────────────────────────────
    elems += [
        Paragraph(EMPRESA_NOMBRE, s_empresa),
        Spacer(1, 3),
        Paragraph(f"INFORME DE GARANTÍA — Orden #{g['no_orden']}", s_titulo),
        Paragraph(
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  "
            f"Estado: {g['estado']}",
            s_sub
        ),
        HRFlowable(width="100%", thickness=1.5, color=AZUL, spaceAfter=8),
    ]

    # ── Datos del equipo ────────────────────────────────────────
    elems.append(Paragraph("DATOS DEL EQUIPO / CLIENTE", s_seccion))
    datos_eq = [
        ["Cliente",    g['nombre_cliente'] or "—",
         "Fecha Ingreso", g['fecha_registro'] or "—"],
        ["Máquina",    g['maquina'] or "—",
         "Marca",      g['marca'] or "—"],
        ["Modelo",     g['modelo'] or "—",
         "N° Serie",   g['serie'] or "—"],
        ["Problema reportado", Paragraph(g['no_trae'] or "—", s_normal), "", ""],
    ]
    t_eq = Table(datos_eq, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
    t_eq.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), FONT_NORMAL),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("FONTNAME",    (0, 0), (0, -1),  FONT_BOLD),
        ("FONTNAME",    (2, 0), (2, -1),  FONT_BOLD),
        ("BACKGROUND",  (0, 0), (-1, -1), GRIS),
        ("GRID",        (0, 0), (-1, -1), 0.3, BORDE),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0), (-1, -1), 4),
        ("SPAN",        (1, 3), (3, 3)),
    ]))
    elems += [t_eq, Spacer(1, 8)]

    # ── Pasos del proceso ───────────────────────────────────────
    elems.append(Paragraph("PROCESO DE GARANTÍA", s_seccion))

    def check(val):
        return "✓  Completado" if val else "—  Pendiente"

    pasos = [
        ["PASO", "DETALLE", "FECHA", "ESTADO"],
        ["Boleta Taller",
         f"Orden #{g['no_orden']}",
         g['fecha_registro'] or "—",
         "✓  Completado"],
        ["Factura Compra",
         g['no_fact_compra'] or "—",
         g['fecha_fact_compra'] or "—",
         check(g['no_fact_compra'])],
        ["Factura Venta",
         g['no_fact_venta'] or "—",
         g['fecha_fact_venta'] or "—",
         check(g['no_fact_venta'])],
        ["Guía de Envío",
         f"{g['no_guia'] or '—'}  {('/ ' + g['transportista']) if g['transportista'] else ''}",
         g['fecha_envio'] or "—",
         check(g['no_guia'])],
        ["Resolución",
         Paragraph(g['resolucion'] or "—", s_normal),
         g['fecha_resolucion'] or "—",
         check(g['resolucion'])],
    ]
    t_pasos = Table(pasos, colWidths=[3.5*cm, 7*cm, 3*cm, 4.5*cm])
    t_pasos.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), FONT_NORMAL),
        ("BACKGROUND",    (0, 0), (-1, 0),  AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  FONT_BOLD),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        # Color verde en "Completado"
        ("TEXTCOLOR",     (3, 1), (3, 1),   VERDE),
        ("TEXTCOLOR",     (3, 2), (3, 2),   VERDE if g['no_fact_compra'] else colors.grey),
        ("TEXTCOLOR",     (3, 3), (3, 3),   VERDE if g['no_fact_venta']  else colors.grey),
        ("TEXTCOLOR",     (3, 4), (3, 4),   VERDE if g['no_guia']        else colors.grey),
        ("TEXTCOLOR",     (3, 5), (3, 5),   VERDE if g['resolucion']     else colors.grey),
    ]))
    elems += [t_pasos, Spacer(1, 8)]

    # ── Notas / bitácora ────────────────────────────────────────
    if notas:
        elems.append(Paragraph("BITÁCORA DE SEGUIMIENTO", s_seccion))
        bit_data = [["FECHA", "USUARIO", "DETALLE"]]
        for n in notas:
            bit_data.append([
                n.get('fecha', '')[:16],
                n.get('usuario', '—'),
                Paragraph(n.get('detalle', ''), s_nota),
            ])
        t_bit = Table(bit_data, colWidths=[3.5*cm, 2.5*cm, 12*cm])
        t_bit.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), FONT_NORMAL),
            ("BACKGROUND",    (0, 0), (-1, 0),  AZUL),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  FONT_BOLD),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, GRIS]),
            ("GRID",          (0, 0), (-1, -1), 0.3, BORDE),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elems.append(t_bit)

    # ── Notas generales ─────────────────────────────────────────
    if g.get('notas'):
        elems += [
            Spacer(1, 8),
            Paragraph("NOTAS GENERALES", s_seccion),
            Paragraph(g['notas'], s_normal),
        ]

    # ── Pie de página ───────────────────────────────────────────
    elems += [
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=0.5, color=BORDE),
        Paragraph(
            f"{EMPRESA_NOMBRE}  |  Informe generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            ParagraphStyle("pie", fontSize=7, textColor=colors.grey, alignment=TA_CENTER, fontName=FONT_NORMAL)
        ),
    ]

    doc.build(elems)
    return buf.getvalue()
