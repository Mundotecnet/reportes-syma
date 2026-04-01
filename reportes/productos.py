from db import ejecutar_query
from collections import defaultdict


def get_productos(fecha_ini: str, fecha_fin: str, estado: str = "A", busqueda: str = "", tipo_item: str = ""):
    """
    Reporte de productos vendidos agrupado por artículo.
    Devuelve lista de productos con totales y, dentro de cada uno,
    el detalle de los documentos de origen en 'detalles'.

    Tablas: PUNTO_VENTA (cabecera) + PUNTO_VENTA_DETALLE (líneas) + PRODUCTOS (catálogo)
    Columnas clave del detalle:
      - IMPORTE   : subtotal de línea (CANTIDAD * PRECIO - DESCUENTO, sin IVA)
      - MONTO_IMP : monto de IVA de la línea
      - DESCUENTO : descuento aplicado en la línea
    """
    filtros = ["CAST(pv.FECHA AS date) BETWEEN ? AND ?"]
    params  = [fecha_ini, fecha_fin]

    if estado != "todos":
        filtros.append("pv.ESTADO = ?")
        params.append(estado)

    if busqueda:
        filtros.append("(pvd.ID_PRODUCTO LIKE ? OR ISNULL(pvd.DESCRIPCION, p.DESCRIPCION) LIKE ?)")
        term = f"%{busqueda}%"
        params.extend([term, term])

    if tipo_item in ("0", "1"):          # 0=Bien, 1=Servicio
        filtros.append("ISNULL(p.IND_BIEN_SERVICIO, 0) = ?")
        params.append(int(tipo_item))

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            pvd.ID_PRODUCTO                                         AS codigo,
            ISNULL(pvd.DESCRIPCION, p.DESCRIPCION)                  AS descripcion,
            ISNULL(p.UNIDAD_MEDIDA, '')                             AS unidad,
            pv.ID_DOCUMENTO                                         AS num_doc,
            CONVERT(varchar(10), pv.FECHA, 120)                     AS fecha,
            pv.NOMBRE                                               AS cliente,
            ISNULL(pvd.CANTIDAD,    0)                              AS cantidad,
            ISNULL(pvd.PRECIO,      0)                              AS precio_unit,
            ISNULL(pvd.DESCUENTO,   0)                              AS descuento,
            ISNULL(pvd.IMPORTE,     0)                              AS subtotal,
            ISNULL(pvd.MONTO_IMP,   0)                              AS iva,
            ISNULL(pvd.IMPORTE, 0) + ISNULL(pvd.MONTO_IMP, 0)      AS total
        FROM PUNTO_VENTA_DETALLE pvd
        INNER JOIN PUNTO_VENTA pv
            ON  pv.ID_DOCUMENTO = pvd.ID_DOCUMENTO
            AND pv.ID_TIPODOC   = pvd.ID_TIPODOC
            AND pv.ID_CONCEPTO  = pvd.ID_CONCEPTO
        LEFT JOIN PRODUCTOS p
            ON  p.CODIGO_ID = pvd.CODIGO_ID
        WHERE {where}
        ORDER BY descripcion, pv.FECHA DESC, pv.ID_DOCUMENTO DESC
    """
    filas = ejecutar_query(sql, tuple(params))

    # Agrupar por producto en Python
    grupos: dict = defaultdict(lambda: {
        "codigo": "", "descripcion": "", "unidad": "",
        "cantidad": 0.0, "subtotal": 0.0, "descuento": 0.0,
        "iva": 0.0, "total": 0.0, "detalles": []
    })

    for f in filas:
        key = f["codigo"] or f["descripcion"]
        g = grupos[key]
        g["codigo"]      = f["codigo"]
        g["descripcion"] = f["descripcion"]
        g["unidad"]      = f["unidad"]

        cant     = float(f["cantidad"]  or 0)
        subtotal = float(f["subtotal"]  or 0)
        desc     = float(f["descuento"] or 0)
        iva      = float(f["iva"]       or 0)
        total    = float(f["total"]     or 0)

        g["cantidad"]  += cant
        g["subtotal"]  += subtotal
        g["descuento"] += desc
        g["iva"]       += iva
        g["total"]     += total

        g["detalles"].append({
            "num_doc":    f["num_doc"],
            "fecha":      f["fecha"],
            "cliente":    f["cliente"],
            "cantidad":   cant,
            "precio_unit": float(f["precio_unit"] or 0),
            "descuento":  desc,
            "total":      total,
        })

    return sorted(grupos.values(), key=lambda x: x["descripcion"])
