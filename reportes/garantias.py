import os
from datetime import datetime
from db import ejecutar_query, get_connection

ARCHIVO_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'garantias')


def init_garantias():
    """Crea las tablas M_GARANTIAS y M_GARANTIAS_BITACORA si no existen, y el directorio de archivos."""
    os.makedirs(ARCHIVO_DIR, exist_ok=True)
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='M_GARANTIAS')
            CREATE TABLE M_GARANTIAS (
                ID                  INT IDENTITY(1,1) PRIMARY KEY,
                NO_ORDEN            INT NOT NULL,
                ESTADO              NVARCHAR(20)  NOT NULL DEFAULT 'Nuevo',
                NO_FACT_COMPRA      NVARCHAR(50)  NULL,
                FECHA_FACT_COMPRA   DATE          NULL,
                ARCHIVO_FACT_COMPRA NVARCHAR(500) NULL,
                NO_FACT_VENTA       NVARCHAR(50)  NULL,
                FECHA_FACT_VENTA    DATE          NULL,
                ARCHIVO_FACT_VENTA  NVARCHAR(500) NULL,
                NO_GUIA             NVARCHAR(100) NULL,
                TRANSPORTISTA       NVARCHAR(100) NULL,
                FECHA_ENVIO         DATE          NULL,
                ARCHIVO_GUIA        NVARCHAR(500) NULL,
                RESOLUCION          NVARCHAR(1000) NULL,
                FECHA_RESOLUCION    DATE          NULL,
                NOTAS               NVARCHAR(1000) NULL,
                USUARIO             NVARCHAR(100) NULL,
                CREADO_EN           DATETIME      DEFAULT GETDATE(),
                ACTUALIZADO_EN      DATETIME      NULL
            )
        """)
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='M_GARANTIAS_BITACORA')
            CREATE TABLE M_GARANTIAS_BITACORA (
                ID           INT IDENTITY(1,1) PRIMARY KEY,
                GARANTIA_ID  INT          NOT NULL,
                FECHA        DATETIME     NOT NULL DEFAULT GETDATE(),
                DETALLE      NVARCHAR(1000) NOT NULL,
                USUARIO      NVARCHAR(100) NULL
            )
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[Garantias init] {e}")
    finally:
        cur.close()
        conn.close()


# ── GARANTÍAS ────────────────────────────────────────────────────────────────

def get_garantias(estado: str = "", busqueda: str = "") -> list:
    """Lista garantías con datos de la orden de taller."""
    params = []
    where  = ["1=1"]
    if estado:
        where.append("g.ESTADO = ?")
        params.append(estado)
    if busqueda:
        b = f"%{busqueda}%"
        where.append("(o.NOMBRE_CLIENTE LIKE ? OR o.MAQUINA LIKE ? OR o.MARCA LIKE ? OR o.MODELO LIKE ? OR CAST(g.NO_ORDEN AS NVARCHAR) LIKE ?)")
        params.extend([b, b, b, b, b])

    filas = ejecutar_query(f"""
        SELECT
            g.ID, g.NO_ORDEN, g.ESTADO,
            g.NO_FACT_COMPRA, g.FECHA_FACT_COMPRA, g.ARCHIVO_FACT_COMPRA,
            g.NO_FACT_VENTA,  g.FECHA_FACT_VENTA,  g.ARCHIVO_FACT_VENTA,
            g.NO_GUIA, g.TRANSPORTISTA, g.FECHA_ENVIO, g.ARCHIVO_GUIA,
            g.RESOLUCION, g.FECHA_RESOLUCION,
            g.NOTAS, g.USUARIO, g.CREADO_EN, g.ACTUALIZADO_EN,
            o.NOMBRE_CLIENTE, o.MAQUINA, o.MARCA, o.MODELO,
            o.SERIE, o.NO_TRAE, o.FECHA_REGISTRO, o.ESTADO AS ESTADO_ORDEN,
            ISNULL(t.TIPO_NOMBRE, '') AS TIPO_NOMBRE
        FROM M_GARANTIAS g
        JOIN ORDEN_SERVICIO o ON o.NO_ORDEN = g.NO_ORDEN
        LEFT JOIN ORDEN_SERVICIO_TIPOS t ON t.TIPO_ID = o.TIPO_ID
        WHERE {' AND '.join(where)}
        ORDER BY g.CREADO_EN DESC
    """, params if params else None)
    return [_row_gar(r) for r in filas]


def get_ordenes_sin_garantia() -> list:
    """Órdenes de tipo Taller-Garantía (TIPO_ID=2) que aún no tienen registro en M_GARANTIAS."""
    filas = ejecutar_query("""
        SELECT
            o.NO_ORDEN, o.NOMBRE_CLIENTE, o.MAQUINA, o.MARCA, o.MODELO,
            o.SERIE, o.NO_TRAE, o.FECHA_REGISTRO, o.ESTADO,
            ISNULL(t.TIPO_NOMBRE,'') AS TIPO_NOMBRE
        FROM ORDEN_SERVICIO o
        LEFT JOIN ORDEN_SERVICIO_TIPOS t ON t.TIPO_ID = o.TIPO_ID
        WHERE o.TIPO_ID = 2
          AND o.NO_ORDEN NOT IN (SELECT NO_ORDEN FROM M_GARANTIAS)
        ORDER BY o.NO_ORDEN DESC
    """)
    return [_row_orden(r) for r in filas]


def crear_garantia(no_orden: int, notas: str = "", usuario: str = "") -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO M_GARANTIAS (NO_ORDEN, ESTADO, NOTAS, USUARIO) "
            "OUTPUT INSERTED.ID VALUES (?, 'Nuevo', ?, ?)",
            (no_orden, notas or None, usuario)
        )
        new_id = int(cur.fetchone()[0])
        conn.commit()
        # Nota automática en bitácora
        cur.execute(
            "INSERT INTO M_GARANTIAS_BITACORA (GARANTIA_ID, DETALLE, USUARIO) VALUES (?, ?, ?)",
            (new_id, f"Garantía registrada para orden #{no_orden}", usuario)
        )
        conn.commit()
        return {"id": new_id, "ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def actualizar_paso(garantia_id: int, paso: str, datos: dict, usuario: str = "") -> dict:
    """
    paso: 'factura_compra' | 'factura_venta' | 'guia' | 'resolucion' | 'notas'
    datos: dict con los campos del paso
    Actualiza el estado automáticamente según los pasos completados.
    """
    conn = get_connection()
    cur  = conn.cursor()
    try:
        sets   = []
        params = []

        if paso == 'factura_compra':
            sets  += ["NO_FACT_COMPRA=?", "FECHA_FACT_COMPRA=?"]
            params += [datos.get('no_fact_compra') or None,
                       datos.get('fecha_fact_compra') or None]
        elif paso == 'factura_venta':
            sets  += ["NO_FACT_VENTA=?", "FECHA_FACT_VENTA=?"]
            params += [datos.get('no_fact_venta') or None,
                       datos.get('fecha_fact_venta') or None]
        elif paso == 'guia':
            sets  += ["NO_GUIA=?", "TRANSPORTISTA=?", "FECHA_ENVIO=?"]
            params += [datos.get('no_guia') or None,
                       datos.get('transportista') or None,
                       datos.get('fecha_envio') or None]
        elif paso == 'resolucion':
            sets  += ["RESOLUCION=?", "FECHA_RESOLUCION=?"]
            params += [datos.get('resolucion') or None,
                       datos.get('fecha_resolucion') or None]
        elif paso == 'notas':
            sets  += ["NOTAS=?"]
            params += [datos.get('notas') or None]

        sets  += ["ACTUALIZADO_EN=GETDATE()"]
        params += [garantia_id]

        cur.execute(
            f"UPDATE M_GARANTIAS SET {','.join(sets)} WHERE ID=?",
            params
        )
        conn.commit()

        # Recalcular estado
        cur.execute(
            "SELECT NO_GUIA, FECHA_ENVIO, RESOLUCION, NO_FACT_COMPRA, NO_FACT_VENTA "
            "FROM M_GARANTIAS WHERE ID=?", (garantia_id,)
        )
        row = cur.fetchone()
        if row:
            nuevo_estado = _calcular_estado(row[0], row[1], row[2], row[3], row[4])
            cur.execute("UPDATE M_GARANTIAS SET ESTADO=? WHERE ID=?",
                        (nuevo_estado, garantia_id))
            conn.commit()

        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def actualizar_archivo(garantia_id: int, campo: str, path: str) -> dict:
    """campo: 'ARCHIVO_FACT_COMPRA' | 'ARCHIVO_FACT_VENTA' | 'ARCHIVO_GUIA'"""
    campos_validos = {'ARCHIVO_FACT_COMPRA', 'ARCHIVO_FACT_VENTA', 'ARCHIVO_GUIA'}
    if campo not in campos_validos:
        return {"ok": False, "error": "campo inválido"}
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(f"UPDATE M_GARANTIAS SET {campo}=?, ACTUALIZADO_EN=GETDATE() WHERE ID=?",
                    (path, garantia_id))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def eliminar_archivo(garantia_id: int, campo: str) -> dict:
    """Elimina el archivo físico y limpia el campo en BD."""
    campos_validos = {'ARCHIVO_FACT_COMPRA', 'ARCHIVO_FACT_VENTA', 'ARCHIVO_GUIA'}
    if campo not in campos_validos:
        return {"ok": False, "error": "campo inválido"}
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(f"SELECT {campo} FROM M_GARANTIAS WHERE ID=?", (garantia_id,))
        row = cur.fetchone()
        if row and row[0]:
            rel  = row[0].lstrip("/")
            base = os.path.join(os.path.dirname(__file__), '..', rel)
            try:
                os.remove(os.path.normpath(base))
            except FileNotFoundError:
                pass
        cur.execute(f"UPDATE M_GARANTIAS SET {campo}=NULL, ACTUALIZADO_EN=GETDATE() WHERE ID=?",
                    (garantia_id,))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


# ── BITÁCORA ─────────────────────────────────────────────────────────────────

def get_bitacora(garantia_id: int) -> list:
    filas = ejecutar_query(
        "SELECT ID, GARANTIA_ID, FECHA, DETALLE, USUARIO "
        "FROM M_GARANTIAS_BITACORA WHERE GARANTIA_ID=? ORDER BY FECHA DESC",
        (garantia_id,)
    )
    return [_row_bit(r) for r in filas]


def agregar_nota(garantia_id: int, detalle: str, usuario: str = "") -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO M_GARANTIAS_BITACORA (GARANTIA_ID, DETALLE, USUARIO) "
            "OUTPUT INSERTED.ID VALUES (?, ?, ?)",
            (garantia_id, detalle, usuario)
        )
        new_id = int(cur.fetchone()[0])
        conn.commit()
        return {"id": new_id, "ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def eliminar_nota(nota_id: int) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM M_GARANTIAS_BITACORA WHERE ID=?", (nota_id,))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


# ── Helpers internos ─────────────────────────────────────────────────────────

def _calcular_estado(no_guia, fecha_envio, resolucion, no_fact_compra, no_fact_venta) -> str:
    if resolucion:
        return 'Resuelto'
    if no_guia or fecha_envio:
        return 'Enviado'
    if no_fact_compra or no_fact_venta:
        return 'Proceso'
    return 'Nuevo'


def _row_gar(r: dict) -> dict:
    return {
        "id":                   r["ID"],
        "no_orden":             r["NO_ORDEN"],
        "estado":               r["ESTADO"] or "Nuevo",
        "no_fact_compra":       r["NO_FACT_COMPRA"] or "",
        "fecha_fact_compra":    str(r["FECHA_FACT_COMPRA"])[:10] if r["FECHA_FACT_COMPRA"] else "",
        "archivo_fact_compra":  r["ARCHIVO_FACT_COMPRA"] or "",
        "no_fact_venta":        r["NO_FACT_VENTA"] or "",
        "fecha_fact_venta":     str(r["FECHA_FACT_VENTA"])[:10] if r["FECHA_FACT_VENTA"] else "",
        "archivo_fact_venta":   r["ARCHIVO_FACT_VENTA"] or "",
        "no_guia":              r["NO_GUIA"] or "",
        "transportista":        r["TRANSPORTISTA"] or "",
        "fecha_envio":          str(r["FECHA_ENVIO"])[:10] if r["FECHA_ENVIO"] else "",
        "archivo_guia":         r["ARCHIVO_GUIA"] or "",
        "resolucion":           r["RESOLUCION"] or "",
        "fecha_resolucion":     str(r["FECHA_RESOLUCION"])[:10] if r["FECHA_RESOLUCION"] else "",
        "notas":                r["NOTAS"] or "",
        "usuario":              r["USUARIO"] or "",
        "creado_en":            str(r["CREADO_EN"])[:16] if r["CREADO_EN"] else "",
        "actualizado_en":       str(r["ACTUALIZADO_EN"])[:16] if r["ACTUALIZADO_EN"] else "",
        "nombre_cliente":       r["NOMBRE_CLIENTE"] or "",
        "maquina":              r["MAQUINA"] or "",
        "marca":                r["MARCA"] or "",
        "modelo":               r["MODELO"] or "",
        "serie":                r["SERIE"] or "",
        "no_trae":              r["NO_TRAE"] or "",
        "fecha_registro":       str(r["FECHA_REGISTRO"])[:10] if r["FECHA_REGISTRO"] else "",
        "estado_orden":         r["ESTADO_ORDEN"],
        "tipo_nombre":          r["TIPO_NOMBRE"] or "",
    }


def _row_orden(r: dict) -> dict:
    return {
        "no_orden":         r["NO_ORDEN"],
        "nombre_cliente":   r["NOMBRE_CLIENTE"] or "",
        "maquina":          r["MAQUINA"] or "",
        "marca":            r["MARCA"] or "",
        "modelo":           r["MODELO"] or "",
        "serie":            r["SERIE"] or "",
        "no_trae":          r["NO_TRAE"] or "",
        "fecha_registro":   str(r["FECHA_REGISTRO"])[:10] if r["FECHA_REGISTRO"] else "",
        "estado_orden":     r["ESTADO"],
        "tipo_nombre":      r["TIPO_NOMBRE"] or "",
    }


def _row_bit(r: dict) -> dict:
    return {
        "id":           r["ID"],
        "garantia_id":  r["GARANTIA_ID"],
        "fecha":        str(r["FECHA"])[:16] if r["FECHA"] else "",
        "detalle":      r["DETALLE"] or "",
        "usuario":      r["USUARIO"] or "",
    }
