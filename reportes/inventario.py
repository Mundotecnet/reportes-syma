from db import ejecutar_query


def get_inventario(categoria: str = "", estado_stock: str = "todos", busqueda: str = "", ind_series: str = ""):
    """
    Reporte de inventario desde PRODUCTOS.
    estado_stock: 'todos' | 'con_stock' | 'sin_stock' | 'bajo_minimo'
    """
    filtros = ["p.ESTADO = 'A'"]
    params  = []

    if categoria:
        filtros.append("p.ID_CATEGORIA = ?")
        params.append(categoria)

    if estado_stock == "con_stock":
        filtros.append("p.CANTIDAD > 0")
    elif estado_stock == "sin_stock":
        filtros.append("p.CANTIDAD <= 0")
    elif estado_stock == "bajo_minimo":
        filtros.append("p.CANTIDAD > 0")
        filtros.append("p.STOCK_MINIMO > 0")
        filtros.append("p.CANTIDAD < p.STOCK_MINIMO")

    if ind_series in ("S", "N"):
        filtros.append("p.IND_SERIES = ?")
        params.append(ind_series)

    if busqueda:
        filtros.append("(p.ID_PRODUCTO LIKE ? OR p.DESCRIPCION LIKE ?)")
        params.append(f"%{busqueda}%")
        params.append(f"%{busqueda}%")

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            RTRIM(p.ID_PRODUCTO)                        AS codigo,
            RTRIM(p.DESCRIPCION)                        AS descripcion,
            RTRIM(ISNULL(p.UNIDAD_MEDIDA, ''))          AS unidad,
            ISNULL(p.CANTIDAD,       0)                 AS cantidad,
            ISNULL(p.STOCK_MINIMO,   0)                 AS stock_min,
            ISNULL(p.PUNTO_REORDEN,  0)                 AS reorden,
            ISNULL(p.COSTOUNI,       0)                 AS costo_unit,
            ISNULL(p.COSTO_PROMEDIO, 0)                 AS costo_prom,
            ISNULL(p.PRECIO,         0)                 AS precio,
            ISNULL(p.PRECIO_IVI,     0)                 AS precio_ivi,
            ISNULL(p.PORC_IMP,       0)                 AS porc_imp,
            ISNULL(p.CANTIDAD, 0) * ISNULL(p.COSTO_PROMEDIO, 0) AS valor_inv,
            RTRIM(ISNULL(p.ID_CATEGORIA, ''))           AS id_categoria,
            RTRIM(ISNULL(cat.CATEGORIA,  ''))           AS categoria,
            RTRIM(ISNULL(sub.SUBCATEGORIA, ''))         AS subcategoria,
            RTRIM(ISNULL(prov.NOMBRE, ''))              AS proveedor,
            RTRIM(ISNULL(p.UBICACION_ID, ''))           AS ubicacion,
            ISNULL(p.IND_SERIES, 'N')                  AS ind_series,
            (SELECT COUNT(*) FROM PRODUCTOS_SERIES ps
             WHERE ps.ID_PRODUCTO = p.ID_PRODUCTO
               AND ps.IND_ESTADO  = 'A')              AS num_seriales,
            CASE
                WHEN ISNULL(p.CANTIDAD, 0) <= 0                          THEN 'sin_stock'
                WHEN p.STOCK_MINIMO > 0 AND p.CANTIDAD < p.STOCK_MINIMO  THEN 'bajo_min'
                ELSE 'ok'
            END                                         AS estado_stock
        FROM PRODUCTOS p
        LEFT JOIN CategoriaProductos    cat  ON cat.ID_CATEGORIA  = p.ID_CATEGORIA
        LEFT JOIN SubCategoriaProductos sub  ON sub.ID_CATEGORIA  = p.ID_CATEGORIA
                                            AND sub.ID_SUBCATEGORIA = p.ID_SUBCATEGORIA
        LEFT JOIN Proveedores           prov ON prov.PROVEEDOR_ID = p.PROVEEDOR_ID
        WHERE {where}
        ORDER BY p.DESCRIPCION
    """
    return ejecutar_query(sql, tuple(params))


def get_seriales_producto(id_producto: str) -> list:
    """Seriales disponibles de un producto desde PRODUCTOS_SERIES."""
    sql = """
        SELECT
            RTRIM(ps.SERIE)                             AS serie,
            CONVERT(varchar(10), ps.FECHA_ENT, 103)     AS fecha_entrada,
            ISNULL(ps.DOC_ENTRADA, 0)                   AS doc_entrada,
            RTRIM(ISNULL(ps.UBICACION_ID, ''))          AS ubicacion
        FROM PRODUCTOS_SERIES ps
        WHERE ps.ID_PRODUCTO  = ?
          AND ps.IND_ESTADO   = 'A'
        ORDER BY ps.FECHA_ENT DESC, ps.SERIE
    """
    try:
        return ejecutar_query(sql, (id_producto,))
    except Exception as e:
        print(f"[Inventario seriales] {e}")
        return []


def get_categorias_producto():
    sql = """
        SELECT ID_CATEGORIA, RTRIM(CATEGORIA) AS CATEGORIA
        FROM CategoriaProductos
        ORDER BY CATEGORIA
    """
    return ejecutar_query(sql)
