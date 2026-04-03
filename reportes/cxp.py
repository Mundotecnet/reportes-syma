from collections import defaultdict
from db import ejecutar_query


ITSERVICE_ID = 178  # IT SERVICE SOCIEDAD ANONIMA

def get_cxp(busqueda: str = "", excluir_itservice: bool = False) -> list:
    """
    Cuentas por Pagar: proveedores con facturas pendientes en ETransacP.
    ID_CONCEPTO='01' = facturas de compra, STATUS='A', SALDO_DOC>0 = pendientes.
    """
    where_extra = ""
    params = []

    if busqueda:
        like = f"%{busqueda}%"
        where_extra += (
            " AND (CAST(p.PROVEEDOR_ID AS varchar(20)) LIKE ?"
            " OR p.NOMBRE LIKE ?"
            " OR p.CEDULA LIKE ?)"
        )
        params.extend([like, like, like])
    if excluir_itservice:
        where_extra += f" AND p.PROVEEDOR_ID <> {ITSERVICE_ID}"

    sql = f"""
        SELECT
            p.PROVEEDOR_ID                            AS codigo,
            RTRIM(ISNULL(p.NOMBRE,    ''))            AS proveedor,
            RTRIM(ISNULL(p.CEDULA,    ''))            AS cedula,
            RTRIM(ISNULL(p.TELEFONO1, ''))            AS telefono,
            RTRIM(ISNULL(p.EMAIL,     ''))            AS email,
            ISNULL(p.PLAZO, 0)                        AS plazo,
            SUM(ISNULL(ep.SALDO_DOC, 0))              AS saldo,
            COUNT(ep.ID_DOCUMENTO)                    AS num_docs,
            MIN(RTRIM(ISNULL(ep.ID_MONEDA, 'COL')))  AS moneda
        FROM Proveedores p
        JOIN ETransacP ep ON ep.PROVEEDOR_ID = p.PROVEEDOR_ID
        WHERE ep.ID_CONCEPTO = '01'
          AND ep.STATUS      = 'A'
          AND ep.SALDO_DOC   > 0
          {where_extra}
        GROUP BY p.PROVEEDOR_ID, p.NOMBRE, p.CEDULA,
                 p.TELEFONO1, p.EMAIL, p.PLAZO
        ORDER BY SUM(ISNULL(ep.SALDO_DOC, 0)) DESC
    """
    try:
        return ejecutar_query(sql, tuple(params))
    except Exception as e:
        print(f"[CxP] {e}")
        return []


def get_calendario_pagos(fecha_ini: str, fecha_fin: str) -> list:
    """
    Facturas pendientes cuyo vencimiento cae en el rango [fecha_ini, fecha_fin].
    Usado para el calendario semanal de pagos.
    """
    sql = """
        SELECT
            CONVERT(varchar(10), ep.FECHA_VENCE, 23)           AS dia_vence,
            p.PROVEEDOR_ID                                      AS codigo,
            RTRIM(ISNULL(p.NOMBRE, ''))                        AS proveedor,
            ep.ID_DOCUMENTO                                     AS documento_id,
            RTRIM(ISNULL(c.FACTURA, ''))                       AS factura,
            CONVERT(varchar(10), ep.FECHA, 103)                AS fecha,
            CONVERT(varchar(10), ep.FECHA_VENCE, 103)          AS fecha_vence,
            ISNULL(ep.SALDO_DOC, 0)                            AS saldo,
            RTRIM(ISNULL(ep.ID_MONEDA, 'COL'))                 AS moneda,
            DATEDIFF(day,
                CAST(GETDATE() AS date),
                CAST(ep.FECHA_VENCE AS date))                  AS dias_vence
        FROM ETransacP ep
        JOIN  Proveedores p ON p.PROVEEDOR_ID = ep.PROVEEDOR_ID
        LEFT JOIN COMPRAS c
            ON  c.DOCUMENTO_ID = ep.ID_DOCUMENTO
            AND c.ID_TIPODOC   = ep.ID_TIPODOC
        WHERE ep.ID_CONCEPTO = '01'
          AND ep.STATUS      = 'A'
          AND ep.SALDO_DOC   > 0
          AND CAST(ep.FECHA_VENCE AS date) BETWEEN ? AND ?
        ORDER BY ep.FECHA_VENCE ASC, p.NOMBRE ASC
    """
    try:
        return ejecutar_query(sql, (fecha_ini, fecha_fin))
    except Exception as e:
        print(f"[CxP Calendario] {e}")
        return []


def get_lineas_compra(documento_id: int) -> list:
    """Líneas de detalle de una compra (COMPRAS_DETALLE)."""
    sql = """
        SELECT
            cd.LINEA                                        AS linea,
            RTRIM(ISNULL(cd.ID_PRODUCTO, ''))               AS codigo,
            RTRIM(ISNULL(cd.DESCRIPCION,  ''))              AS descripcion,
            ISNULL(cd.CANTIDAD,        0)                   AS cantidad,
            ISNULL(cd.COSTO_UNITARIO,  0)                   AS costo_unitario,
            ISNULL(cd.IMPORTE,         0)                   AS importe
        FROM COMPRAS_DETALLE cd
        WHERE cd.DOCUMENTO_ID = ?
        ORDER BY cd.LINEA
    """
    try:
        return ejecutar_query(sql, (documento_id,))
    except Exception as e:
        print(f"[LineasCompra] {e}")
        return []


def get_documentos_proveedor(proveedor_id: int) -> list:
    """
    Facturas pendientes de un proveedor usando ETransacP.
    Muestra MONTO original y SALDO_DOC actual (saldo restante por pagar).
    """
    sql = """
        SELECT
            ep.ID_DOCUMENTO                                         AS documento_id,
            RTRIM(ISNULL(c.FACTURA, ''))                           AS factura,
            CONVERT(varchar(10), ep.FECHA,       103)              AS fecha,
            CONVERT(varchar(10), ep.FECHA_VENCE, 103)              AS fecha_vence,
            DATEDIFF(day,
                CAST(GETDATE()       AS date),
                CAST(ep.FECHA_VENCE  AS date))                     AS dias_vence,
            ISNULL(ep.MONTO,     0)                                AS monto,
            ISNULL(ep.SALDO_DOC, 0)                                AS saldo,
            RTRIM(ISNULL(ep.ID_MONEDA, 'COL'))                     AS moneda,
            ISNULL(ep.TIPO_CAMBIO, 1)                              AS tipo_cambio
        FROM ETransacP ep
        LEFT JOIN COMPRAS c
            ON  c.DOCUMENTO_ID = ep.ID_DOCUMENTO
            AND c.ID_TIPODOC   = ep.ID_TIPODOC
        WHERE ep.PROVEEDOR_ID = ?
          AND ep.ID_CONCEPTO  = '01'
          AND ep.STATUS       = 'A'
          AND ep.SALDO_DOC    > 0
        ORDER BY ep.FECHA_VENCE ASC
    """
    try:
        return ejecutar_query(sql, (proveedor_id,))
    except Exception as e:
        print(f"[CxP docs] {e}")
        return []
