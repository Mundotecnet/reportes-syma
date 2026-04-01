from db import ejecutar_query


def get_compras_ventas_grafico(
    fecha_ini:  str,
    fecha_fin:  str,
    agrupacion: str = "mes",
) -> list:
    """
    Reporte comparativo Ventas vs Compras con utilidad bruta por período.

    Utilidad bruta = Ventas netas (SUBTOTAL-DESCUENTO) − Compras del período (en CRC)
    Nota: aproximación práctica; la diferencia de inventario puede afectar el dato.
    """
    if agrupacion == "dia":
        lbl_v = "CONVERT(varchar(10), pv.FECHA, 103)"
        srt_v = "CONVERT(varchar(10), CAST(pv.FECHA AS date), 120)"
        lbl_c = "CONVERT(varchar(10), c.FECHA, 103)"
        srt_c = "CONVERT(varchar(10), CAST(c.FECHA AS date), 120)"
    elif agrupacion == "semana":
        lbl_v = ("RIGHT('0'+CAST(DATEPART(wk,pv.FECHA) AS varchar(2)),2)"
                 " + '/' + CAST(YEAR(pv.FECHA) AS varchar(4))")
        srt_v = ("CAST(YEAR(pv.FECHA) AS varchar(4)) + '-'"
                 " + RIGHT('0'+CAST(DATEPART(wk,pv.FECHA) AS varchar(2)),2)")
        lbl_c = ("RIGHT('0'+CAST(DATEPART(wk,c.FECHA) AS varchar(2)),2)"
                 " + '/' + CAST(YEAR(c.FECHA) AS varchar(4))")
        srt_c = ("CAST(YEAR(c.FECHA) AS varchar(4)) + '-'"
                 " + RIGHT('0'+CAST(DATEPART(wk,c.FECHA) AS varchar(2)),2)")
    elif agrupacion == "anio":
        lbl_v = "CAST(YEAR(pv.FECHA) AS varchar(4))"
        srt_v = "CAST(YEAR(pv.FECHA) AS varchar(4))"
        lbl_c = "CAST(YEAR(c.FECHA) AS varchar(4))"
        srt_c = "CAST(YEAR(c.FECHA) AS varchar(4))"
    else:  # mes (default)
        lbl_v = ("RIGHT('0'+CAST(MONTH(pv.FECHA) AS varchar(2)),2)"
                 " + '/' + CAST(YEAR(pv.FECHA) AS varchar(4))")
        srt_v = ("CAST(YEAR(pv.FECHA) AS varchar(4)) + '-'"
                 " + RIGHT('0'+CAST(MONTH(pv.FECHA) AS varchar(2)),2)")
        lbl_c = ("RIGHT('0'+CAST(MONTH(c.FECHA) AS varchar(2)),2)"
                 " + '/' + CAST(YEAR(c.FECHA) AS varchar(4))")
        srt_c = ("CAST(YEAR(c.FECHA) AS varchar(4)) + '-'"
                 " + RIGHT('0'+CAST(MONTH(c.FECHA) AS varchar(2)),2)")

    sql = f"""
    WITH V AS (
        SELECT
            {srt_v}  AS sk,
            {lbl_v}  AS periodo,
            SUM(ISNULL(pv.SUBTOTAL, 0) - ISNULL(pv.DESCUENTO, 0)) AS ventas_netas,
            SUM(ISNULL(pv.TOTAL,    0))                             AS ventas_total,
            COUNT(*)                                                AS num_ventas
        FROM PUNTO_VENTA pv
        WHERE CAST(pv.FECHA AS date) BETWEEN ? AND ?
          AND pv.ESTADO = 'A'
        GROUP BY {srt_v}, {lbl_v}
    ),
    C AS (
        SELECT
            {srt_c}  AS sk,
            {lbl_c}  AS periodo,
            SUM(
                CASE WHEN ISNULL(c.ID_MONEDA,'CRC') != 'CRC'
                          AND ISNULL(c.TIPO_CAMBIO, 0) > 1
                     THEN ISNULL(c.TOTAL, 0) * c.TIPO_CAMBIO
                     ELSE ISNULL(c.TOTAL, 0)
                END
            )        AS compras_total,
            COUNT(*) AS num_compras
        FROM COMPRAS c
        WHERE CAST(c.FECHA AS date) BETWEEN ? AND ?
        GROUP BY {srt_c}, {lbl_c}
    )
    SELECT
        ISNULL(v.sk,      c.sk)                                   AS sort_key,
        ISNULL(v.periodo, c.periodo)                              AS periodo,
        ISNULL(v.ventas_netas,  0)                                AS ventas_netas,
        ISNULL(v.ventas_total,  0)                                AS ventas_total,
        ISNULL(c.compras_total, 0)                                AS compras_total,
        ISNULL(v.ventas_netas,  0) - ISNULL(c.compras_total, 0)  AS utilidad,
        ISNULL(v.num_ventas,    0)                                AS num_ventas,
        ISNULL(c.num_compras,   0)                                AS num_compras
    FROM V v
    FULL OUTER JOIN C c ON c.sk = v.sk
    ORDER BY ISNULL(v.sk, c.sk)
    """
    params = (fecha_ini, fecha_fin, fecha_ini, fecha_fin)
    try:
        return ejecutar_query(sql, params)
    except Exception as e:
        print(f"[ComprasVentasGrafico] {e}")
        return []
