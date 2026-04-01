from db import ejecutar_query

def get_pagos_clientes(fecha_ini: str, fecha_fin: str,
                       tipo_pago: str = "", cliente_id: str = "",
                       filtro_fecha: str = "pago"):
    """
    filtro_fecha:
      'pago'     → filtra por FECHA         (día que el cliente pagó)
      'registro' → filtra por FECHA_REGISTRO (día que afecta la caja)
    """
    campo_filtro = "et.FECHA_REGISTRO" if filtro_fecha == "registro" else "et.FECHA"

    filtros = [f"CAST({campo_filtro} AS date) BETWEEN ? AND ?",
               "et.ID_TIPODOC  = '01'",
               "et.ID_CONCEPTO = '01'",
               "et.STATUS      = 'A'"]
    params  = [fecha_ini, fecha_fin]

    if tipo_pago:
        filtros.append("et.ID_TIPOPAGO = ?")
        params.append(tipo_pago)
    if cliente_id:
        filtros.append("et.ID_CLIENTE = ?")
        params.append(cliente_id)

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            et.ID_DOCUMENTO                                     AS num_doc,
            CONVERT(varchar(10), et.FECHA,          103)        AS fecha_pago,
            CONVERT(varchar(10), et.FECHA_REGISTRO, 103)        AS fecha_registro,
            et.ID_CLIENTE,
            cl.NOMBRE + ' ' + ISNULL(cl.APELLIDO1, '')         AS cliente,
            cl.CEDULA,
            ISNULL(tp.DESCRIPCION, '')                          AS tipo_pago,
            ISNULL(et.MONTO, 0)                                 AS monto,
            ISNULL(et.SALDO_ANT, 0)                             AS saldo_anterior,
            ISNULL(et.SALDO_ACT, 0)                             AS saldo_actual,
            ISNULL(et.MONTO, 0) - ISNULL(et.SALDO_ACT, 0)      AS monto_aplicado,
            ISNULL(et.REFERENCIA,   '')                         AS referencia,
            ISNULL(et.OBSERVACIONES,'')                         AS observaciones,
            et.STATUS
        FROM ETransac et
        INNER JOIN Clientes cl ON cl.ID_CLIENTE  = et.ID_CLIENTE
        LEFT  JOIN TipoPago tp ON tp.ID_TIPOPAGO = et.ID_TIPOPAGO
        WHERE {where}
        ORDER BY {campo_filtro} DESC, et.ID_DOCUMENTO DESC
    """
    return ejecutar_query(sql, tuple(params))

