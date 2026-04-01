from collections import defaultdict
from db import ejecutar_query


def _get_facturas(ids: list) -> list:
    """
    Facturas pendientes por cliente usando ETransac.

    ETransac con ID_CONCEPTO='02', STATUS='A', SALDO_DOC>0 contiene
    exactamente las facturas que Syma muestra en "Facturas Pendientes".
    SALDO_DOC es el saldo actualizado por factura (se reduce al aplicar pagos).
    Incluye facturas antiguas (pre-facturación electrónica) que no existen
    en PUNTO_VENTA.
    """
    if not ids:
        return []

    placeholders = ",".join(["?"] * len(ids))

    sql = f"""
        SELECT
            et.ID_CLIENTE                                        AS id_cliente,
            et.ID_DOCUMENTO                                      AS id_documento,
            ISNULL(pv.ID_DOCUMENTO, 0)                           AS pv_id,
            RTRIM(CAST(et.ID_DOCUMENTO AS varchar(20)))          AS num_doc,
            CONVERT(varchar(10), et.FECHA,       103)            AS fecha,
            CONVERT(varchar(10), et.FECHA_VENCE, 103)            AS fecha_vence,
            RTRIM(ISNULL(et.ID_TIPODOC, ''))                     AS tipo_doc,
            ISNULL(et.MONTO,     0)                              AS total,
            ISNULL(et.SALDO_DOC, 0)                              AS saldo_factura,
            DATEDIFF(day,
                CAST(et.FECHA_VENCE AS date),
                CAST(GETDATE()      AS date))                    AS dias_atraso
        FROM ETransac et
        LEFT JOIN PUNTO_VENTA pv
            ON  pv.ID_CLIENTE        = et.ID_CLIENTE
            AND CAST(pv.FECHA AS date) = CAST(et.FECHA AS date)
            AND pv.TOTAL             = et.MONTO
            AND pv.PLAZO             > 0
            AND pv.ESTADO            = 'A'
        WHERE et.ID_CLIENTE  IN ({placeholders})
          AND et.ID_CONCEPTO  = '02'
          AND et.STATUS       = 'A'
          AND et.SALDO_DOC    > 0
        ORDER BY et.ID_CLIENTE, et.FECHA, et.ID_DOCUMENTO
    """
    try:
        return ejecutar_query(sql, tuple(ids))
    except Exception as e:
        print(f"[CxC facturas] {e}")
        return []


def get_lineas_factura(pv_id: int) -> list:
    """
    Líneas de PUNTO_VENTA_DETALLE usando el ID de PUNTO_VENTA obtenido
    vía ETransac.CERTIFICADO = PUNTO_VENTA.FACTURA.
    Retorna lista vacía si pv_id es 0 (factura antigua sin enlace).
    """
    if not pv_id:
        return []
    sql = """
        SELECT
            RTRIM(ISNULL(pvd.ID_PRODUCTO, ''))                  AS codigo,
            RTRIM(ISNULL(pvd.DESCRIPCION,
                  ISNULL(p.DESCRIPCION, '')))                   AS descripcion,
            RTRIM(ISNULL(p.UNIDAD_MEDIDA, ''))                  AS unidad,
            ISNULL(pvd.CANTIDAD,   0)                           AS cantidad,
            ISNULL(pvd.PRECIO,     0)                           AS precio_unit,
            ISNULL(pvd.DESCUENTO,  0)                           AS descuento,
            ISNULL(pvd.IMPORTE,    0)                           AS subtotal,
            ISNULL(pvd.MONTO_IMP,  0)                           AS iva,
            ISNULL(pvd.IMPORTE, 0) + ISNULL(pvd.MONTO_IMP, 0)  AS total
        FROM PUNTO_VENTA_DETALLE pvd
        LEFT JOIN PRODUCTOS p ON p.CODIGO_ID = pvd.CODIGO_ID
        WHERE pvd.ID_DOCUMENTO = ?
        ORDER BY pvd.ID_PRODUCTO
    """
    try:
        return ejecutar_query(sql, (pv_id,))
    except Exception as e:
        print(f"[CxC lineas] {e}")
        return []


def get_cxc(categoria: str = "", busqueda: str = "", solo_saldo_positivo: bool = True):
    """
    Cuentas por Cobrar: clientes con saldo pendiente.
    Incluye facturas de crédito pendientes calculadas con lógica FIFO.
    """
    filtros = ["cl.ESTADO = 'A'"]
    params  = []

    if solo_saldo_positivo:
        filtros.append("cl.SALDO > 0")

    if categoria:
        filtros.append("cl.CATEGORIA = ?")
        params.append(categoria)

    if busqueda:
        like = f"%{busqueda}%"
        filtros.append(
            "(CAST(cl.ID_CLIENTE AS varchar(20)) LIKE ? "
            "OR cl.NOMBRE    LIKE ? "
            "OR cl.APELLIDO1 LIKE ? "
            "OR cl.APELLIDO2 LIKE ?)"
        )
        params.extend([like, like, like, like])

    where = " AND ".join(filtros)

    sql_clientes = f"""
        SELECT
            cl.ID_CLIENTE                                           AS codigo,
            RTRIM(cl.NOMBRE)
              + CASE WHEN RTRIM(ISNULL(cl.APELLIDO1,' ')) <> ''
                     THEN ' ' + RTRIM(cl.APELLIDO1) ELSE '' END
              + CASE WHEN RTRIM(ISNULL(cl.APELLIDO2,' ')) <> ''
                     THEN ' ' + RTRIM(cl.APELLIDO2) ELSE '' END    AS cliente,
            ISNULL(cl.CEDULA,    '')                                AS cedula,
            ISNULL(cl.CATEGORIA, '')                                AS categoria,
            ISNULL(cc.CATEGORIA, '')                                AS desc_categoria,
            ISNULL(cl.SALDO, 0)                                     AS saldo
        FROM Clientes cl
        LEFT JOIN CLIENTES_CATEGORIA cc ON cc.ID_CATEGORIA = cl.CATEGORIA
        WHERE {where}
        ORDER BY cl.SALDO DESC
    """
    clientes = ejecutar_query(sql_clientes, tuple(params))

    if not clientes:
        return []

    ids      = [c["codigo"] for c in clientes]
    facturas = _get_facturas(ids)

    fac_map = defaultdict(list)
    for f in facturas:
        fac_map[f["id_cliente"]].append(f)

    for c in clientes:
        c["facturas"] = fac_map.get(c["codigo"], [])

    return clientes
