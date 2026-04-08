import os
from db import ejecutar_query, get_connection

FOTO_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'caja_chica')


def init_db():
    """Asegura que el directorio de fotos exista (tabla en SQL Server ya creada)."""
    os.makedirs(FOTO_DIR, exist_ok=True)


def get_caja_chica(fecha: str) -> list:
    filas = ejecutar_query(
        "SELECT ID, FECHA, DETALLE, MONTO, FOTO_PATH, USUARIO, CREADO_EN "
        "FROM M_CAJA_CHICA WHERE CAST(FECHA AS date) = ? ORDER BY CREADO_EN",
        (fecha,)
    )
    return [_row(r) for r in filas]


def get_caja_chica_rango(fecha_ini: str, fecha_fin: str) -> list:
    filas = ejecutar_query(
        "SELECT ID, FECHA, DETALLE, MONTO, FOTO_PATH, USUARIO, CREADO_EN "
        "FROM M_CAJA_CHICA WHERE CAST(FECHA AS date) BETWEEN ? AND ? "
        "ORDER BY FECHA, CREADO_EN",
        (fecha_ini, fecha_fin)
    )
    return [_row(r) for r in filas]


def crear_movimiento(fecha: str, detalle: str, monto: float,
                     usuario: str = "", foto_path: str = None) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO M_CAJA_CHICA (FECHA, DETALLE, MONTO, USUARIO, FOTO_PATH) "
            "OUTPUT INSERTED.ID VALUES (?, ?, ?, ?, ?)",
            (fecha, detalle, float(monto), usuario, foto_path)
        )
        row_id = int(cur.fetchone()[0])
        conn.commit()
        return {"id": row_id, "fecha": fecha, "detalle": detalle,
                "monto": float(monto), "foto_path": foto_path}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def actualizar_foto(mov_id: int, foto_path: str):
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("UPDATE M_CAJA_CHICA SET FOTO_PATH=? WHERE ID=?",
                    (foto_path, mov_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def eliminar_movimiento(mov_id: int):
    conn = get_connection()
    cur  = conn.cursor()
    try:
        # Obtener ruta de foto antes de borrar
        cur.execute("SELECT FOTO_PATH FROM M_CAJA_CHICA WHERE ID=?", (mov_id,))
        row = cur.fetchone()
        if row and row[0]:
            # foto_path viene como "/static/caja_chica/cc_X.jpg"
            # convertir a ruta absoluta en disco
            rel = row[0].lstrip("/")            # "static/caja_chica/cc_X.jpg"
            base = os.path.join(os.path.dirname(__file__), '..', rel)
            try:
                os.remove(os.path.normpath(base))
            except FileNotFoundError:
                pass
        cur.execute("DELETE FROM M_CAJA_CHICA WHERE ID=?", (mov_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_total_dia(fecha: str) -> float:
    filas = ejecutar_query(
        "SELECT ISNULL(SUM(MONTO), 0) AS total FROM M_CAJA_CHICA "
        "WHERE CAST(FECHA AS date) = ?",
        (fecha,)
    )
    return float(filas[0]["total"]) if filas else 0.0


# ── Helper interno ─────────────────────────────────────────────────────────────
def _row(r: dict) -> dict:
    return {
        "id":        r["ID"],
        "fecha":     str(r["FECHA"])[:10] if r["FECHA"] else "",
        "detalle":   r["DETALLE"] or "",
        "monto":     float(r["MONTO"] or 0),
        "foto_path": r["FOTO_PATH"] or None,
        "usuario":   r["USUARIO"] or "",
        "creado_en": str(r["CREADO_EN"]) if r["CREADO_EN"] else "",
    }
