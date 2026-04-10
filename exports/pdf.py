import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import EMPRESA_NOMBRE

# ── Registrar fuentes DejaVu (soporte Unicode completo, incluye ₡) ──────────
_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
try:
    pdfmetrics.registerFont(TTFont("DejaVu",     f"{_FONT_DIR}/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{_FONT_DIR}/DejaVuSans-Bold.ttf"))
    FONT_NORMAL = "DejaVu"
    FONT_BOLD   = "DejaVu-Bold"
except Exception:
    # Fallback a Helvetica si no están disponibles
    FONT_NORMAL = "Helvetica"
    FONT_BOLD   = "Helvetica-Bold"

AZUL  = colors.HexColor("#1E4E8C")
GRIS  = colors.HexColor("#F2F2F2")
NEGRO = colors.black

def _doc(buf, titulo):
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(letter),
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=titulo
    )
    return doc

def _encabezado(titulo, filtros_txt=""):
    styles = getSampleStyleSheet()
    empresa_style = ParagraphStyle("emp", fontSize=14, textColor=AZUL,
                                   alignment=TA_CENTER, fontName=FONT_BOLD)
    titulo_style  = ParagraphStyle("tit", fontSize=11,
                                   alignment=TA_CENTER, fontName=FONT_BOLD)
    sub_style     = ParagraphStyle("sub", fontSize=8, textColor=colors.grey,
                                   alignment=TA_CENTER, fontName=FONT_NORMAL)
    elems = [
        Paragraph(EMPRESA_NOMBRE, empresa_style),
        Spacer(1, 4),
        Paragraph(titulo, titulo_style),
        Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  {filtros_txt}", sub_style),
        Spacer(1, 10),
    ]
    return elems

def _tabla_style(num_cols, num_filas, fila_tot):
    cmds = [
        ("FONTNAME",    (0, 0), (-1, -1),          FONT_NORMAL),   # todas las filas → DejaVu
        ("BACKGROUND",  (0, 0), (-1, 0),          AZUL),
        ("TEXTCOLOR",   (0, 0), (-1, 0),          colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),          FONT_BOLD),      # encabezado → bold
        ("FONTSIZE",    (0, 0), (-1, -1),         8),
        ("ROWBACKGROUNDS", (0, 1), (-1, fila_tot-1), [colors.white, GRIS]),
        ("BACKGROUND",  (0, fila_tot), (-1, fila_tot), colors.HexColor("#DDEEFF")),
        ("FONTNAME",    (0, fila_tot), (-1, fila_tot), FONT_BOLD),  # fila totales → bold
        ("GRID",        (0, 0), (-1, -1),          0.3, colors.HexColor("#CCCCCC")),
        ("VALIGN",      (0, 0), (-1, -1),          "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1),          4),
        ("BOTTOMPADDING",(0,0), (-1, -1),          4),
    ]
    return TableStyle(cmds)

def _fmt(v):
    try:
        return f"₡{float(v):,.2f}"
    except:
        return str(v) if v else ""


def exportar_ventas_pdf(datos: list, titulo: str = "Reporte de Ventas",
                        filtros_txt: str = "") -> bytes:
    buf = io.BytesIO()
    doc = _doc(buf, titulo)
    elems = _encabezado(titulo, filtros_txt)

    cabecera = ["Nº Doc", "Fecha", "Tipo", "Cliente", "Cat.", "Vendedor",
                "Subtotal", "Desc.", "IVA", "Total"]

    tot_sub = tot_desc = tot_iva = tot_total = 0
    filas = [cabecera]
    for r in datos:
        filas.append([
            str(r.get("num_doc", "")),
            str(r.get("fecha", "")),
            str(r.get("tipo_venta", "")),
            str(r.get("cliente", ""))[:28],
            str(r.get("cat_cliente", "")),
            str(r.get("vendedor", ""))[:14],
            _fmt(r.get("subtotal", 0)),
            _fmt(r.get("descuento", 0)),
            _fmt(r.get("iva", 0)),
            _fmt(r.get("total", 0)),
        ])
        tot_sub   += r.get("subtotal", 0) or 0
        tot_desc  += r.get("descuento", 0) or 0
        tot_iva   += r.get("iva", 0) or 0
        tot_total += r.get("total", 0) or 0

    filas.append([
        f"TOTALES ({len(datos)})", "", "", "", "", "",
        _fmt(tot_sub), _fmt(tot_desc), _fmt(tot_iva), _fmt(tot_total)
    ])

    col_widths = [2*cm, 2.2*cm, 2*cm, 6*cm, 1.5*cm, 3.5*cm,
                  3*cm, 2.5*cm, 2.5*cm, 3*cm]
    t = Table(filas, colWidths=col_widths, repeatRows=1)
    t.setStyle(_tabla_style(10, len(filas), len(filas)-1))
    elems.append(t)

    doc.build(elems)
    buf.seek(0)
    return buf.read()


def exportar_pagos_pdf(datos: list, titulo: str = "Reporte de Pagos",
                       filtros_txt: str = "") -> bytes:
    buf = io.BytesIO()
    doc = _doc(buf, titulo)
    elems = _encabezado(titulo, filtros_txt)

    cabecera = ["Nº Doc", "Fecha", "Cliente", "Cédula",
                "Tipo Pago", "Monto", "Saldo Ant.", "Saldo Act.", "Aplicado"]

    tot_monto = tot_aplicado = 0
    filas = [cabecera]
    for r in datos:
        filas.append([
            str(r.get("num_doc", "")),
            str(r.get("fecha", "")),
            str(r.get("cliente", ""))[:30],
            str(r.get("cedula", "")),
            str(r.get("tipo_pago", "")),
            _fmt(r.get("monto", 0)),
            _fmt(r.get("saldo_anterior", 0)),
            _fmt(r.get("saldo_actual", 0)),
            _fmt(r.get("monto_aplicado", 0)),
        ])
        tot_monto    += r.get("monto", 0) or 0
        tot_aplicado += r.get("monto_aplicado", 0) or 0

    filas.append([
        f"TOTALES ({len(datos)})", "", "", "", "",
        _fmt(tot_monto), "", "", _fmt(tot_aplicado)
    ])

    col_widths = [2*cm, 2.2*cm, 6.5*cm, 3*cm, 3*cm, 3*cm, 3*cm, 3*cm, 3*cm]
    t = Table(filas, colWidths=col_widths, repeatRows=1)
    t.setStyle(_tabla_style(9, len(filas), len(filas)-1))
    elems.append(t)

    doc.build(elems)
    buf.seek(0)
    return buf.read()


def exportar_productos_pdf(datos: list, titulo: str = "Productos Vendidos",
                           filtros_txt: str = "") -> bytes:
    buf = io.BytesIO()
    doc = _doc(buf, titulo)
    elems = _encabezado(titulo, filtros_txt)

    cabecera = ["Código", "Descripción", "Unidad",
                "Cantidad", "Subtotal", "Desc.", "IVA", "Total"]

    tot_cant = tot_sub = tot_desc = tot_iva = tot_total = 0
    filas = [cabecera]
    for r in datos:
        cant = r.get("cantidad", 0) or 0
        filas.append([
            str(r.get("codigo", "") or ""),
            str(r.get("descripcion", ""))[:35],
            str(r.get("unidad", "") or ""),
            f"{float(cant):,.2f}",
            _fmt(r.get("subtotal",  0)),
            _fmt(r.get("descuento", 0)),
            _fmt(r.get("iva",       0)),
            _fmt(r.get("total",     0)),
        ])
        tot_cant  += float(cant)
        tot_sub   += r.get("subtotal",  0) or 0
        tot_desc  += r.get("descuento", 0) or 0
        tot_iva   += r.get("iva",       0) or 0
        tot_total += r.get("total",     0) or 0

    filas.append([
        f"TOTALES ({len(datos)})", "", "",
        f"{tot_cant:,.2f}",
        _fmt(tot_sub), _fmt(tot_desc), _fmt(tot_iva), _fmt(tot_total)
    ])

    col_widths = [2.5*cm, 8*cm, 1.8*cm, 2.2*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm]
    t = Table(filas, colWidths=col_widths, repeatRows=1)
    t.setStyle(_tabla_style(8, len(filas), len(filas)-1))
    elems.append(t)

    doc.build(elems)
    buf.seek(0)
    return buf.read()


def exportar_compras_pdf(datos: list, titulo: str = "Reporte de Compras",
                         filtros_txt: str = "") -> bytes:
    buf = io.BytesIO()
    doc = _doc(buf, titulo)
    elems = _encabezado(titulo, filtros_txt)

    cabecera = ["Nº Doc", "Fecha", "Proveedor", "Cédula",
                "Factura Prov.", "Subtotal", "Desc.", "IVA", "Total", "Estado"]

    tot_sub = tot_desc = tot_iva = tot_total = 0
    filas = [cabecera]
    for r in datos:
        filas.append([
            str(r.get("num_doc", "")),
            str(r.get("fecha", "")),
            str(r.get("proveedor", ""))[:28],
            str(r.get("cedula", "")),
            str(r.get("factura_proveedor", "")),
            _fmt(r.get("subtotal", 0)),
            _fmt(r.get("descuento", 0)),
            _fmt(r.get("iva", 0)),
            _fmt(r.get("total", 0)),
            str(r.get("estado", "")),
        ])
        tot_sub   += r.get("subtotal", 0) or 0
        tot_desc  += r.get("descuento", 0) or 0
        tot_iva   += r.get("iva", 0) or 0
        tot_total += r.get("total", 0) or 0

    filas.append([
        f"TOTALES ({len(datos)})", "", "", "", "",
        _fmt(tot_sub), _fmt(tot_desc), _fmt(tot_iva), _fmt(tot_total), ""
    ])

    col_widths = [2*cm, 2.2*cm, 6*cm, 3*cm, 3*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm, 2*cm]
    t = Table(filas, colWidths=col_widths, repeatRows=1)
    t.setStyle(_tabla_style(10, len(filas), len(filas)-1))
    elems.append(t)

    doc.build(elems)
    buf.seek(0)
    return buf.read()


def exportar_cxc_pdf(datos: list, titulo: str = "Cuentas por Cobrar",
                     filtros_txt: str = "") -> bytes:
    buf = io.BytesIO()
    doc = _doc(buf, titulo)
    elems = _encabezado(titulo, filtros_txt)

    cabecera = ["Código", "Cliente", "Cédula", "Categoría", "Saldo"]

    tot_saldo = 0
    filas = [cabecera]
    for r in datos:
        saldo = r.get("saldo", 0) or 0
        filas.append([
            str(r.get("codigo", "")),
            str(r.get("cliente", ""))[:38],
            str(r.get("cedula", "")),
            str(r.get("desc_categoria") or r.get("categoria", "")),
            _fmt(saldo),
        ])
        tot_saldo += saldo

    filas.append([
        f"TOTAL ({len(datos)} clientes)", "", "", "", _fmt(tot_saldo)
    ])

    col_widths = [2*cm, 9*cm, 4*cm, 3.5*cm, 3.5*cm]
    t = Table(filas, colWidths=col_widths, repeatRows=1)
    t.setStyle(_tabla_style(5, len(filas), len(filas)-1))
    elems.append(t)

    doc.build(elems)
    buf.seek(0)
    return buf.read()


def exportar_boleta_pdf(orden: dict) -> bytes:
    """Genera la boleta de orden de servicio en formato A4 portrait."""
    W = 17 * cm   # ancho útil (A4 21cm − 2cm*2 márgenes)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Orden de Servicio #{orden.get('no_orden','')}",
    )

    s_emp  = ParagraphStyle("emp",  fontSize=14, textColor=AZUL, alignment=TA_CENTER, fontName=FONT_BOLD)
    s_tit  = ParagraphStyle("tit",  fontSize=11, alignment=TA_CENTER, fontName=FONT_BOLD)
    s_sec  = ParagraphStyle("sec",  fontSize=9,  textColor=colors.white, fontName=FONT_BOLD, leftIndent=5)
    s_lbl  = ParagraphStyle("lbl",  fontSize=7,  textColor=colors.HexColor("#666666"), fontName=FONT_NORMAL)
    s_val  = ParagraphStyle("val",  fontSize=9,  fontName=FONT_NORMAL)
    s_nord = ParagraphStyle("nord", fontSize=18, textColor=AZUL, fontName=FONT_BOLD, alignment=TA_CENTER)
    s_fir  = ParagraphStyle("fir",  fontSize=8,  alignment=TA_CENTER, fontName=FONT_NORMAL)
    s_flbl = ParagraphStyle("flbl", fontSize=8,  textColor=colors.grey, alignment=TA_CENTER, fontName=FONT_NORMAL)
    s_foot = ParagraphStyle("foot", fontSize=7,  textColor=colors.grey, alignment=TA_CENTER, fontName=FONT_NORMAL)

    def v(key):
        return str(orden.get(key) or "—")

    def seccion(titulo):
        t = Table([[Paragraph(titulo, s_sec)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), AZUL),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        return t

    BASE = [
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#DDDDDD")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
    ]

    elems = []

    # ── Encabezado ────────────────────────────────────────
    elems += [
        Paragraph(EMPRESA_NOMBRE, s_emp),
        Spacer(1, 4),
        Paragraph("ORDEN DE SERVICIO", s_tit),
        Spacer(1, 10),
    ]

    # Número de orden + fecha + tipo + ubicación
    hdr = Table([[
        Paragraph("N° ORDEN", s_lbl),
        Paragraph(v("no_orden"), s_nord),
        Paragraph("FECHA", s_lbl),
        Paragraph(v("fecha"), s_val),
        Paragraph("TIPO", s_lbl),
        Paragraph(v("tipo"), s_val),
        Paragraph("UBICACIÓN", s_lbl),
        Paragraph(v("ubicacion"), s_val),
    ]], colWidths=[2*cm, 2.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 2.5*cm, 2*cm, 2.5*cm])
    hdr.setStyle(TableStyle(BASE))
    elems += [hdr, Spacer(1, 8)]

    # ── Equipo ────────────────────────────────────────────
    elems.append(seccion("EQUIPO"))
    eq = Table([
        [Paragraph("Equipo / Máquina", s_lbl),
         Paragraph(v("maquina"), s_val),
         Paragraph("Marca", s_lbl),
         Paragraph(v("marca"), s_val),
         Paragraph("Modelo", s_lbl),
         Paragraph(v("modelo"), s_val),
         Paragraph("Serie", s_lbl),
         Paragraph(v("serie"), s_val)],
        [Paragraph("Accesorios", s_lbl),
         Paragraph(v("accesorios"), s_val),
         Paragraph("Estado al ingresar", s_lbl),
         Paragraph(v("estado_ingreso"), s_val),
         "", "", "", ""],
        [Paragraph("Problema / Observaciones", s_lbl),
         Paragraph(v("observaciones"), s_val),
         "", "", "", "", "", ""],
    ], colWidths=[3*cm, 3.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 1*cm])
    eq.setStyle(TableStyle([
        *BASE,
        ("SPAN", (3,1), (7,1)),
        ("SPAN", (1,2), (7,2)),
    ]))
    elems += [eq, Spacer(1, 8)]

    # ── Cliente ───────────────────────────────────────────
    elems.append(seccion("CLIENTE"))
    cli = Table([
        [Paragraph("Nombre", s_lbl),
         Paragraph(v("nombre_cliente"), s_val),
         Paragraph("Cédula", s_lbl),
         Paragraph(v("cedula"), s_val),
         Paragraph("Teléfono", s_lbl),
         Paragraph(v("telefono"), s_val)],
        [Paragraph("Correo electrónico", s_lbl),
         Paragraph(v("correo"), s_val),
         "", "", "", ""],
    ], colWidths=[2.5*cm, 5.5*cm, 2*cm, 2.5*cm, 2*cm, 2.5*cm])
    cli.setStyle(TableStyle([
        *BASE,
        ("SPAN", (1,1), (5,1)),
    ]))
    elems += [cli, Spacer(1, 8)]

    # ── Agenda ────────────────────────────────────────────
    elems.append(seccion("AGENDA"))
    agenda = Table([[
        Paragraph("Hora entrada", s_lbl),
        Paragraph(v("hora_entrada"), s_val),
        Paragraph("Hora salida est.", s_lbl),
        Paragraph(v("hora_salida"), s_val),
        Paragraph("Técnico asignado", s_lbl),
        Paragraph(v("reparador"), s_val),
    ]], colWidths=[2.5*cm, 3*cm, 2.5*cm, 3*cm, 3*cm, 3*cm])
    agenda.setStyle(TableStyle(BASE))
    elems += [agenda, Spacer(1, 30)]

    # ── Firmas ───────────────────────────────────────────
    firmas = Table([
        [Paragraph("_" * 26, s_fir),
         Paragraph("_" * 26, s_fir),
         Paragraph("_" * 26, s_fir)],
        [Paragraph("Entregado por", s_flbl),
         Paragraph("Técnico responsable", s_flbl),
         Paragraph("Autorizado por", s_flbl)],
    ], colWidths=[W/3, W/3, W/3])
    firmas.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    elems += [firmas, Spacer(1, 12)]

    # ── Pie ──────────────────────────────────────────────
    elems.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  {EMPRESA_NOMBRE}",
        s_foot,
    ))

    doc.build(elems)
    buf.seek(0)
    return buf.read()
