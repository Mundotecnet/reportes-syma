import os
from db import ejecutar_query, get_connection

FOTO_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'depositos')


def init_depositos():
    """Asegura que exista el directorio de fotos."""
    os.makedirs(FOTO_DIR, exist_ok=True)


# ── CRUD DEPÓSITOS ─────────────────────────────────────────────────────────────

def get_depositos(fecha_ini: str, fecha_fin: str) -> list:
    filas = ejecutar_query(
        "SELECT ID, FECHA, BANCO, MONTO, NOTAS, FOTO_PATH, USUARIO, CREADO_EN "
        "FROM M_DEPOSITOS WHERE FECHA BETWEEN ? AND ? ORDER BY FECHA, CREADO_EN",
        (fecha_ini, fecha_fin)
    )
    return [_row_dep(r) for r in filas]


def crear_deposito(fecha: str, banco: str, monto: float,
                   notas: str = "", usuario: str = "",
                   foto_path: str = None) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO M_DEPOSITOS (FECHA, BANCO, MONTO, NOTAS, USUARIO, FOTO_PATH) "
            "OUTPUT INSERTED.ID VALUES (?, ?, ?, ?, ?, ?)",
            (fecha, banco, float(monto), notas or None, usuario, foto_path)
        )
        row_id = int(cur.fetchone()[0])
        conn.commit()
        return {"id": row_id, "fecha": fecha, "banco": banco,
                "monto": float(monto), "notas": notas, "foto_path": foto_path}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def actualizar_foto_deposito(dep_id: int, foto_path: str):
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("UPDATE M_DEPOSITOS SET FOTO_PATH=? WHERE ID=?",
                    (foto_path, dep_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def eliminar_deposito(dep_id: int):
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT FOTO_PATH FROM M_DEPOSITOS WHERE ID=?", (dep_id,))
        row = cur.fetchone()
        if row and row[0]:
            rel  = row[0].lstrip("/")
            base = os.path.join(os.path.dirname(__file__), '..', rel)
            try:
                os.remove(os.path.normpath(base))
            except FileNotFoundError:
                pass
        cur.execute("DELETE FROM M_DEPOSITOS WHERE ID=?", (dep_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ── RESUMEN CONTROL DE EFECTIVO ────────────────────────────────────────────────

def get_resumen_control_efectivo(fecha_ini: str, fecha_fin: str) -> dict:
    """
    Retorna el resumen diario de efectivo acumulado vs depósitos.
    Efectivo neto por día = ef_ventas + ef_cobros_cxc - caja_chica
    Saldo en caja (acumulado) = Σ(neto) - Σ(depósitos)
    """

    # 1. Efectivo ventas contado por día
    ventas = ejecutar_query("""
        SELECT
            CAST(FECHA AS date) AS fecha,
            SUM(CASE WHEN RTRIM(ID_CONCEPTO)='01'
                     THEN ISNULL(TOTAL,0)
                          - ISNULL(MONTO_TARJETAS,0)
                          - ISNULL(MONTO_CHEQUES,0)
                          - ISNULL(MONTO_TRANSFERENCIAS,0)
                     ELSE 0 END) AS ef_ventas
        FROM PUNTO_VENTA
        WHERE CAST(FECHA AS date) BETWEEN ? AND ?
          AND ESTADO = 'A'
        GROUP BY CAST(FECHA AS date)
    """, (fecha_ini, fecha_fin))

    # 2. Cobros CXC en efectivo por día
    cobros = ejecutar_query("""
        SELECT
            CAST(FECHA AS date) AS fecha,
            SUM(CASE WHEN RTRIM(ISNULL(ID_TIPOPAGO,'01'))='01'
                     THEN ISNULL(MONTO,0) ELSE 0 END) AS ef_cobros
        FROM ETransac
        WHERE CAST(FECHA AS date) BETWEEN ? AND ?
          AND ID_TIPODOC  = '01'
          AND ID_CONCEPTO = '01'
          AND STATUS      = 'A'
        GROUP BY CAST(FECHA AS date)
    """, (fecha_ini, fecha_fin))

    # 3. Caja chica por día
    gastos = ejecutar_query(
        "SELECT CAST(FECHA AS date) AS fecha, SUM(ISNULL(MONTO,0)) AS caja_chica "
        "FROM M_CAJA_CHICA WHERE CAST(FECHA AS date) BETWEEN ? AND ? "
        "GROUP BY CAST(FECHA AS date)",
        (fecha_ini, fecha_fin)
    )

    # 4. Depósitos por día (detalle y agrupado)
    deps_raw = ejecutar_query(
        "SELECT ID, FECHA, BANCO, MONTO, NOTAS, FOTO_PATH, USUARIO "
        "FROM M_DEPOSITOS WHERE FECHA BETWEEN ? AND ? ORDER BY FECHA, CREADO_EN",
        (fecha_ini, fecha_fin)
    )

    # ── Indexar por fecha ──────────────────────────────────────────────────────
    def _idx(rows, key):
        d = {}
        for r in rows:
            k = str(r[key])[:10]
            d[k] = float(r.get(list(r.keys())[1], 0) if len(r) == 2 else 0)
        return d

    v_map  = {str(r["fecha"])[:10]: float(r["ef_ventas"] or 0) for r in ventas}
    c_map  = {str(r["fecha"])[:10]: float(r["ef_cobros"] or 0) for r in cobros}
    g_map  = {str(r["fecha"])[:10]: float(r["caja_chica"] or 0) for r in gastos}
    dep_map = {}
    for r in deps_raw:
        k = str(r["FECHA"])[:10]
        dep_map[k] = dep_map.get(k, 0) + float(r["MONTO"] or 0)

    # ── Todas las fechas con actividad ─────────────────────────────────────────
    todas = sorted(set(v_map) | set(c_map) | set(g_map) | set(dep_map))

    # ── Construir resumen diario con saldo acumulado ───────────────────────────
    saldo_acum = 0.0
    dias = []
    for fecha in todas:
        ef_v  = v_map.get(fecha, 0)
        ef_c  = c_map.get(fecha, 0)
        cc    = g_map.get(fecha, 0)
        dep   = dep_map.get(fecha, 0)
        neto  = ef_v + ef_c - cc
        saldo_acum += neto - dep
        dias.append({
            "fecha":     fecha,
            "ef_ventas": ef_v,
            "ef_cobros": ef_c,
            "caja_chica": cc,
            "neto":      neto,
            "deposito":  dep,
            "saldo":     round(saldo_acum, 2),
        })

    # ── Totales del período ────────────────────────────────────────────────────
    total_ef_ventas  = sum(d["ef_ventas"]  for d in dias)
    total_ef_cobros  = sum(d["ef_cobros"]  for d in dias)
    total_caja_chica = sum(d["caja_chica"] for d in dias)
    total_neto       = sum(d["neto"]       for d in dias)
    total_depositos  = sum(d["deposito"]   for d in dias)
    saldo_final      = round(total_neto - total_depositos, 2)

    return {
        "dias":             dias,
        "depositos":        [_row_dep(r) for r in deps_raw],
        "total_ef_ventas":  total_ef_ventas,
        "total_ef_cobros":  total_ef_cobros,
        "total_caja_chica": total_caja_chica,
        "total_neto":       total_neto,
        "total_depositos":  total_depositos,
        "saldo_final":      saldo_final,
    }


# ── Helper interno ─────────────────────────────────────────────────────────────
def _row_dep(r: dict) -> dict:
    return {
        "id":        r["ID"],
        "fecha":     str(r["FECHA"])[:10] if r["FECHA"] else "",
        "banco":     r["BANCO"] or "",
        "monto":     float(r["MONTO"] or 0),
        "notas":     r["NOTAS"] or "",
        "foto_path": r["FOTO_PATH"] or None,
        "usuario":   r["USUARIO"] or "",
    }
