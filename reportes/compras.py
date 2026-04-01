from db import ejecutar_query

def get_compras(fecha_ini: str, fecha_fin: str,
                proveedor_id: str = "", estado: str = "",
                moneda: str = ""):
    filtros = ["CAST(c.FECHA AS date) BETWEEN ? AND ?"]
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
            c.DOCUMENTO_ID                                              AS num_doc,
            CONVERT(varchar(10), c.FECHA, 120)                          AS fecha,
            c.PROVEEDOR_ID                                              AS proveedor_id,
            p.NOMBRE                                                    AS proveedor,
            p.CEDULA                                                    AS cedula,
            ISNULL(c.FACTURA, '')                                       AS factura_proveedor,
            ISNULL(c.ID_MONEDA, 'CRC')                                  AS moneda,

            -- Tipo de cambio: primero el de la compra, si es 1 y moneda USD busca en tabla
            CASE
                WHEN ISNULL(c.ID_MONEDA,'CRC') = 'CRC' THEN 1
                WHEN ISNULL(c.TIPO_CAMBIO, 1) > 1       THEN c.TIPO_CAMBIO
                ELSE ISNULL(
                    (SELECT TOP 1 tc.VENTA
                     FROM TIPO_CAMBIO tc
                     WHERE tc.ID_MONEDA = c.ID_MONEDA
                       AND CONVERT(date, tc.FECHA) <= CONVERT(date, c.FECHA)
                     ORDER BY tc.FECHA DESC), c.TIPO_CAMBIO)
            END                                                         AS tipo_cambio,

            ISNULL(c.SUBTOTAL, 0)                                       AS subtotal,
            ISNULL(c.DESCUENTO, 0)                                      AS descuento,
            ISNULL(c.IMP_VENTA, 0)                                      AS iva,
            ISNULL(c.TOTAL, 0)                                          AS total_moneda,

            -- Total en colones
            CASE
                WHEN ISNULL(c.ID_MONEDA, 'CRC') = 'CRC'
                    THEN ISNULL(c.TOTAL, 0)
                ELSE
                    ISNULL(c.TOTAL, 0) * CASE
                        WHEN ISNULL(c.TIPO_CAMBIO, 1) > 1 THEN c.TIPO_CAMBIO
                        ELSE ISNULL(
                            (SELECT TOP 1 tc.VENTA
                             FROM TIPO_CAMBIO tc
                             WHERE tc.ID_MONEDA = c.ID_MONEDA
                               AND CONVERT(date, tc.FECHA) <= CONVERT(date, c.FECHA)
                             ORDER BY tc.FECHA DESC), 1)
                    END
            END                                                         AS total_crc,

            -- Total en dolares
            CASE
                WHEN ISNULL(c.ID_MONEDA, 'CRC') = 'USD'
                    THEN ISNULL(c.TOTAL, 0)
                ELSE 0
            END                                                         AS total_usd,

            ISNULL(c.PLAZO, 0)                                          AS plazo,
            ISNULL(c.ESTADO, '')                                        AS estado,
            ISNULL(c.OBSERVACIONES, '')                                 AS observaciones
        FROM COMPRAS c
        INNER JOIN Proveedores p ON p.PROVEEDOR_ID = c.PROVEEDOR_ID
        WHERE {where}
        ORDER BY c.FECHA DESC, c.DOCUMENTO_ID DESC
    """
    return ejecutar_query(sql, tuple(params))


def get_lineas_compra(documento_id: int) -> list:
    """Líneas de producto de una compra desde COMPRAS_DETALLE."""
    sql = """
        SELECT
            RTRIM(ISNULL(cd.ID_PRODUCTO, ''))                        AS codigo,
            RTRIM(ISNULL(cd.DESCRIPCION, ISNULL(p.DESCRIPCION,'')))  AS descripcion,
            RTRIM(ISNULL(p.UNIDAD_MEDIDA, ''))                       AS unidad,
            ISNULL(cd.CANTIDAD,       0)                             AS cantidad,
            ISNULL(cd.COSTO_UNITARIO, 0)                             AS costo_unit,
            ISNULL(cd.DESCUENTO,      0)                             AS descuento,
            ISNULL(cd.IMPORTE,        0)                             AS importe,
            ISNULL(cd.PORCENTAJE_IV,  0)                             AS porc_iv,
            ROUND(ISNULL(cd.IMPORTE, 0)
                  * ISNULL(cd.PORCENTAJE_IV, 0) / 100, 2)           AS iva
        FROM COMPRAS_DETALLE cd
        LEFT JOIN PRODUCTOS p ON p.CODIGO_ID = cd.CODIGO_ID
        WHERE cd.DOCUMENTO_ID = ?
        ORDER BY cd.ID_PRODUCTO
    """
    try:
        return ejecutar_query(sql, (documento_id,))
    except Exception as e:
        print(f"[Compras lineas] {e}")
        return []


def get_proveedores():
    sql = """
        SELECT PROVEEDOR_ID, NOMBRE
        FROM Proveedores
        WHERE ESTADO = 'A'
        ORDER BY NOMBRE
    """
    return ejecutar_query(sql)
