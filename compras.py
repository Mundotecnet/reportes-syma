from db import ejecutar_query

def get_compras(fecha_ini: str, fecha_fin: str,
                proveedor_id: str = "", estado: str = "",
                moneda: str = ""):
    filtros = ["c.FECHA BETWEEN ? AND ?"]
    params  = [fecha_ini, fecha_fin]

    if proveedor_id:
        filtros.append("c.PROVEEDOR_ID = ?")
        params.append(proveedor_id)
    if estado:
        filtros.append("c.ESTADO = ?")
        params.append(estado)
    if moneda:
        filtros.append("c.ID_MONEDA = ?")
        params.append(moneda)

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            c.DOCUMENTO_ID                                          AS num_doc,
            CONVERT(varchar(10), c.FECHA, 120)                      AS fecha,
            c.PROVEEDOR_ID,
            p.NOMBRE                                                AS proveedor,
            p.CEDULA,
            ISNULL(c.FACTURA, '')                                   AS factura_proveedor,
            ISNULL(c.ID_MONEDA, 'CRC')                              AS moneda,
            ISNULL(c.TIPO_CAMBIO, 1)                                AS tipo_cambio,
            ISNULL(c.SUBTOTAL_EXENTO, 0)                            AS subtotal_exento,
            ISNULL(c.SUBTOTAL_GRABADO, 0)                           AS subtotal_grabado,
            ISNULL(c.SUBTOTAL, 0)                                   AS subtotal,
            ISNULL(c.DESCUENTO, 0)                                  AS descuento,
            ISNULL(c.IMP_VENTA, 0)                                  AS iva,
            ISNULL(c.IMP_CONSUMO, 0)                                AS imp_consumo,
            ISNULL(c.TOTAL, 0)                                      AS total,
            CASE
                WHEN ISNULL(c.ID_MONEDA, 'CRC') = 'CRC'
                    THEN ISNULL(c.TOTAL, 0)
                ELSE ISNULL(c.TOTAL, 0) * ISNULL(c.TIPO_CAMBIO, 1)
            END                                                     AS total_crc,
            ISNULL(c.PLAZO, 0)                                      AS plazo,
            ISNULL(c.ESTADO, '')                                    AS estado,
            ISNULL(c.OBSERVACIONES, '')                             AS observaciones
        FROM COMPRAS c
        INNER JOIN Proveedores p ON p.PROVEEDOR_ID = c.PROVEEDOR_ID
        WHERE {where}
        ORDER BY c.FECHA DESC, c.DOCUMENTO_ID DESC
    """
    return ejecutar_query(sql, tuple(params))


def get_proveedores():
    sql = """
        SELECT PROVEEDOR_ID, NOMBRE
        FROM Proveedores
        WHERE ESTADO = 'A'
        ORDER BY NOMBRE
    """
    return ejecutar_query(sql)
