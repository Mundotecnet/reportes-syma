import sqlite3
import os
from datetime import date

DB_PATH    = os.path.join(os.path.dirname(__file__), '..', 'banco.db')
FOTO_DIR   = os.path.join(os.path.dirname(__file__), '..', 'static', 'caja_chica')


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Crea la tabla si no existe."""
    os.makedirs(FOTO_DIR, exist_ok=True)
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS caja_chica (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha      TEXT    NOT NULL,
                detalle    TEXT    NOT NULL,
                monto      REAL    NOT NULL,
                foto_path  TEXT,
                usuario    TEXT,
                creado_en  TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)
        c.commit()


def get_caja_chica(fecha: str) -> list:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT * FROM caja_chica WHERE fecha = ? ORDER BY creado_en",
            (fecha,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_caja_chica_rango(fecha_ini: str, fecha_fin: str) -> list:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT * FROM caja_chica WHERE fecha BETWEEN ? AND ? ORDER BY fecha, creado_en",
            (fecha_ini, fecha_fin)
        ).fetchall()
    return [dict(r) for r in rows]


def crear_movimiento(fecha: str, detalle: str, monto: float,
                     usuario: str = "", foto_path: str = None) -> dict:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO caja_chica (fecha, detalle, monto, usuario, foto_path) VALUES (?,?,?,?,?)",
            (fecha, detalle, monto, usuario, foto_path)
        )
        c.commit()
        row_id = cur.lastrowid
    return {"id": row_id, "fecha": fecha, "detalle": detalle,
            "monto": monto, "foto_path": foto_path}


def actualizar_foto(mov_id: int, foto_path: str):
    with _conn() as c:
        c.execute("UPDATE caja_chica SET foto_path=? WHERE id=?", (foto_path, mov_id))
        c.commit()


def eliminar_movimiento(mov_id: int):
    with _conn() as c:
        row = c.execute("SELECT foto_path FROM caja_chica WHERE id=?", (mov_id,)).fetchone()
        if row and row[0]:
            try:
                os.remove(row[0])
            except FileNotFoundError:
                pass
        c.execute("DELETE FROM caja_chica WHERE id=?", (mov_id,))
        c.commit()


def get_total_dia(fecha: str) -> float:
    with _conn() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(monto),0) FROM caja_chica WHERE fecha=?", (fecha,)
        ).fetchone()
    return float(row[0])
