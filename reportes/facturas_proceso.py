from db import ejecutar_query


def get_facturas_proceso(fecha_ini: str = "", fecha_fin: str = "", busqueda: str = "") -> list:
    """
    Facturas con ESTADO='P' (en proceso / pendientes de envío FE).
    Incluye cabecera + líneas de detalle.
    """
    filtros = ["RTRIM(pv.ESTADO) = 'P'"]
    params  = []

    if fecha_ini and fecha_fin:
        filtros.append("CAST(pv.FECHA AS date) BETWEEN ? AND ?")
        params += [fecha_ini, fecha_fin]

    if busqueda:
        like = f"%{busqueda}%"
        filtros.append(
            "(RTRIM(pv.NOMBRE) LIKE ? OR RTRIM(pv.CEDULA) LIKE ? "
            "OR CAST(pv.ID_DOCUMENTO AS varchar(20)) LIKE ?)"
        )
        params += [like, like, like]

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            pv.ID_DOCUMENTO                                        AS id_documento,
            RTRIM(pv.ID_TIPODOC)                                   AS tipo_doc,
            RTRIM(pv.ID_CONCEPTO)                                  AS concepto,
            pv.FECHA                                               AS fecha,
            RTRIM(ISNULL(pv.NOMBRE, ''))                           AS cliente,
            RTRIM(ISNULL(pv.CEDULA, ''))                           AS cedula,
            ISNULL(pv.SUBTOTAL, 0)                                 AS subtotal,
            ISNULL(pv.IMP_VENTA, 0)                                AS iva,
            ISNULL(pv.TOTAL, 0)                                    AS total,
            RTRIM(ISNULL(pv.ID_MONEDA, 'CRC'))                     AS moneda,
            ISNULL(pv.TIPO_CAMBIO, 1)                              AS tipo_cambio,
            RTRIM(ISNULL(pv.FACTURA, ''))                          AS num_factura,
            RTRIM(ISNULL(pv.observaciones, ''))                    AS observaciones,
            RTRIM(ISNULL(pv.ID_TIPOPAGO, ''))                      AS tipo_pago,
            RTRIM(ISNULL(pv.RESPUESTA, ''))                        AS respuesta_fe
        FROM PUNTO_VENTA pv
        WHERE {where}
        ORDER BY pv.FECHA DESC
    """

    facturas = ejecutar_query(sql, tuple(params))
    if not facturas:
        return []

    # Cargar detalle de todas las facturas en una sola query
    ids = [f["id_documento"] for f in facturas]
    placeholders = ",".join("?" * len(ids))

    sql_det = f"""
        SELECT
            pvd.ID_DOCUMENTO                           AS id_documento,
            RTRIM(ISNULL(pvd.CODIGO_ID, ''))           AS codigo,
            RTRIM(ISNULL(pvd.DESCRIPCION, ''))         AS descripcion,
            ISNULL(pvd.CANTIDAD, 0)                    AS cantidad,
            ISNULL(pvd.PRECIO, 0)                      AS precio_unit,
            ISNULL(pvd.IMPORTE, 0)                     AS importe,
            ISNULL(pvd.MONTO_IMP, 0)                   AS iva_linea,
            ISNULL(pvd.IMPORTE, 0) + ISNULL(pvd.MONTO_IMP, 0) AS total_linea,
            RTRIM(ISNULL(pvd.SERIES, ''))                      AS serial
        FROM PUNTO_VENTA_DETALLE pvd
        WHERE pvd.ID_DOCUMENTO IN ({placeholders})
        ORDER BY pvd.ID_DOCUMENTO, pvd.ID_CP
    """
    lineas = ejecutar_query(sql_det, tuple(ids))

    # Mapear líneas a cada factura
    det_map = {}
    for ln in lineas:
        det_map.setdefault(ln["id_documento"], []).append(ln)

    for f in facturas:
        f["lineas"] = det_map.get(f["id_documento"], [])
        # Convertir decimales a float
        for key in ("subtotal", "iva", "total", "tipo_cambio"):
            f[key] = float(f[key])
        for ln in f["lineas"]:
            for key in ("cantidad", "precio_unit", "importe", "iva_linea", "total_linea"):
                ln[key] = float(ln[key])

    return facturas
