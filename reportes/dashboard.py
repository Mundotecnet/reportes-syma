from db import ejecutar_query


def get_dashboard_periodo(fecha_ini: str, fecha_fin: str) -> dict:
    """
    Métricas consolidadas del período: ventas, compras, bienes/servicios, recuperación.
    """
    resultado = {}

    # ── Ventas (contado + crédito) ────────────────────────────────────────────
    try:
        rows = ejecutar_query("""
            SELECT
                SUM(CASE WHEN ID_CONCEPTO='01' THEN ISNULL(TOTAL,0) ELSE 0 END) AS ventas_contado,
                SUM(CASE WHEN ID_CONCEPTO='02' THEN ISNULL(TOTAL,0) ELSE 0 END) AS ventas_credito,
                SUM(ISNULL(TOTAL,0))                                             AS ventas_total,
                COUNT(CASE WHEN ID_CONCEPTO='01' THEN 1 END)                     AS docs_contado,
                COUNT(CASE WHEN ID_CONCEPTO='02' THEN 1 END)                     AS docs_credito,
                COUNT(*)                                                          AS docs_total
            FROM PUNTO_VENTA
            WHERE CAST(FECHA AS date) BETWEEN ? AND ?
              AND ESTADO = 'A'
        """, (fecha_ini, fecha_fin))
        r = rows[0] if rows else {}
        resultado.update({
            "ventas_contado": float(r.get("ventas_contado") or 0),
            "ventas_credito": float(r.get("ventas_credito") or 0),
            "ventas_total":   float(r.get("ventas_total")   or 0),
            "docs_contado":   int(r.get("docs_contado")     or 0),
            "docs_credito":   int(r.get("docs_credito")     or 0),
            "docs_total":     int(r.get("docs_total")       or 0),
        })
    except Exception as e:
        print(f"[Dashboard ventas] {e}")
        resultado.update({"ventas_contado":0,"ventas_credito":0,"ventas_total":0,
                          "docs_contado":0,"docs_credito":0,"docs_total":0})

    # ── Compras (CRC y USD) ───────────────────────────────────────────────────
    try:
        rows = ejecutar_query("""
            SELECT
                SUM(CASE WHEN ISNULL(ID_MONEDA,'CRC')='CRC'
                         THEN ISNULL(TOTAL,0) ELSE 0 END)  AS compras_crc,
                SUM(CASE WHEN ISNULL(ID_MONEDA,'CRC')<>'CRC'
                         THEN ISNULL(TOTAL,0) ELSE 0 END)  AS compras_usd,
                COUNT(CASE WHEN ISNULL(ID_MONEDA,'CRC')='CRC'  THEN 1 END) AS docs_crc,
                COUNT(CASE WHEN ISNULL(ID_MONEDA,'CRC')<>'CRC' THEN 1 END) AS docs_usd
            FROM COMPRAS
            WHERE CAST(FECHA AS date) BETWEEN ? AND ?
              AND ESTADO = 'A'
        """, (fecha_ini, fecha_fin))
        r = rows[0] if rows else {}
        resultado.update({
            "compras_crc": float(r.get("compras_crc") or 0),
            "compras_usd": float(r.get("compras_usd") or 0),
            "docs_crc":    int(r.get("docs_crc")      or 0),
            "docs_usd":    int(r.get("docs_usd")      or 0),
        })
    except Exception as e:
        print(f"[Dashboard compras] {e}")
        resultado.update({"compras_crc":0,"compras_usd":0,"docs_crc":0,"docs_usd":0})

    # ── Bienes y Servicios vendidos ───────────────────────────────────────────
    try:
        rows = ejecutar_query("""
            SELECT
                SUM(CASE WHEN ISNULL(p.IND_BIEN_SERVICIO,0)=0
                         THEN ISNULL(pvd.IMPORTE,0)+ISNULL(pvd.MONTO_IMP,0) ELSE 0 END) AS total_bienes,
                SUM(CASE WHEN ISNULL(p.IND_BIEN_SERVICIO,0)=1
                         THEN ISNULL(pvd.IMPORTE,0)+ISNULL(pvd.MONTO_IMP,0) ELSE 0 END) AS total_servicios
            FROM PUNTO_VENTA_DETALLE pvd
            INNER JOIN PUNTO_VENTA pv
                ON  pv.ID_DOCUMENTO = pvd.ID_DOCUMENTO
                AND pv.ID_TIPODOC   = pvd.ID_TIPODOC
                AND pv.ID_CONCEPTO  = pvd.ID_CONCEPTO
            LEFT JOIN PRODUCTOS p ON p.CODIGO_ID = pvd.CODIGO_ID
            WHERE CAST(pv.FECHA AS date) BETWEEN ? AND ?
              AND pv.ESTADO = 'A'
        """, (fecha_ini, fecha_fin))
        r = rows[0] if rows else {}
        resultado.update({
            "total_bienes":    float(r.get("total_bienes")    or 0),
            "total_servicios": float(r.get("total_servicios") or 0),
        })
    except Exception as e:
        print(f"[Dashboard bienes/servicios] {e}")
        resultado.update({"total_bienes":0,"total_servicios":0})

    # ── Recuperación de crédito (pagos recibidos en el período) ───────────────
    try:
        rows = ejecutar_query("""
            SELECT
                SUM(ISNULL(MONTO,0)) AS recuperacion,
                COUNT(*)             AS docs_pagos
            FROM ETransac
            WHERE ID_TIPODOC  = '01'
              AND ID_CONCEPTO = '01'
              AND STATUS      = 'A'
              AND CAST(FECHA AS date) BETWEEN ? AND ?
        """, (fecha_ini, fecha_fin))
        r = rows[0] if rows else {}
        resultado.update({
            "recuperacion": float(r.get("recuperacion") or 0),
            "docs_pagos":   int(r.get("docs_pagos")    or 0),
        })
    except Exception as e:
        print(f"[Dashboard recuperacion] {e}")
        resultado.update({"recuperacion":0,"docs_pagos":0})

    return resultado


def get_dashboard_saldos(excluir_itservice: bool = False) -> dict:
    """
    Saldos actuales de CXC y CXP (sin filtro de fecha).
    """
    resultado = {}

    # ── Saldo CXC ─────────────────────────────────────────────────────────────
    try:
        rows = ejecutar_query("""
            SELECT
                SUM(ISNULL(SALDO_DOC,0)) AS saldo_cxc,
                COUNT(*)                 AS facturas_pendientes
            FROM ETransac
            WHERE ID_CONCEPTO = '02'
              AND STATUS      = 'A'
              AND SALDO_DOC   > 0
        """)
        r = rows[0] if rows else {}
        resultado.update({
            "saldo_cxc":          float(r.get("saldo_cxc")          or 0),
            "facturas_pendientes": int(r.get("facturas_pendientes")  or 0),
        })
    except Exception as e:
        print(f"[Dashboard CXC] {e}")
        resultado.update({"saldo_cxc":0,"facturas_pendientes":0})

    # ── Saldo CXP ─────────────────────────────────────────────────────────────
    _cxp_extra = " AND PROVEEDOR_ID <> 178" if excluir_itservice else ""
    try:
        rows = ejecutar_query(f"""
            SELECT
                SUM(ISNULL(SALDO_DOC,0)) AS saldo_cxp,
                COUNT(*)                 AS facturas_cxp
            FROM ETransacP
            WHERE ID_CONCEPTO = '01'
              AND STATUS      = 'A'
              AND SALDO_DOC   > 0
              {_cxp_extra}
        """)
        r = rows[0] if rows else {}
        resultado.update({
            "saldo_cxp":    float(r.get("saldo_cxp")    or 0),
            "facturas_cxp": int(r.get("facturas_cxp")   or 0),
        })
    except Exception as e:
        print(f"[Dashboard CXP] {e}")
        resultado.update({"saldo_cxp":0,"facturas_cxp":0})

    return resultado
