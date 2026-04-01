from db import ejecutar_query, get_connection


def get_inventario_ajustes(
    fecha_ini:    str,
    fecha_fin:    str,
    categoria:    str = "",
    estado_stock: str = "todos",
    busqueda:     str = "",
    ind_series:   str = "",
) -> list:
    """
    Productos que tuvieron ventas en el rango de fechas dado.
    Muestra el inventario actual + cantidad vendida en el período,
    ordenado por mayor rotación primero — para priorizar conteo físico.
    """
    filtros = ["p.ESTADO = 'A'", "v.CODIGO_ID IS NOT NULL"]
    params  = [fecha_ini, fecha_fin]   # usados en el subquery

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
            p.CODIGO_ID                                 AS codigo_id,
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
               AND ps.IND_ESTADO  = 'A')               AS num_seriales,
            CASE
                WHEN ISNULL(p.CANTIDAD, 0) <= 0                          THEN 'sin_stock'
                WHEN p.STOCK_MINIMO > 0 AND p.CANTIDAD < p.STOCK_MINIMO  THEN 'bajo_min'
                ELSE 'ok'
            END                                         AS estado_stock,

            -- Datos de ventas en el período
            ISNULL(v.cant_vendida,  0)                  AS cant_vendida,
            ISNULL(v.num_facturas,  0)                  AS num_facturas,
            ISNULL(v.ult_venta,    '')                  AS ult_venta

        FROM PRODUCTOS p
        LEFT JOIN (
            SELECT
                pvd.CODIGO_ID,
                SUM(pvd.CANTIDAD)                       AS cant_vendida,
                COUNT(DISTINCT pv.ID_DOCUMENTO)         AS num_facturas,
                CONVERT(varchar(10), MAX(pv.FECHA), 103) AS ult_venta
            FROM PUNTO_VENTA_DETALLE pvd
            JOIN PUNTO_VENTA pv
                ON  pv.ID_DOCUMENTO = pvd.ID_DOCUMENTO
                AND pv.ID_TIPODOC   = pvd.ID_TIPODOC
                AND pv.ID_CONCEPTO  = pvd.ID_CONCEPTO
            WHERE CAST(pv.FECHA AS date) BETWEEN ? AND ?
              AND pv.ESTADO = 'A'
            GROUP BY pvd.CODIGO_ID
        ) v ON v.CODIGO_ID = p.CODIGO_ID
        LEFT JOIN CategoriaProductos    cat  ON cat.ID_CATEGORIA  = p.ID_CATEGORIA
        LEFT JOIN SubCategoriaProductos sub  ON sub.ID_CATEGORIA  = p.ID_CATEGORIA
                                            AND sub.ID_SUBCATEGORIA = p.ID_SUBCATEGORIA
        LEFT JOIN Proveedores           prov ON prov.PROVEEDOR_ID = p.PROVEEDOR_ID
        WHERE {where}
        ORDER BY v.cant_vendida DESC, p.DESCRIPCION
    """
    try:
        return ejecutar_query(sql, tuple(params))
    except Exception as e:
        print(f"[InventarioAjustes] {e}")
        return []


def get_historial_ajustes(
    fecha_ini: str,
    fecha_fin: str,
    usuario:   str = "",
) -> list:
    """
    Devuelve los ajustes de inventario registrados en el período.
    Solo ID_TIPODOC 03 (entrada) y 04 (salida) con concepto 06/08.
    """
    params  = [fecha_ini, fecha_fin]
    filtros = ["it.ID_TIPODOC IN ('03','04')",
               "it.ID_CONCEPTO IN ('06','08')",
               "CAST(it.FECHA AS date) BETWEEN ? AND ?"]

    if usuario:
        filtros.append("RTRIM(it.ID_USER) = ?")
        params.append(usuario)

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            it.ID_DOCUMENTO                                     AS id_documento,
            it.ID_TIPODOC                                       AS id_tipodoc,
            CASE it.ID_TIPODOC WHEN '03' THEN 'Entrada'
                               ELSE           'Salida' END      AS tipo,
            it.ID_CONCEPTO                                      AS id_concepto,
            CONVERT(varchar(10), it.FECHA, 103)                 AS fecha,
            CONVERT(varchar(5),  it.FECHA, 108)                 AS hora,
            RTRIM(ISNULL(it.OBSERVACIONES, ''))                 AS observaciones,
            RTRIM(ISNULL(it.ID_USER, ''))                       AS usuario,
            it.ESTADO                                           AS estado,
            ISNULL(d.num_lineas,    0)                          AS num_lineas,
            ISNULL(d.total_unidades,0)                          AS total_unidades
        FROM INVENTARIO_TRANS it
        LEFT JOIN (
            SELECT ID_DOCUMENTO, ID_TIPODOC, ID_CONCEPTO,
                   COUNT(*)       AS num_lineas,
                   SUM(CANTIDAD)  AS total_unidades
            FROM   INVENTARIO_TRANS_DETALLE
            GROUP  BY ID_DOCUMENTO, ID_TIPODOC, ID_CONCEPTO
        ) d ON  d.ID_DOCUMENTO = it.ID_DOCUMENTO
            AND d.ID_TIPODOC   = it.ID_TIPODOC
            AND d.ID_CONCEPTO  = it.ID_CONCEPTO
        WHERE {where}
        ORDER BY it.FECHA DESC, it.ID_DOCUMENTO DESC
    """
    try:
        return ejecutar_query(sql, tuple(params))
    except Exception as e:
        print(f"[HistorialAjustes] {e}")
        return []


def get_detalle_ajuste(id_documento: int, id_tipodoc: str, id_concepto: str) -> list:
    """
    Devuelve las líneas de detalle de un documento de ajuste.
    """
    sql = """
        SELECT
            RTRIM(d.ID_PRODUCTO)                            AS id_producto,
            RTRIM(ISNULL(p.DESCRIPCION,   ''))              AS descripcion,
            RTRIM(ISNULL(p.UNIDAD_MEDIDA, ''))              AS unidad,
            d.CANTIDAD                                      AS cantidad,
            ISNULL(d.TIPO_CAMBIO, 0)                        AS costo,
            d.CANTIDAD * ISNULL(d.TIPO_CAMBIO, 0)           AS valor
        FROM   INVENTARIO_TRANS_DETALLE d
        LEFT JOIN PRODUCTOS p ON p.ID_PRODUCTO = d.ID_PRODUCTO
        WHERE  d.ID_DOCUMENTO = ?
          AND  d.ID_TIPODOC   = ?
          AND  d.ID_CONCEPTO  = ?
        ORDER  BY p.DESCRIPCION
    """
    try:
        return ejecutar_query(sql, (id_documento, id_tipodoc, id_concepto))
    except Exception as e:
        print(f"[DetalleAjuste] {e}")
        return []


def aplicar_ajuste_fisico(items: list, usuario: str, observaciones: str) -> dict:
    """
    Aplica ajuste físico de inventario directo a tablas (sin proc encriptado).
    items = [{"id_producto":"106074","codigo_id":1234,"conteo":119,
              "sistema":117,"costo_prom":338.0}, ...]

    Escribe en:
      INVENTARIO_TRANS         → cabezal (1 fila por dirección)
      INVENTARIO_TRANS_DETALLE → detalle (1 fila por producto)
      PRODUCTOS.CANTIDAD       → nuevo saldo
    """
    if not items:
        return {"ok": False, "error": "No hay ítems para ajustar"}

    # ID_CONCEPTO según catálogo Conceptos:
    #   '03'+'06' → "Ajustes"           → ENTRADA por conteo físico
    #   '04'+'08' → "SALIDA POR AJUSTE" → SALIDA  por conteo físico
    CONCEPTO = {'03': '06', '04': '08'}

    entradas = [i for i in items if float(i["conteo"]) > float(i["sistema"])]
    salidas  = [i for i in items if float(i["conteo"]) < float(i["sistema"])]

    if not entradas and not salidas:
        return {"ok": False, "error": "Ningún ítem tiene diferencia de conteo"}

    # ── Una sola conexión / una sola transacción (atómica) ──────────────────
    # Si entradas o salidas falla → rollback deshace AMBOS grupos.
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        doc_ent = None
        doc_sal = None

        def insertar_grupo(tipodoc: str, grupo: list) -> int:
            """
            Registra cabezal + detalle y dispara el trigger para un grupo.
            Trabaja sobre la conexión/transacción compartida del llamador.
            ID_DOCUMENTO = MAX por ID_TIPODOC + 1 (numeración independiente
            por tipo de movimiento, calculada dentro de la misma transacción).
            """
            concepto = CONCEPTO[tipodoc]

            # Siguiente número de documento para este tipo de movimiento
            cursor.execute(
                "SELECT ISNULL(MAX(ID_DOCUMENTO), 0) + 1 "
                "FROM INVENTARIO_TRANS WHERE ID_TIPODOC = ?",
                (tipodoc,)
            )
            doc_id = int(cursor.fetchone()[0])

            # 1. Cabezal con ESTADO='N' → trigger NO actúa todavía
            cursor.execute("""
                INSERT INTO INVENTARIO_TRANS
                    (ID_DOCUMENTO, ID_TIPODOC, ID_CONCEPTO, FECHA,
                     OBSERVACIONES, ID_USER, FECHA_REGISTRO, ESTADO, ORIGEN, DESTINO)
                VALUES (?, ?, ?, GETDATE(), ?, ?, GETDATE(), 'P', '01', '01')
            """, (doc_id, tipodoc, concepto, observaciones, usuario))

            # 2. Detalle — una línea por producto, misma llave primaria del cabezal
            #    CANTIDAD siempre positiva; ID_TIPODOC determina si suma o resta
            for item in grupo:
                dif = abs(float(item["conteo"]) - float(item["sistema"]))
                cursor.execute("""
                    INSERT INTO INVENTARIO_TRANS_DETALLE
                        (ID_DOCUMENTO, ID_TIPODOC, ID_CONCEPTO,
                         CODIGO_ID, ID_PRODUCTO, CANTIDAD, SERIE, TIPO_CAMBIO)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
                """, (doc_id, tipodoc, concepto,
                      int(item["codigo_id"]), item["id_producto"],
                      dif, float(item["costo_prom"])))

            # 3. UPDATE a ESTADO='A' → trigger Aplicar_Transaccion dispara
            #    El trigger usa ID_TIPODOC: '03' suma, '04' resta en PRODUCTOS.CANTIDAD
            cursor.execute("""
                UPDATE INVENTARIO_TRANS SET ESTADO = 'A'
                WHERE ID_DOCUMENTO = ? AND ID_TIPODOC = ? AND ID_CONCEPTO = ?
            """, (doc_id, tipodoc, concepto))

            return doc_id

        if entradas:
            doc_ent = insertar_grupo('03', entradas)
        if salidas:
            doc_sal = insertar_grupo('04', salidas)

        # Commit único — ambos grupos quedan confirmados juntos
        conn.commit()
        return {
            "ok":      True,
            "doc_ent": doc_ent,
            "doc_sal": doc_sal,
            "entradas": len(entradas),
            "salidas":  len(salidas),
            "total":    len(items),
        }

    except Exception as e:
        try:
            conn.rollback()   # deshace entradas Y salidas si alguno falló
        except Exception:
            pass
        print(f"[AjusteFisico] {e}")
        return {"ok": False, "error": str(e)}
    finally:
        cursor.close()
        conn.close()
