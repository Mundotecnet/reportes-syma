import pyodbc
from config import DB_CONFIG

def get_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['user']};"
        f"PWD={DB_CONFIG['password']};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def ejecutar_query(sql: str, params: tuple = ()):
    """Ejecuta un query y devuelve lista de dicts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        columnas = [col[0] for col in cursor.description]
        filas = cursor.fetchall()
        return [dict(zip(columnas, fila)) for fila in filas]

def probar_conexion():
    """Verifica que la conexión funcione."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            return {"ok": True, "version": version}
    except Exception as e:
        return {"ok": False, "error": str(e)}
