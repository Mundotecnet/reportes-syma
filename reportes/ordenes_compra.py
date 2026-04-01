from datetime import datetime
from db import get_connection


def _rows_to_dicts(cursor) -> list:
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ── Correlativo ───────────────────────────────────────────────────────────────
def get_siguiente_no_oc() -> str:
    year = datetime.now().year
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM M_ORDEN_COMPRA WHERE no_oc LIKE ?",
        (f"OC-{year}-%",)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return f"OC-{year}-{str(count + 1).zfill(3)}"


# ── CRUD ──────────────────────────────────────────────────────────────────────
def crear_oc(data: dict, usuario: str) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        no_oc = get_siguiente_no_oc()
        cur.execute(
            """INSERT INTO M_ORDEN_COMPRA
               (no_oc, fecha, estado, observaciones, creado_por)
               OUTPUT INSERTED.id
               VALUES (?, ?, 'Borrador', ?, ?)""",
            (no_oc, data['fecha'],
             data.get('observaciones') or '',
             usuario)
        )
        oc_id = int(cur.fetchone()[0])
        for i, ln in enumerate(data.get('lineas', []), start=1):
            det = (ln.get('detalle') or '').strip()
            if det:
                cur.execute(
                    """INSERT INTO M_ORDEN_COMPRA_DETALLE
                       (oc_id, linea, detalle, cantidad) VALUES (?, ?, ?, ?)""",
                    (oc_id, i, det, ln.get('cantidad') or None)
                )
        conn.commit()
        return {"ok": True, "no_oc": no_oc, "id": oc_id}
    except Exception as e:
        conn.rollback()
        print(f"[CrearOC] {e}")
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def get_historial_oc(fecha_ini: str, fecha_fin: str, estado: str = '') -> list:
    conn   = get_connection()
    cur    = conn.cursor()
    params = [fecha_ini, fecha_fin]
    where  = "WHERE CAST(fecha AS date) BETWEEN ? AND ?"
    if estado:
        where += " AND estado = ?"
        params.append(estado)
    cur.execute(
        f"""SELECT id, no_oc, CAST(fecha AS date) AS fecha,
                   estado, observaciones, creado_por
            FROM M_ORDEN_COMPRA {where}
            ORDER BY id DESC""",
        params
    )
    rows = _rows_to_dicts(cur)
    # Convertir fecha a string
    for r in rows:
        if r.get('fecha'):
            r['fecha'] = str(r['fecha'])
    cur.close()
    conn.close()
    return rows


def get_oc(oc_id: int) -> dict | None:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        """SELECT id, no_oc, CAST(fecha AS date) AS fecha,
                  estado, observaciones, creado_por, fecha_creacion
           FROM M_ORDEN_COMPRA WHERE id = ?""",
        (oc_id,)
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None
    cols = [c[0].lower() for c in cur.description]
    oc   = dict(zip(cols, row))
    if oc.get('fecha'):
        oc['fecha'] = str(oc['fecha'])
    if oc.get('fecha_creacion'):
        oc['fecha_creacion'] = str(oc['fecha_creacion'])

    cur.execute(
        """SELECT linea, detalle, cantidad
           FROM M_ORDEN_COMPRA_DETALLE WHERE oc_id = ? ORDER BY linea""",
        (oc_id,)
    )
    oc['lineas'] = _rows_to_dicts(cur)
    cur.close()
    conn.close()
    return oc


def actualizar_estado_oc(oc_id: int, estado: str) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE M_ORDEN_COMPRA SET estado = ? WHERE id = ?",
            (estado, oc_id)
        )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def eliminar_oc(oc_id: int) -> dict:
    """Solo permite eliminar OC en estado Borrador."""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT estado FROM M_ORDEN_COMPRA WHERE id = ?", (oc_id,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "Orden no encontrada"}
        if row[0] != 'Borrador':
            return {"ok": False, "error": "Solo se pueden eliminar borradores"}
        cur.execute("DELETE FROM M_ORDEN_COMPRA_DETALLE WHERE oc_id = ?", (oc_id,))
        cur.execute("DELETE FROM M_ORDEN_COMPRA WHERE id = ?", (oc_id,))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()
