from db import ejecutar_query, get_connection

MODULOS_TODOS = [
    'dashboard',
    'ventas', 'pagos', 'compras', 'productos', 'cxc', 'fproceso',
    'inventario', 'inv-ajustes', 'hist-ajustes', 'cv',
    'taller', 'ingreso-taller', 'agenda-taller', 'st003', 'orden-compra',
    'cxp', 'cierre-caja', 'caja-chica', 'admin'
]

MODULOS_POR_ROL_DEFAULT = {
    'Administrador': MODULOS_TODOS,
    'Ventas':        ['ventas', 'pagos', 'productos', 'cxc', 'cv', 'fproceso'],
    'Compras':       ['compras', 'cxp'],
    'Inventario':    ['inventario', 'inv-ajustes', 'hist-ajustes'],
    'Taller':        ['taller', 'ingreso-taller', 'agenda-taller', 'st003', 'orden-compra'],
}


def get_modulos_usuario(login: str) -> list:
    try:
        filas = ejecutar_query("""
            SELECT DISTINCT rm.modulo
            FROM M_USUARIO_ROL ur
            JOIN M_ROL_MODULOS rm ON rm.rol_id = ur.rol_id
            WHERE RTRIM(ur.login) = ?
        """, (login.strip()[:10],))
        if filas:
            return [f['modulo'] for f in filas]
        # Sin rol asignado → acceso total (admin por defecto inicial)
        return MODULOS_TODOS
    except Exception as e:
        print(f"[Permisos] {e}")
        return MODULOS_TODOS


def get_roles() -> list:
    try:
        return ejecutar_query(
            "SELECT id, nombre, descripcion FROM M_ROLES ORDER BY nombre"
        )
    except Exception as e:
        print(f"[Roles] {e}")
        return []


def get_modulos_rol(rol_id: int) -> list:
    try:
        filas = ejecutar_query(
            "SELECT modulo FROM M_ROL_MODULOS WHERE rol_id = ? ORDER BY modulo",
            (rol_id,)
        )
        return [f['modulo'] for f in filas]
    except Exception as e:
        print(f"[ModulosRol] {e}")
        return []


def get_usuarios_con_rol() -> list:
    try:
        return ejecutar_query("""
            SELECT
                RTRIM(u.LOGIN)                   AS login,
                RTRIM(ISNULL(u.USUARIO, u.LOGIN)) AS nombre,
                r.id                             AS rol_id,
                ISNULL(r.nombre, '')             AS rol_nombre
            FROM USUARIOS u
            LEFT JOIN M_USUARIO_ROL  ur ON RTRIM(ur.login) = RTRIM(u.LOGIN)
            LEFT JOIN M_ROLES        r  ON r.id = ur.rol_id
            WHERE u.ESTADO = 'A'
            ORDER BY u.USUARIO
        """)
    except Exception as e:
        print(f"[UsuariosRol] {e}")
        return []


def asignar_rol_usuario(login: str, rol_id) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM M_USUARIO_ROL WHERE RTRIM(login) = ?",
            (login.strip()[:10],)
        )
        if rol_id:
            cur.execute(
                "INSERT INTO M_USUARIO_ROL (login, rol_id) VALUES (?, ?)",
                (login.strip()[:10], int(rol_id))
            )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def actualizar_modulos_rol(rol_id: int, modulos: list) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM M_ROL_MODULOS WHERE rol_id = ?", (rol_id,))
        for m in modulos:
            cur.execute(
                "INSERT INTO M_ROL_MODULOS (rol_id, modulo) VALUES (?, ?)",
                (rol_id, m)
            )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def crear_rol(nombre: str, descripcion: str, modulos: list) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO M_ROLES (nombre, descripcion) OUTPUT INSERTED.id VALUES (?, ?)",
            (nombre, descripcion)
        )
        rol_id = int(cur.fetchone()[0])
        for m in modulos:
            cur.execute(
                "INSERT INTO M_ROL_MODULOS (rol_id, modulo) VALUES (?, ?)",
                (rol_id, m)
            )
        conn.commit()
        return {"ok": True, "rol_id": rol_id}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()
