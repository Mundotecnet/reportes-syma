from db import ejecutar_query


def get_cierre_caja(fecha: str) -> dict:
    """
    Cierre de caja para una fecha dada.
    Dos queries: ventas del día + cobros CXC del día.
    Resultado agrupado por forma de pago.
    """

    # ── VENTAS del día ────────────────────────────────────────────────────────
    ventas = ejecutar_query("""
        SELECT
            COUNT(*)                                                        AS docs,
            SUM(ISNULL(TOTAL, 0))                                           AS total,
            SUM(ISNULL(MONTO_TARJETAS, 0))                                  AS tarjetas,
            SUM(ISNULL(MONTO_CHEQUES, 0))                                   AS cheques,
            SUM(ISNULL(MONTO_TRANSFERENCIAS, 0))                            AS transferencias,
            SUM(ISNULL(TOTAL, 0)
                - ISNULL(MONTO_TARJETAS, 0)
                - ISNULL(MONTO_CHEQUES, 0)
                - ISNULL(MONTO_TRANSFERENCIAS, 0))                          AS efectivo
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

        # Cobros CXC
        "c_docs":           int(f(c.get("docs"))),
        "c_total":          f(c.get("total")),
        "c_efectivo":       f(c.get("efectivo")),
        "c_tarjetas":       f(c.get("tarjetas")),
        "c_cheques":        f(c.get("cheques")),
        "c_transferencias": f(c.get("transferencias")),

        # Totales consolidados por forma de pago
        "total_efectivo":       f(v.get("efectivo"))      + f(c.get("efectivo")),
        "total_tarjetas":       f(v.get("tarjetas"))      + f(c.get("tarjetas")),
        "total_cheques":        f(v.get("cheques"))       + f(c.get("cheques")),
        "total_transferencias": f(v.get("transferencias"))+ f(c.get("transferencias")),
        "gran_total":           f(v.get("total"))         + f(c.get("total")),

        # CAJAS_TRANS
        "trans_entradas": entradas,
        "trans_salidas":  salidas,
        "trans_detalle":  [{"tipo": t["tipo"], "concepto": t["concepto"],
                            "monto": float(t["MONTO"] or 0),
                            "responsable": t["responsable"]} for t in trans],
    }
