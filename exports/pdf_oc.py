import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# ── Colores Mundotec ──────────────────────────────────────────────────────────
AZUL    = colors.HexColor("#1a3a5c")
AZUL_HD = colors.HexColor("#0033a0")
GRIS    = colors.HexColor("#F2F2F2")
NEGRO   = colors.black

LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo_mundotec.png')

# ── Proveedor fijo ────────────────────────────────────────────────────────────
PROVEEDOR = {
    "nombre":    "PART SCR SOCIEDAD ANONIMA",
    "direccion": "San Francisco Heredia, 100m Sur 350m Este Taco Bell, Casa #14",
    "telefono":  "",
    "correo":    "",
    "contacto":  "",
}

# ── Empresa emisora ───────────────────────────────────────────────────────────
EMPRESA = {
    "nombre":    "MUNDOTEC SOCIEDAD ANONIMA",
    "cedula":    "3-101-565688",
    "telefono":  "2460-2460",
    "correo":    "facturacompra@mundoteconline.com",
    "actividad": "4651.0",
    "direccion": "Entre Calle 1 y Avenida 3, Ciudad Quesada, San Carlos, Alajuela",
}


def exportar_oc_pdf(oc: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
        title=f"Orden de Compra {oc['no_oc']}"
    )

    styles  = getSampleStyleSheet()
    normal  = styles['Normal']
    estilo_empresa = ParagraphStyle("emp",   fontSize=14, textColor=AZUL_HD,
                                   fontName="Helvetica-Bold")
    estilo_sub     = ParagraphStyle("sub",   fontSize=8,  textColor=colors.grey)
    estilo_titulo  = ParagraphStyle("titulo",fontSize=16, textColor=AZUL,
                                   fontName="Helvetica-Bold", alignment=TA_CENTER)
    estilo_seccion = ParagraphStyle("sec",   fontSize=9,  textColor=AZUL,
                                   fontName="Helvetica-Bold")
    estilo_normal  = ParagraphStyle("nor",   fontSize=9)
    estilo_centro  = ParagraphStyle("cen",   fontSize=9,  alignment=TA_CENTER)
    estilo_pie     = ParagraphStyle("pie",   fontSize=8,  textColor=colors.grey,
                                   alignment=TA_CENTER)

    elems = []

    # ── Encabezado: logo + datos empresa + número OC ──────────────────────────
    logo_cell  = ""
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=4*cm, height=2*cm, kind='proportional')
        logo_cell = img

    empresa_txt = [
        Paragraph(EMPRESA["nombre"], estilo_empresa),
        Paragraph(EMPRESA["direccion"], estilo_sub),
    ]
    if EMPRESA.get("cedula"):
        empresa_txt.append(Paragraph(f'Cédula: {EMPRESA["cedula"]}', estilo_sub))
    if EMPRESA.get("actividad"):
        empresa_txt.append(Paragraph(f'Act. Económica: {EMPRESA["actividad"]}', estilo_sub))
    if EMPRESA.get("telefono"):
        empresa_txt.append(Paragraph(f'Tel: {EMPRESA["telefono"]}', estilo_sub))
    if EMPRESA.get("correo"):
        empresa_txt.append(Paragraph(f'E-mail: {EMPRESA["correo"]}', estilo_sub))

    oc_num_style = ParagraphStyle("ocnum", fontSize=14, fontName="Helvetica-Bold",
                                  textColor=AZUL, alignment=TA_RIGHT)
    oc_sub_style = ParagraphStyle("ocsub", fontSize=9, textColor=AZUL,
                                  alignment=TA_RIGHT)

    oc_info = [
        Paragraph("ORDEN DE COMPRA", oc_num_style),
        Paragraph(oc['no_oc'], ParagraphStyle("ocn2", fontSize=13,
                                              fontName="Helvetica-Bold",
                                              textColor=AZUL_HD, alignment=TA_RIGHT)),
        Paragraph(f'Fecha: {_fmt_fecha(oc["fecha"])}', oc_sub_style),
        Paragraph(f'Estado: {oc["estado"]}', oc_sub_style),
    ]

    hdr_table = Table(
        [[logo_cell, empresa_txt, oc_info]],
        colWidths=[4*cm, 9.5*cm, 4*cm]
    )
    hdr_table.setStyle(TableStyle([
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING',(0,0), (-1,-1), 4),
    ]))
    elems.append(hdr_table)
    elems.append(HRFlowable(width="100%", thickness=2, color=AZUL, spaceAfter=8))

    # ── Datos del proveedor ───────────────────────────────────────────────────
    elems.append(Paragraph("PROVEEDOR", estilo_seccion))
    elems.append(Spacer(1, 4))

    prov_data = [
        [Paragraph("<b>Nombre:</b>",    estilo_normal), Paragraph(PROVEEDOR["nombre"],    estilo_normal)],
        [Paragraph("<b>Dirección:</b>", estilo_normal), Paragraph(PROVEEDOR["direccion"], estilo_normal)],
    ]
    if PROVEEDOR.get("telefono"):
        prov_data.append([Paragraph("<b>Teléfono:</b>", estilo_normal),
                          Paragraph(PROVEEDOR["telefono"], estilo_normal)])
    if PROVEEDOR.get("correo"):
        prov_data.append([Paragraph("<b>Correo:</b>", estilo_normal),
                          Paragraph(PROVEEDOR["correo"], estilo_normal)])
    if PROVEEDOR.get("contacto"):
        prov_data.append([Paragraph("<b>Contacto:</b>", estilo_normal),
                          Paragraph(PROVEEDOR["contacto"], estilo_normal)])

    prov_table = Table(prov_data, colWidths=[3*cm, 14.5*cm])
    prov_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GRIS),
        ('GRID',       (0,0), (-1,-1), 0.3, colors.lightgrey),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GRIS, colors.white]),
    ]))
    elems.append(prov_table)
    elems.append(Spacer(1, 12))

    # ── Detalle de líneas ─────────────────────────────────────────────────────
    elems.append(Paragraph("DETALLE DE LA ORDEN", estilo_seccion))
    elems.append(Spacer(1, 4))

    lineas = oc.get('lineas', [])
    det_data = [[
        Paragraph("#",          ParagraphStyle("h", fontSize=9, fontName="Helvetica-Bold", alignment=TA_CENTER)),
        Paragraph("Detalle",    ParagraphStyle("h", fontSize=9, fontName="Helvetica-Bold")),
        Paragraph("Cantidad",   ParagraphStyle("h", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
    ]]
    for ln in lineas:
        cant = str(int(ln['cantidad'])) if ln.get('cantidad') and ln['cantidad'] == int(ln['cantidad']) \
               else (str(ln['cantidad']) if ln.get('cantidad') else "")
        det_data.append([
            Paragraph(str(ln['linea']), estilo_centro),
            Paragraph(ln['detalle'],    estilo_normal),
            Paragraph(cant,             ParagraphStyle("r", fontSize=9, alignment=TA_RIGHT)),
        ])

    if not lineas:
        det_data.append([Paragraph("", estilo_normal),
                         Paragraph("(sin líneas)", ParagraphStyle("gl", fontSize=9, textColor=colors.grey)),
                         Paragraph("", estilo_normal)])

    det_table = Table(det_data, colWidths=[1*cm, 14.5*cm, 2*cm])
    det_table.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),  (-1,0),  AZUL),
        ('TEXTCOLOR',   (0,0),  (-1,0),  colors.white),
        ('GRID',        (0,0),  (-1,-1), 0.3, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRIS]),
        ('FONTSIZE',    (0,0),  (-1,-1), 9),
        ('VALIGN',      (0,0),  (-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0),  (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
    ]))
    elems.append(det_table)
    elems.append(Spacer(1, 12))

    # ── Observaciones ─────────────────────────────────────────────────────────
    if oc.get('observaciones') and oc['observaciones'].strip():
        elems.append(Paragraph("OBSERVACIONES", estilo_seccion))
        elems.append(Spacer(1, 4))
        obs_table = Table(
            [[Paragraph(oc['observaciones'], estilo_normal)]],
            colWidths=[17.5*cm]
        )
        obs_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fffbe6')),
            ('GRID',       (0,0), (-1,-1), 0.3, colors.HexColor('#f0c040')),
            ('LEFTPADDING',(0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ]))
        elems.append(obs_table)
        elems.append(Spacer(1, 16))

    # ── Firmas ────────────────────────────────────────────────────────────────
    firma_data = [[
        Paragraph("_______________________\nElaborado por", estilo_centro),
        Paragraph("_______________________\nAutorizado por", estilo_centro),
        Paragraph("_______________________\nRecibido / Proveedor", estilo_centro),
    ]]
    firma_table = Table(firma_data, colWidths=[5.8*cm, 5.8*cm, 5.8*cm])
    firma_table.setStyle(TableStyle([
        ('VALIGN',   (0,0), (-1,-1), 'TOP'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 20),
    ]))
    elems.append(Spacer(1, 20))
    elems.append(firma_table)

    # ── Pie de página ─────────────────────────────────────────────────────────
    elems.append(Spacer(1, 12))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elems.append(Spacer(1, 4))
    elems.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} · {EMPRESA['nombre']} · {oc['no_oc']}",
        estilo_pie
    ))

    doc.build(elems)
    return buf.getvalue()


def _fmt_fecha(f: str) -> str:
    try:
        return datetime.strptime(f[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        return f
