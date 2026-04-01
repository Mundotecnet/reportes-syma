from db import ejecutar_query, get_connection

ESTADOS_TALLER = {
    1: "Pendiente",
    2: "En proceso",
    3: "Finalizado",
    4: "Facturado",
    5: "No Reparable",
}


def get_siguiente_no_orden() -> int:
    rows = ejecutar_query("SELECT ISNULL(MAX(NO_ORDEN),0)+1 AS sig FROM ORDEN_SERVICIO")
    return int(rows[0]["sig"]) if rows else 1


def buscar_clientes(busqueda: str) -> list:
    sql = """
        SELECT TOP 15
            CLIENTE_ID                          AS cliente_id,
            RTRIM(ISNULL(NOMBRE,  ''))          AS nombre,
            RTRIM(ISNULL(TELEFONO,''))          AS telefono,
            RTRIM(ISNULL(CEDULA,  ''))          AS cedula,
            RTRIM(ISNULL(CORREO,  ''))          AS correo
        FROM Clientes
        WHERE NOMBRE  LIKE ? OR CEDULA LIKE ? OR TELEFONO LIKE ?
        ORDER BY NOMBRE
    """
    b = f"%{busqueda}%"
    try:
        return ejecutar_query(sql, (b, b, b))
    except Exception as e:
        print(f"[BuscarClientes] {e}")
        return []


def get_agenda_mes(year: int, month: int) -> list:
    """Devuelve conteo de órdenes por día para el mes/año indicado."""
    sql = """
        SELECT
            CAST(FECHA AS date)                         AS dia,
            COUNT(*)                                    AS total,
            SUM(CASE WHEN ESTADO = 1 THEN 1 ELSE 0 END) AS pendientes,
            SUM(CASE WHEN ESTADO = 2 THEN 1 ELSE 0 END) AS en_proceso,
            SUM(CASE WHEN ESTADO IN (3,4) THEN 1 ELSE 0 END) AS finalizadas
        FROM ORDEN_SERVICIO
        WHERE YEAR(FECHA) = ? AND MONTH(FECHA) = ?
        GROUP BY CAST(FECHA AS date)
        ORDER BY dia
    """
    try:
        rows = ejecutar_query(sql, (year, month))
        return [
            {
                "dia":        str(r["dia"]),
                "total":      int(r["total"]      or 0),
                "pendientes": int(r["pendientes"] or 0),
                "en_proceso": int(r["en_proceso"] or 0),
                "finalizadas":int(r["finalizadas"]or 0),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[AgendaMes] {e}")
        return []


def get_agenda_dia(fecha: str) -> list:
    """Órdenes programadas para una fecha — para verificar disponibilidad al ingresar."""
    sql = """
        SELECT
            os.NO_ORDEN                                     AS no_orden,
            ISNULL(os.SECUENCIA_DIA, 0)                     AS secuencia_dia,
            CONVERT(varchar(5), os.HORA_ENTRADA, 108)       AS hora_entrada,
            CONVERT(varchar(5), os.HORA_SALIDA,  108)       AS hora_salida,
            RTRIM(ISNULL(os.NOMBRE_CLIENTE,  ''))           AS cliente,
            RTRIM(ISNULL(os.MAQUINA,         ''))           AS maquina,
            RTRIM(ISNULL(os.MARCA,           ''))           AS marca,
            RTRIM(ISNULL(os.NOMBRE_REPARADOR,''))           AS reparador,
            os.ESTADO                                       AS estado,
            CONVERT(varchar(10), os.FECHA_REGISTRO, 103)    AS fecha_registro,
            DATEDIFF(day, os.FECHA_REGISTRO,
                CASE WHEN os.ESTADO IN (3,4,5)
                     THEN ISNULL(os.FECHA_ESTADO, GETDATE())
                     ELSE GETDATE() END)                    AS dias_abierta
        FROM ORDEN_SERVICIO os
        WHERE CAST(os.FECHA AS date) = ?
        ORDER BY ISNULL(os.SECUENCIA_DIA, 9999), os.HORA_ENTRADA, os.NO_ORDEN
    """
    try:
        rows = ejecutar_query(sql, (fecha,))
        for r in rows:
            r["estado_label"] = ESTADOS_TALLER.get(int(r["estado"] or 0), str(r["estado"]))
        return rows
    except Exception as e:
        print(f"[AgendaDia] {e}")
        return []


def crear_orden(data: dict, usuario: str) -> dict:
    """
    Inserta una nueva orden de servicio en ORDEN_SERVICIO.
    Retorna {"ok": True, "no_orden": N} o {"ok": False, "error": "..."}.
    """
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        # Siguiente número (dentro de la misma transacción para evitar colisiones)
        cursor.execute("SELECT ISNULL(MAX(NO_ORDEN),0)+1 FROM ORDEN_SERVICIO")
        no_orden = int(cursor.fetchone()[0])

        cursor.execute("""
            INSERT INTO ORDEN_SERVICIO (
                NO_ORDEN, FECHA, TIPO_ID, UBICACION,
                MAQUINA, MARCA, MODELO, SERIE,
                ACCESORIOS, ESTADO_INGRESO, NO_TRAE, OBSERVACIONES,
                HORA_ENTRADA, HORA_SALIDA,
                CLIENTE_ID, NOMBRE_CLIENTE, TELEFONO, CEDULA, CORREO,
                NOMBRE_REPARADOR, KILOMETRAJE,
                ESTADO, FECHA_REGISTRO
            ) VALUES (
                ?, GETDATE(), ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?,
                1, GETDATE()
            )
        """, (
            no_orden,
            int(data.get("tipo_id") or 1),
            data.get("ubicacion") or None,
            data.get("maquina")   or None,
            data.get("marca")     or None,
            data.get("modelo")    or None,
            data.get("serie")     or None,
            data.get("accesorios")     or None,
            data.get("estado_ingreso") or None,
            data.get("problema")       or None,
            data.get("observaciones")  or None,
            data.get("hora_entrada") or None,
            data.get("hora_salida")  or None,
            int(data["cliente_id"]) if data.get("cliente_id") else None,
            data.get("nombre_cliente") or None,
            data.get("telefono")       or None,
            data.get("cedula")         or None,
            data.get("correo")         or None,
            data.get("reparador")      or None,
            float(data["kilometraje"]) if data.get("kilometraje") else None,
        ))
        conn.commit()
        return {"ok": True, "no_orden": no_orden}
    except Exception as e:
        conn.rollback()
        print(f"[CrearOrden] {e}")
        return {"ok": False, "error": str(e)}
    finally:
        cursor.close()
        conn.close()


def get_ordenes_antiguas(year: int, month: int) -> list:
    """
    Órdenes abiertas (Pendiente o En proceso) cuya FECHA es anterior
    al primer día del mes/año indicado. Se usan como backlog en la agenda.
    """
    sql = """
        SELECT
            os.NO_ORDEN                                         AS no_orden,
            CONVERT(varchar(10), os.FECHA, 103)                 AS fecha,
            RTRIM(ISNULL(os.NOMBRE_CLIENTE,  ''))               AS cliente,
            RTRIM(ISNULL(os.MAQUINA,         ''))               AS maquina,
            RTRIM(ISNULL(os.MARCA,           ''))               AS marca,
            RTRIM(ISNULL(os.MODELO,          ''))               AS modelo,
            RTRIM(ISNULL(os.NOMBRE_REPARADOR,''))               AS reparador,
            RTRIM(ISNULL(os.NO_TRAE,         ''))               AS problema,
            os.ESTADO                                           AS estado,
            CONVERT(varchar(10), os.FECHA_REGISTRO, 103)        AS fecha_registro,
            DATEDIFF(day, os.FECHA_REGISTRO, GETDATE())         AS dias_abierta
        FROM ORDEN_SERVICIO os
        WHERE os.ESTADO IN (1, 2)
          AND CAST(os.FECHA AS date) < DATEFROMPARTS(?, ?, 1)
        ORDER BY os.FECHA ASC, os.NO_ORDEN ASC
    """
    try:
        rows = ejecutar_query(sql, (year, month))
        for r in rows:
            r["estado_label"] = ESTADOS_TALLER.get(int(r["estado"] or 0), str(r["estado"]))
        return rows
    except Exception as e:
        print(f"[OrdenesAntiguas] {e}")
        return []


def reordenar_dia(ordenes: list) -> dict:
    """
    Actualiza SECUENCIA_DIA para una lista de órdenes.
    ordenes = [{no_orden: int, secuencia: int}, ...]
    """
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        for item in ordenes:
            cursor.execute(
                "UPDATE ORDEN_SERVICIO SET SECUENCIA_DIA = ? WHERE NO_ORDEN = ?",
                (item["secuencia"], item["no_orden"])
            )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        print(f"[ReordenarDia] {e}")
        return {"ok": False, "error": str(e)}
    finally:
        cursor.close()
        conn.close()


def mover_orden(no_orden: int, nueva_fecha: str) -> dict:
    """Cambia la fecha de una orden preservando la hora original."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE ORDEN_SERVICIO
               SET FECHA = DATEADD(day, DATEDIFF(day, FECHA, CONVERT(datetime, ?)), FECHA)
               WHERE NO_ORDEN = ?""",
            (nueva_fecha, no_orden)
        )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        print(f"[MoverOrden] {e}")
        return {"ok": False, "error": str(e)}
    finally:
        cursor.close()
        conn.close()


def get_taller(
    fecha_ini:    str,
    fecha_fin:    str,
    tipo_id:      str = "",
    estado:       str = "",
    busqueda:     str = "",
    filtro_fecha: str = "ingreso",   # "ingreso" = FECHA | "estado" = FECHA_ESTADO
) -> list:
    campo_fecha = "os.FECHA_ESTADO" if filtro_fecha == "estado" else "os.FECHA"
    filtros = [f"CAST({campo_fecha} AS date) BETWEEN ? AND ?"]
    params  = [fecha_ini, fecha_fin]

    if tipo_id:
        filtros.append("os.TIPO_ID = ?")
        params.append(int(tipo_id))

    if estado:
        filtros.append("os.ESTADO = ?")
        params.append(int(estado))

    if busqueda:
        filtros.append(
            "(os.NOMBRE_CLIENTE LIKE ? OR os.MAQUINA LIKE ? "
            " OR os.MARCA LIKE ? OR os.MODELO LIKE ?)"
        )
        params.extend([f"%{busqueda}%"] * 4)

    where = " AND ".join(filtros)

    sql = f"""
        SELECT
            os.NO_ORDEN                                             AS no_orden,
            CONVERT(varchar(10), os.FECHA, 103)                     AS fecha,
            CONVERT(varchar(5),  os.FECHA, 108)                     AS hora,
            os.TIPO_ID                                              AS tipo_id,
            RTRIM(ISNULL(ost.TIPO_NOMBRE, ''))                      AS tipo,
            RTRIM(ISNULL(os.NOMBRE_CLIENTE, ''))                    AS cliente,
            RTRIM(ISNULL(os.TELEFONO, ''))                          AS telefono,
            RTRIM(ISNULL(os.CEDULA, ''))                            AS cedula,
            RTRIM(ISNULL(os.MAQUINA, ''))                           AS maquina,
            RTRIM(ISNULL(os.MARCA, ''))                             AS marca,
            RTRIM(ISNULL(os.MODELO, ''))                            AS modelo,
            ISNULL(os.KILOMETRAJE, 0)                               AS kilometraje,
            RTRIM(ISNULL(os.NOMBRE_REPARADOR, ''))                  AS reparador,
            RTRIM(ISNULL(os.NOMBRE_AUTORIZADO, ''))                 AS autorizado,
            os.ESTADO                                               AS estado,
            RTRIM(ISNULL(os.OBSERVACIONES, ''))                     AS observaciones,
            CONVERT(varchar(10), os.FECHA_REGISTRO, 103)            AS fecha_registro,
            DATEDIFF(day, os.FECHA_REGISTRO,
                CASE WHEN os.ESTADO IN (3,4,5)
                     THEN ISNULL(os.FECHA_ESTADO, GETDATE())
                     ELSE GETDATE() END)                            AS dias_abierta,
            ISNULL(d.num_lineas,  0)                                AS num_lineas,
            ISNULL(d.total_orden, 0)                                AS total,
            ISNULL(st.total_st003, 0)                               AS total_servicio,
            RTRIM(ISNULL(st.desc_st003, ''))                        AS desc_servicio
        FROM ORDEN_SERVICIO os
        LEFT JOIN ORDEN_SERVICIO_TIPOS ost ON ost.TIPO_ID = os.TIPO_ID
        LEFT JOIN (
            SELECT
                NO_ORDEN,
                COUNT(*)                                            AS num_lineas,
                SUM(ISNULL(CANTIDAD,0) * ISNULL(PRECIO,0))         AS total_orden
            FROM ORDEN_SERVICIO_DETALLE
            WHERE ESTADO = 'A'
            GROUP BY NO_ORDEN
        ) d ON d.NO_ORDEN = os.NO_ORDEN
        LEFT JOIN (
            SELECT
                NO_ORDEN,
                SUM(ISNULL(CANTIDAD,0) * ISNULL(PRECIO,0))         AS total_st003,
                MAX(RTRIM(ISNULL(DESCRIPCION_SERVICIO,'')))         AS desc_st003
            FROM ORDEN_SERVICIO_DETALLE
            WHERE UPPER(RTRIM(ID_PRODUCTO)) = 'ST003' AND ESTADO = 'A'
            GROUP BY NO_ORDEN
        ) st ON st.NO_ORDEN = os.NO_ORDEN
        WHERE {where}
        ORDER BY os.FECHA DESC, os.NO_ORDEN DESC
    """
    try:
        rows = ejecutar_query(sql, tuple(params))
        # Agregar etiqueta de estado
        for r in rows:
            r["estado_label"] = ESTADOS_TALLER.get(int(r["estado"] or 0), str(r["estado"]))
        return rows
    except Exception as e:
        print(f"[Taller] {e}")
        return []


def get_orden_completa(no_orden: int) -> dict | None:
    sql = """
        SELECT
            os.NO_ORDEN                                         AS no_orden,
            CONVERT(varchar(10), os.FECHA, 103)                 AS fecha,
            os.TIPO_ID                                          AS tipo_id,
            RTRIM(ISNULL(ost.TIPO_NOMBRE, ''))                  AS tipo,
            RTRIM(ISNULL(os.UBICACION,         ''))             AS ubicacion,
            RTRIM(ISNULL(os.MAQUINA,           ''))             AS maquina,
            RTRIM(ISNULL(os.MARCA,             ''))             AS marca,
            RTRIM(ISNULL(os.MODELO,            ''))             AS modelo,
            RTRIM(ISNULL(os.SERIE,             ''))             AS serie,
            RTRIM(ISNULL(os.ACCESORIOS,        ''))             AS accesorios,
            RTRIM(ISNULL(os.ESTADO_INGRESO,    ''))             AS estado_ingreso,
            RTRIM(ISNULL(os.NO_TRAE,           ''))             AS problema,
            RTRIM(ISNULL(os.OBSERVACIONES,     ''))             AS observaciones,
            CONVERT(varchar(5), os.HORA_ENTRADA, 108)           AS hora_entrada,
            CONVERT(varchar(5), os.HORA_SALIDA,  108)           AS hora_salida,
            RTRIM(ISNULL(os.NOMBRE_CLIENTE,    ''))             AS nombre_cliente,
            RTRIM(ISNULL(os.CEDULA,            ''))             AS cedula,
            RTRIM(ISNULL(os.TELEFONO,          ''))             AS telefono,
            RTRIM(ISNULL(os.CORREO,            ''))             AS correo,
            RTRIM(ISNULL(os.NOMBRE_REPARADOR,  ''))             AS reparador,
            os.ESTADO                                           AS estado,
            CONVERT(varchar(10), os.FECHA_REGISTRO, 103)        AS fecha_registro,
            DATEDIFF(day, os.FECHA_REGISTRO,
                CASE WHEN os.ESTADO IN (3,4,5)
                     THEN ISNULL(os.FECHA_ESTADO, GETDATE())
                     ELSE GETDATE() END)                        AS dias_abierta
        FROM ORDEN_SERVICIO os
        LEFT JOIN ORDEN_SERVICIO_TIPOS ost ON ost.TIPO_ID = os.TIPO_ID
        WHERE os.NO_ORDEN = ?
    """
    try:
        rows = ejecutar_query(sql, (no_orden,))
        if rows:
            r = rows[0]
            r["estado_label"] = ESTADOS_TALLER.get(int(r["estado"] or 0), str(r["estado"]))
            return r
        return None
    except Exception as e:
        print(f"[OrdenCompleta] {e}")
        return None


def get_servicios_st003(fecha_ini: str, fecha_fin: str) -> list:
    """
    Líneas de servicio ST003/ST001 facturadas en punto_venta para el rango dado.
    Una fila por línea de detalle.
    """
    sql = """
        SELECT
            CONVERT(varchar(10), pv.FECHA, 103)                         AS fecha,
            pv.ID_DOCUMENTO                                             AS num_doc,
            CASE pv.ID_TIPODOC
                WHEN '02' THEN 'Factura'
                WHEN '04' THEN 'Tiquete'
                ELSE RTRIM(pv.ID_TIPODOC)
            END                                                         AS tipo_doc,
            RTRIM(ISNULL(pv.NOMBRE,          ''))                       AS cliente,
            RTRIM(ISNULL(pv.CEDULA,          ''))                       AS cedula,
            UPPER(RTRIM(pvd.ID_PRODUCTO))                               AS codigo,
            RTRIM(ISNULL(pvd.DESCRIPCION,    ''))                       AS descripcion,
            ISNULL(pvd.CANTIDAD, 0)                                     AS cantidad,
            ISNULL(pvd.PRECIO,   0)                                     AS precio_unit,
            ISNULL(pvd.IMPORTE,  0)                                     AS importe,
            ISNULL(pvd.MONTO_IMP,0)                                     AS iva,
            ISNULL(pvd.IMPORTE, 0) + ISNULL(pvd.MONTO_IMP, 0)          AS total
        FROM PUNTO_VENTA_DETALLE pvd
        INNER JOIN PUNTO_VENTA pv
            ON  pv.ID_DOCUMENTO = pvd.ID_DOCUMENTO
            AND pv.ID_TIPODOC   = pvd.ID_TIPODOC
            AND pv.ID_CONCEPTO  = pvd.ID_CONCEPTO
        WHERE CAST(pv.FECHA AS date) BETWEEN ? AND ?
          AND pv.ESTADO = 'A'
          AND UPPER(RTRIM(pvd.ID_PRODUCTO)) = 'ST003'
        ORDER BY pv.FECHA DESC, pv.ID_DOCUMENTO DESC
    """
    try:
        return ejecutar_query(sql, (fecha_ini, fecha_fin))
    except Exception as e:
        print(f"[ServiciosST003] {e}")
        return []


def get_detalle_taller(no_orden: int) -> list:
    sql = """
        SELECT
            d.NO_LINEA                                              AS no_linea,
            RTRIM(ISNULL(d.ID_PRODUCTO,          ''))               AS id_producto,
            RTRIM(ISNULL(d.DESCRIPCION_SERVICIO, ''))               AS descripcion,
            ISNULL(d.CANTIDAD, 0)                                   AS cantidad,
            ISNULL(d.PRECIO,   0)                                   AS precio,
            ISNULL(d.CANTIDAD, 0) * ISNULL(d.PRECIO, 0)            AS subtotal
        FROM ORDEN_SERVICIO_DETALLE d
        WHERE d.NO_ORDEN = ?
          AND d.ESTADO   = 'A'
        ORDER BY d.NO_LINEA
    """
    try:
        return ejecutar_query(sql, (no_orden,))
    except Exception as e:
        print(f"[DetalleTaller] {e}")
        return []
