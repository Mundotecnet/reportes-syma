from db import ejecutar_query

def get_ventas(fecha_ini: str, fecha_fin: str, tipo: str = "todos",
               categoria_cliente: str = "", estado: str = "A", vendedor_id: str = ""):
    """
    Reporte de ventas contado/crédito con categoría de cliente.
    tipo: 'todos' | '01' (contado) | '02' (crédito)
    """
    filtros = ["CAST(pv.FECHA AS date) BETWEEN ? AND ?"]
    params  = [fecha_ini, fecha_fin]

    if tipo != "todos":
        filtros.append("pv.ID_CONCEPTO = ?")
        params.append(tipo)

    if categoria_cliente:
        filtros.append("cl.CATEGORIA = ?")
        params.append(categoria_cliente)

    if estado != "todos":
        filtros.append("pv.ESTADO = ?")
        params.append(estado)

    if vendedor_id:
        filtros.append("pv.VENDEDOR_ID = ?")
        params.append(int(vendedor_id))

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            pv.ID_DOCUMENTO                             AS num_doc,
            CONVERT(varchar(10), pv.FECHA, 120)         AS fecha,
            CASE pv.ID_TIPODOC
                WHEN '02' THEN 'Factura'
                WHEN '04' THEN 'Tiquete'
                ELSE pv.ID_TIPODOC
            END                                         AS tipo_documento,
            CASE pv.ID_CONCEPTO
                WHEN '01' THEN 'Contado'
                WHEN '02' THEN 'Crédito'
                ELSE pv.ID_CONCEPTO
            END                                         AS tipo_venta,
            pv.ID_CLIENTE,
            pv.NOMBRE                                   AS cliente,
            pv.CEDULA,
            ISNULL(cl.CATEGORIA, '')                    AS cat_cliente,
            ISNULL(cc.CATEGORIA, '')                    AS desc_categoria,
            ISNULL(ch.NOMBRE, '')                       AS vendedor,
            ISNULL(tp.DESCRIPCION, '')                  AS tipo_pago,
            ISNULL(pv.SUBTOTAL_EXENTO, 0)               AS subtotal_exento,
            ISNULL(pv.SUBTOTAL_GRABADO, 0)              AS subtotal_grabado,
            ISNULL(pv.SUBTOTAL, 0)                      AS subtotal,
            ISNULL(pv.DESCUENTO, 0)                     AS descuento,
            ISNULL(pv.IMP_VENTA, 0)                     AS iva,
            ISNULL(pv.IMP_CONSUMO, 0)                   AS imp_consumo,
            ISNULL(pv.TOTAL, 0)                         AS total,
            ISNULL(pv.PLAZO, 0)                         AS plazo,
            ISNULL(pv.FACTURA, '')                      AS clave_numerica,
            pv.ESTADO
        FROM PUNTO_VENTA pv
        LEFT JOIN Clientes           cl  ON cl.ID_CLIENTE   = pv.ID_CLIENTE
        LEFT JOIN CLIENTES_CATEGORIA cc  ON cc.ID_CATEGORIA = cl.CATEGORIA
        LEFT JOIN CHOFERES           ch  ON ch.CHOFER_ID    = pv.VENDEDOR_ID
        LEFT JOIN TipoPago           tp  ON tp.ID_TIPOPAGO  = pv.ID_TIPOPAGO
        WHERE {where}
        ORDER BY pv.FECHA DESC, pv.ID_DOCUMENTO DESC
    """
    return ejecutar_query(sql, tuple(params))


def get_lineas_venta(id_documento: int) -> list:
    """Líneas de producto de una venta desde PUNTO_VENTA_DETALLE."""
    sql = """
        SELECT
            RTRIM(ISNULL(pvd.ID_PRODUCTO, ''))                         AS codigo,
            RTRIM(ISNULL(pvd.DESCRIPCION, ISNULL(p.DESCRIPCION, ''))) AS descripcion,
            RTRIM(ISNULL(p.UNIDAD_MEDIDA, ''))                        AS unidad,
            ISNULL(pvd.CANTIDAD,  0)                                   AS cantidad,
            ISNULL(pvd.PRECIO,    0)                                   AS precio_unit,
            ISNULL(pvd.DESCUENTO, 0)                                   AS descuento,
            ISNULL(pvd.IMPORTE,   0)                                   AS importe,
            ISNULL(pvd.PORC_IMP,  0)                                   AS porc_iva,
            ISNULL(pvd.MONTO_IMP, 0)                                   AS iva,
            ISNULL(pvd.IMPORTE, 0) + ISNULL(pvd.MONTO_IMP, 0)        AS total
        FROM PUNTO_VENTA_DETALLE pvd
        LEFT JOIN PRODUCTOS p ON p.CODIGO_ID = pvd.CODIGO_ID
        WHERE pvd.ID_DOCUMENTO = ?
        ORDER BY pvd.ID_PRODUCTO
    """
    try:
        return ejecutar_query(sql, (id_documento,))
    except Exception as e:
        print(f"[Ventas lineas] {e}")
        return []


def get_ventas_totales(fecha_ini: str, fecha_fin: str, tipo: str = "todos",
                       categoria_cliente: str = "", estado: str = "A", vendedor_id: str = ""):
    """Totales agrupados por tipo de venta y categoría de cliente."""
    filtros = ["CAST(pv.FECHA AS date) BETWEEN ? AND ?"]
    params  = [fecha_ini, fecha_fin]

    if tipo != "todos":
        filtros.append("pv.ID_CONCEPTO = ?")
        params.append(tipo)
    if categoria_cliente:
        filtros.append("cl.CATEGORIA = ?")
        params.append(categoria_cliente)
    if estado != "todos":
        filtros.append("pv.ESTADO = ?")
        params.append(estado)
    if vendedor_id:
        filtros.append("pv.VENDEDOR_ID = ?")
        params.append(int(vendedor_id))

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            CASE pv.ID_CONCEPTO
                WHEN '01' THEN 'Contado'
                WHEN '02' THEN 'Crédito'
                ELSE pv.ID_CONCEPTO
            END                                         AS tipo_venta,
            ISNULL(cl.CATEGORIA, 'S/C')                 AS cat_cliente,
            ISNULL(cc.CATEGORIA, 'Sin categoría')       AS desc_categoria,
            COUNT(DISTINCT pv.ID_DOCUMENTO)             AS num_facturas,
            SUM(ISNULL(pv.SUBTOTAL, 0))                 AS subtotal,
            SUM(ISNULL(pv.DESCUENTO, 0))                AS descuentos,
            SUM(ISNULL(pv.IMP_VENTA, 0))                AS iva,
            SUM(ISNULL(pv.TOTAL, 0))                    AS total_ventas
        FROM PUNTO_VENTA pv
        LEFT JOIN Clientes           cl  ON cl.ID_CLIENTE   = pv.ID_CLIENTE
        LEFT JOIN CLIENTES_CATEGORIA cc  ON cc.ID_CATEGORIA = cl.CATEGORIA
        WHERE {where}
        GROUP BY pv.ID_CONCEPTO, cl.CATEGORIA, cc.CATEGORIA
        ORDER BY total_ventas DESC
    """
    return ejecutar_query(sql, tuple(params))


def get_categorias_cliente():
    """Lista de categorías de clientes para el filtro."""
    sql = """
        SELECT ID_CATEGORIA, CATEGORIA
        FROM CLIENTES_CATEGORIA
        ORDER BY ID_CATEGORIA
    """
    return ejecutar_query(sql)


def get_vendedores():
    """Lista de vendedores para el filtro."""
    sql = """
        SELECT CHOFER_ID, NOMBRE
        FROM CHOFERES
        WHERE NOMBRE IS NOT NULL
        ORDER BY NOMBRE
    """
    return ejecutar_query(sql)


def get_ventas_grafico(
    fecha_ini: str, fecha_fin: str,
    agrupacion: str = "dia",
    tipo: str = "todos",
    categoria_cliente: str = "",
    estado: str = "A",
    vendedor_id: str = "",
) -> list:
    """
    Datos agregados para gráfico de ventas.
    agrupacion: 'dia' | 'semana' | 'mes' | 'año'
    """
    filtros = ["CAST(pv.FECHA AS date) BETWEEN ? AND ?"]
    params  = [fecha_ini, fecha_fin]

    if tipo != "todos":
        filtros.append("pv.ID_CONCEPTO = ?")
        params.append(tipo)
    if categoria_cliente:
        filtros.append("cl.CATEGORIA = ?")
        params.append(categoria_cliente)
    if estado != "todos":
        filtros.append("pv.ESTADO = ?")
        params.append(estado)
    if vendedor_id:
        filtros.append("pv.VENDEDOR_ID = ?")
        params.append(int(vendedor_id))

    where = " AND ".join(filtros)

    if agrupacion == "semana":
        select_periodo = ("CAST(YEAR(pv.FECHA) AS varchar) + '-S' + "
                          "RIGHT('0'+CAST(DATEPART(week,pv.FECHA) AS varchar),2)")
        group_by       = "YEAR(pv.FECHA), DATEPART(week,pv.FECHA)"
        order_by       = "YEAR(pv.FECHA), DATEPART(week,pv.FECHA)"
    elif agrupacion == "mes":
        select_periodo = "CONVERT(varchar(7), pv.FECHA, 120)"
        group_by       = "YEAR(pv.FECHA), MONTH(pv.FECHA), CONVERT(varchar(7), pv.FECHA, 120)"
        order_by       = "YEAR(pv.FECHA), MONTH(pv.FECHA)"
    elif agrupacion == "año":
        select_periodo = "CAST(YEAR(pv.FECHA) AS varchar)"
        group_by       = "YEAR(pv.FECHA)"
        order_by       = "YEAR(pv.FECHA)"
    else:  # dia
        select_periodo = "CONVERT(varchar(10), CAST(pv.FECHA AS date), 103)"
        group_by       = "CAST(pv.FECHA AS date)"
        order_by       = "CAST(pv.FECHA AS date)"

    sql = f"""
        SELECT
            {select_periodo}            AS periodo,
            COUNT(*)                    AS num_facturas,
            ISNULL(SUM(pv.TOTAL), 0)   AS total
        FROM PUNTO_VENTA pv
        LEFT JOIN Clientes cl ON cl.ID_CLIENTE = pv.ID_CLIENTE
        WHERE {where}
        GROUP BY {group_by}
        ORDER BY {order_by}
    """
    try:
        return ejecutar_query(sql, tuple(params))
    except Exception as e:
        print(f"[VentasGrafico] {e}")
        return []
