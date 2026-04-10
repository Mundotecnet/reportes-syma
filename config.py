import os

# ============================================================
# CONFIGURACIÓN — MUNDOTEC REPORTES
# ============================================================

DB_CONFIG = {
    "server":   os.getenv("DB_SERVER",   r"192.168.10.15\SQLEXPRESS"),
    "database": os.getenv("DB_DATABASE", "Syma"),
    "user":     os.getenv("DB_USER",     "sa"),
    "password": os.getenv("DB_PASSWORD", "sqladmin"),
}

APP_PORT       = int(os.getenv("APP_PORT", 8000))
APP_HOST       = os.getenv("APP_HOST", "0.0.0.0")
EMPRESA_NOMBRE = os.getenv("EMPRESA_NOMBRE", "MUNDOTEC, S.A.")
SECRET_KEY     = os.getenv("SECRET_KEY", "cambiar_en_produccion_mundotec2026!")

# ── SMTP (para envío de informes de garantía) ────────────────
SMTP_HOST     = os.getenv("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER",     "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM",     "")

# Autenticación: usa la tabla USUARIOS de Syma
# Campos: LOGIN (varchar 10), PASWORD (varchar 10), ESTADO = 'A'
