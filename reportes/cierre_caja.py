from db import ejecutar_query


def get_cierre_caja(fecha: str) -> dict:
    """
    Cierre de caja para una fecha dada.
    Dos queries: ventas del día + cobros CXC del día.
    Resultado agrupado por forma de pago.
    """

    # ── VENTAS del día ────────────────────────────────────────────────────────
    # Solo contado (ID_CONCEPTO='01') entra en el desglose de cobro.
    # Crédito (ID_CONCEPTO='02') se muestra aparte — el dinero llega por CXC.
    ventas = ejecutar_query("""
        SELECT
            COUNT(*)                                                         AS docs,
            SUM(ISNULL(TOTAL, 0))                                            AS total,

            -- Contado: desglose por forma de pago
            SUM(CASE WHEN RTRIM(ID_CONCEPTO)='01'
                     THEN ISNULL(MONTO_TARJETAS,0) ELSE 0 END)              AS tarjetas,
            SUM(CASE WHEN RTRIM(ID_CONCEPTO)='01'
                     THEN ISNULL(MONTO_CHEQUES,0) ELSE 0 END)               AS cheques,
            SUM(CASE WHEN RTRIM(ID_CONCEPTO)='01'
                     THEN ISNULL(MONTO_TRANSFERENCIAS,0) ELSE 0 END)        AS transferencias,
            SUM(CASE WHEN RTRIM(ID_CONCEPTO)='01'
                     THEN ISNULL(TOTAL,0)
                          - ISNULL(MONTO_TARJETAS,0)
                          - ISNULL(MONTO_CHEQUES,0)
                          - ISNULL(MONTO_TRANSFERENCIAS,0)
                     ELSE 0 END)                                             AS efectivo,

            -- Crédito: monto facturado pendiente de cobro
            SUM(CASE WHEN RTRIM(ID_CONCEPTO)='02'
                     THEN ISNULL(TOTAL,0) ELSE 0 END)                       AS credito,
            COUNT(CASE WHEN RTRIM(ID_CONCEPTO)='02' THEN 1 END)             AS docs_credito,
            COUNT(CASE WHEN RTRIM(ID_CONCEPTO)='01' THEN 1 END)             AS docs_contado
        FROM PUNTO_VENTA
        WHERE CAST(FECHA AS date) = ?
          AND ESTADO = 'A'
    """, (fecha,))

    v = ventas[0] if ventas else {}

    # ── COBROS CXC del día ────────────────────────────────────────────────────
    cobros = ejecutar_query("""
        SELECT
            COUNT(*)                                                         AS docs,
            SUM(ISNULL(MONTO, 0))                                            AS total,
            SUM(CASE WHEN RTRIM(ISNULL(ID_TIPOPAGO,'01')) = '01'
                     THEN ISNULL(MONTO, 0) ELSE 0 END)                       AS efectivo,
            SUM(CASE WHEN RTRIM(ISNULL(ID_TIPOPAGO,'01')) = '02'
                     THEN ISNULL(MONTO, 0) ELSE 0 END)                       AS tarjetas,
            SUM(CASE WHEN RTRIM(ISNULL(ID_TIPOPAGO,'01')) = '03'
                     THEN ISNULL(MONTO, 0) ELSE 0 END)                       AS cheques,
            SUM(CASE WHEN RTRIM(ISNULL(ID_TIPOPAGO,'01')) IN ('04','06','07')
                     THEN ISNULL(MONTO, 0) ELSE 0 END)                       AS transferencias
        FROM ETransac
        WHERE CAST(FECHA AS date) = ?
          AND ID_TIPODOC  = '01'
          AND ID_CONCEPTO = '01'
          AND STATUS      = 'A'
    """, (fecha,))

    c = cobros[0] if cobros else {}

    # ── CAJAS_TRANS del día (entradas/salidas manuales) ───────────────────────
    trans = ejecutar_query("""
        SELECT
            RTRIM(TIPO_ID)  AS tipo,
            RTRIM(CONCEPTO) AS concepto,
            MONTO,
            RTRIM(ISNULL(RESPONSABLE,'')) AS responsable
        FROM CAJAS_TRANS
        WHERE CAST(FECHA AS date) = ?
          AND ESTADO = 'A'
        ORDER BY FECHA
    """, (fecha,))

    entradas  = sum(float(t["MONTO"] or 0) for t in trans if t["tipo"] == "E")
    salidas   = sum(float(t["MONTO"] or 0) for t in trans if t["tipo"] == "S")

    # ── DETALLE VENTAS del día ────────────────────────────────────────────────
    detalle_ventas = ejecutar_query("""
        SELECT
            pv.ID_DOCUMENTO                                                  AS doc,
            RTRIM(ISNULL(pv.FACTURA,''))                                     AS factura,
            CONVERT(varchar(5), pv.FECHA, 108)                               AS hora,
            RTRIM(ISNULL(pv.NOMBRE,''))                                      AS cliente,
            RTRIM(ISNULL(tp.DESCRIPCION,''))                                 AS forma_pago,
            RTRIM(ISNULL(pv.ID_CONCEPTO,''))                                 AS concepto,
            ISNULL(pv.TOTAL, 0)                                              AS total,
            ISNULL(pv.MONTO_TARJETAS, 0)                                     AS tarjetas,
            ISNULL(pv.MONTO_CHEQUES, 0)                                      AS cheques,
            ISNULL(pv.MONTO_TRANSFERENCIAS, 0)                               AS transferencias,
            CASE WHEN RTRIM(pv.ID_CONCEPTO)='01'
                 THEN ISNULL(pv.TOTAL,0)
                      - ISNULL(pv.MONTO_TARJETAS,0)
                      - ISNULL(pv.MONTO_CHEQUES,0)
                      - ISNULL(pv.MONTO_TRANSFERENCIAS,0)
                 ELSE 0 END                                                  AS efectivo
        FROM PUNTO_VENTA pv
        LEFT JOIN TipoPago tp ON RTRIM(tp.ID_TIPOPAGO) = RTRIM(pv.ID_TIPOPAGO)
        WHERE CAST(pv.FECHA AS date) = ?
          AND pv.ESTADO = 'A'
        ORDER BY pv.FECHA
    """, (fecha,))

    # ── DETALLE COBROS CXC del día ────────────────────────────────────────────
    detalle_cobros = ejecutar_query("""
        SELECT
            et.ID_DOCUMENTO                                                  AS doc,
            CONVERT(varchar(5), et.FECHA, 108)                               AS hora,
            RTRIM(ISNULL(cl.NOMBRE,'') + ' ' + ISNULL(cl.APELLIDO1,''))     AS cliente,
            RTRIM(ISNULL(tp.DESCRIPCION,''))                                 AS forma_pago,
            ISNULL(et.MONTO, 0)                                              AS total
        FROM ETransac et
        LEFT JOIN Clientes cl ON cl.ID_CLIENTE = et.ID_CLIENTE
        LEFT JOIN TipoPago tp ON RTRIM(tp.ID_TIPOPAGO) = RTRIM(et.ID_TIPOPAGO)
        WHERE CAST(et.FECHA AS date) = ?
          AND et.ID_TIPODOC  = '01'
          AND et.ID_CONCEPTO = '01'
          AND et.STATUS      = 'A'
        ORDER BY et.FECHA
    """, (fecha,))

    def f(val):
        return float(val or 0)

    return {
        "fecha": fecha,

        # Ventas
        "v_docs":          int(f(v.get("docs"))),
        "v_total":         f(v.get("total")),
        "v_efectivo":      f(v.get("efectivo")),
        "v_tarjetas":      f(v.get("tarjetas")),
        "v_cheques":       f(v.get("cheques")),
        "v_transferencias": f(v.get("transferencias")),
        "v_credito":       f(v.get("credito")),
        "v_docs_contado":  int(f(v.get("docs_contado"))),
        "v_docs_credito":  int(f(v.get("docs_credito"))),

        # Cobros CXC
        "c_docs":           int(f(c.get("docs"))),
        "c_total":          f(c.get("total")),
        "c_efectivo":       f(c.get("efectivo")),
        "c_tarjetas":       f(c.get("tarjetas")),
        "c_cheques":        f(c.get("cheques")),
        "c_transferencias": f(c.get("transferencias")),

        # Totales consolidados por forma de pago (solo contado + cobros CXC)
        "total_efectivo":       f(v.get("efectivo"))       + f(c.get("efectivo")),
        "total_tarjetas":       f(v.get("tarjetas"))       + f(c.get("tarjetas")),
        "total_cheques":        f(v.get("cheques"))        + f(c.get("cheques")),
        "total_transferencias": f(v.get("transferencias")) + f(c.get("transferencias")),
        "total_cobrado":        f(v.get("total")) - f(v.get("credito")) + f(c.get("total")),
        "gran_total":           f(v.get("total"))           + f(c.get("total")),

        # CAJAS_TRANS
        "trans_entradas": entradas,
        "trans_salidas":  salidas,
        "trans_detalle":  [{"tipo": t["tipo"], "concepto": t["concepto"],
                            "monto": float(t["MONTO"] or 0),
                            "responsable": t["responsable"]} for t in trans],

        # Detalle ventas
        "detalle_ventas": [{
            "doc":            r["doc"],
            "factura":        r["factura"].strip(),
            "hora":           r["hora"],
            "cliente":        r["cliente"],
            "forma_pago":     r["forma_pago"],
            "concepto":       r["concepto"].strip(),
            "total":          f(r["total"]),
            "efectivo":       f(r["efectivo"]),
            "tarjetas":       f(r["tarjetas"]),
            "cheques":        f(r["cheques"]),
            "transferencias": f(r["transferencias"]),
        } for r in detalle_ventas],

        # Detalle cobros
        "detalle_cobros": [{
            "doc":        r["doc"],
            "hora":       r["hora"],
            "cliente":    r["cliente"].strip(),
            "forma_pago": r["forma_pago"],
            "total":      f(r["total"]),
        } for r in detalle_cobros],
    }
