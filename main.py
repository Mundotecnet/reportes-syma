from fastapi import FastAPI, Query, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import io, sys, os

sys.path.insert(0, os.path.dirname(__file__))

from db import probar_conexion, ejecutar_query
from reportes.ventas    import get_ventas, get_ventas_totales, get_categorias_cliente, get_vendedores, get_lineas_venta, get_ventas_grafico
from reportes.pagos     import get_pagos_clientes
from reportes.compras   import get_compras, get_proveedores, get_lineas_compra
from reportes.productos import get_productos
from reportes.cxc       import get_cxc, get_lineas_factura
from reportes.cxp       import get_cxp, get_documentos_proveedor, get_calendario_pagos, get_lineas_compra as get_lineas_compra_cxp
from reportes.inventario        import get_inventario, get_categorias_producto, get_seriales_producto
from reportes.inventario_ajustes import get_inventario_ajustes, aplicar_ajuste_fisico, get_historial_ajustes, get_detalle_ajuste
from reportes.compras_ventas     import get_compras_ventas_grafico
from reportes.dashboard          import get_dashboard_periodo, get_dashboard_saldos
from reportes.facturas_proceso   import get_facturas_proceso
from reportes.taller             import get_taller, get_detalle_taller, get_siguiente_no_orden, buscar_clientes, get_agenda_dia, get_agenda_mes, get_ordenes_antiguas, get_servicios_st003, crear_orden, get_orden_completa, mover_orden, reordenar_dia
from reportes.ordenes_compra     import get_siguiente_no_oc, crear_oc, get_historial_oc, get_oc, actualizar_estado_oc, eliminar_oc
from reportes.permisos           import get_modulos_usuario, get_roles, get_modulos_rol, get_usuarios_con_rol, asignar_rol_usuario, actualizar_modulos_rol, crear_rol, MODULOS_TODOS
from exports.pdf_oc              import exportar_oc_pdf
from exports.excel      import exportar_ventas, exportar_pagos, exportar_compras, exportar_productos, exportar_cxc
from exports.pdf        import exportar_ventas_pdf, exportar_pagos_pdf, exportar_compras_pdf, exportar_productos_pdf, exportar_cxc_pdf, exportar_boleta_pdf
from config             import APP_HOST, APP_PORT, SECRET_KEY

app = FastAPI(title="Reportes MUNDOTEC", version="1.0")

# ── Middlewares — ORDEN IMPORTANTE ──────────────────────────
# Starlette ejecuta el ÚLTIMO agregado PRIMERO.
# 1ro debe correr SessionMiddleware (descifra la cookie),
# 2do AuthMiddleware (lee request.session que ya existe).

RUTAS_PUBLICAS = {"/login", "/favicon.ico"}

class AuthMiddleware:
    """
    Middleware ASGI puro — no consume el body del request.
    BaseHTTPMiddleware tiene un bug conocido que impide leer
    campos de formulario (Form(...)) en los endpoints.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path    = request.url.path

        if path in RUTAS_PUBLICAS or path.startswith("/static"):
            await self.app(scope, receive, send)
            return

        if not request.session.get("usuario"):
            response = RedirectResponse(url="/login", status_code=302)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

# SessionMiddleware primero (exterior) → AuthMiddleware interior
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware,
                   secret_key=SECRET_KEY,
                   session_cookie="mundotec_session",
                   max_age=28800,
                   https_only=False,
                   same_site="lax")

# ── Templates (para login.html) ──────────────────────────────
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Helpers de auth ──────────────────────────────────────────
def _encode_syma(pwd: str) -> str:
    """
    Reproduce el cifrado de PowerBuilder/Syma:
      encoded[i] = chr( ord(char[i]) + 126 - i )
    Verificado con: admin→ßáéäè  |  123→¯¯¯
    """
    return "".join(chr(ord(c) + 126 - i) for i, c in enumerate(pwd[:10]))

def verificar_credenciales(usuario: str, clave: str) -> bool:
    """
    1. Obtiene la contraseña cifrada almacenada en USUARIOS.
    2. Cifra la clave recibida con el mismo algoritmo.
    3. Compara en Python (evita problemas de collation SQL).
    """
    try:
        filas = ejecutar_query(
            "SELECT TOP 1 RTRIM(PASWORD) AS PASWORD FROM USUARIOS "
            "WHERE RTRIM(LOGIN) = ? AND ESTADO = 'A'",
            (usuario.strip()[:10],)
        )
        if not filas:
            return False
        stored  = filas[0]["PASWORD"]
        encoded = _encode_syma(clave)
        return stored == encoded
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
        return False

# ─────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    # Si ya tiene sesión, ir al dashboard
    if request.session.get("usuario"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "usuario_previo": ""})

class LoginData(BaseModel):
    usuario: str
    clave:   str

@app.post("/login")
async def login_post(request: Request, data: LoginData):
    if verificar_credenciales(data.usuario, data.clave):
        request.session["usuario"] = data.usuario.strip()
        return {"ok": True}
    return {"ok": False, "error": "Usuario o contraseña incorrectos."}

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────
@app.get("/api/dashboard")
async def dashboard(fecha_ini: str = Query(...), fecha_fin: str = Query(...),
                    excluir_itservice: bool = Query(False)):
    periodo = get_dashboard_periodo(fecha_ini, fecha_fin)
    saldos  = get_dashboard_saldos(excluir_itservice=excluir_itservice)
    return {**periodo, **saldos}

@app.get("/api/facturas-proceso")
async def facturas_proceso(fecha_ini: str = Query(""), fecha_fin: str = Query(""),
                           busqueda: str = Query("")):
    return get_facturas_proceso(fecha_ini=fecha_ini, fecha_fin=fecha_fin, busqueda=busqueda)

# ─────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

# ─────────────────────────────────────────
# HEALTH / SESIÓN
# ─────────────────────────────────────────
@app.get("/api/ping")
async def ping():
    return probar_conexion()

@app.get("/api/me")
async def me(request: Request):
    usuario = request.session.get("usuario", "")
    modulos = get_modulos_usuario(usuario)
    return {"usuario": usuario, "modulos": modulos}

# ── Permisos / Admin ─────────────────────────────────────────
@app.get("/api/admin/roles")
async def admin_roles():
    return {"roles": get_roles()}

@app.get("/api/admin/roles/{rol_id}/modulos")
async def admin_modulos_rol(rol_id: int):
    return {"modulos": get_modulos_rol(rol_id), "todos": MODULOS_TODOS}

@app.post("/api/admin/roles/{rol_id}/modulos")
async def admin_guardar_modulos_rol(rol_id: int, request: Request):
    data = await request.json()
    return actualizar_modulos_rol(rol_id, data.get("modulos", []))

@app.post("/api/admin/roles")
async def admin_crear_rol(request: Request):
    data = await request.json()
    return crear_rol(data.get("nombre",""), data.get("descripcion",""), data.get("modulos",[]))

@app.get("/api/admin/usuarios")
async def admin_usuarios():
    return {"usuarios": get_usuarios_con_rol()}

@app.post("/api/admin/usuarios/asignar-rol")
async def admin_asignar_rol(request: Request):
    data = await request.json()
    return asignar_rol_usuario(data["login"], data.get("rol_id"))

# ─────────────────────────────────────────
# CATÁLOGOS (para los filtros)
# ─────────────────────────────────────────
@app.get("/api/categorias-cliente")
async def categorias_cliente():
    return get_categorias_cliente()

@app.get("/api/vendedores")
async def vendedores():
    return get_vendedores()

@app.get("/api/proveedores")
async def proveedores():
    return get_proveedores()

# ─────────────────────────────────────────
# REPORTE VENTAS
# ─────────────────────────────────────────
@app.get("/api/ventas")
async def ventas(
    fecha_ini:   str = Query(...),
    fecha_fin:   str = Query(...),
    tipo:        str = Query("todos"),
    categoria:   str = Query(""),
    estado:      str = Query("A"),
    vendedor_id: str = Query(""),
):
    datos = get_ventas(fecha_ini, fecha_fin, tipo, categoria, estado, vendedor_id)
    tots  = get_ventas_totales(fecha_ini, fecha_fin, tipo, categoria, estado, vendedor_id)
    return {"datos": datos, "totales": tots, "count": len(datos)}

@app.get("/api/ventas/grafico")
async def ventas_grafico(
    fecha_ini:         str = Query(...),
    fecha_fin:         str = Query(...),
    agrupacion:        str = Query("dia"),
    tipo:              str = Query("todos"),
    categoria:         str = Query(""),
    estado:            str = Query("A"),
    vendedor_id:       str = Query(""),
):
    datos = get_ventas_grafico(fecha_ini, fecha_fin, agrupacion, tipo, categoria, estado, vendedor_id)
    return {"datos": datos}

@app.get("/api/ventas/lineas")
async def ventas_lineas(id_documento: int = Query(...)):
    return {"lineas": get_lineas_venta(id_documento)}

@app.get("/api/ventas/excel")
async def ventas_excel(
    fecha_ini:   str = Query(...),
    fecha_fin:   str = Query(...),
    tipo:        str = Query("todos"),
    categoria:   str = Query(""),
    estado:      str = Query("A"),
    vendedor_id: str = Query(""),
):
    datos  = get_ventas(fecha_ini, fecha_fin, tipo, categoria, estado, vendedor_id)
    titulo = f"Ventas {'Contado' if tipo=='01' else 'Crédito' if tipo=='02' else 'Contado+Crédito'} — {fecha_ini} al {fecha_fin}"
    archivo = exportar_ventas(datos, titulo)
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=ventas_{fecha_ini}_{fecha_fin}.xlsx"}
    )

@app.get("/api/ventas/pdf")
async def ventas_pdf(
    fecha_ini:   str = Query(...),
    fecha_fin:   str = Query(...),
    tipo:        str = Query("todos"),
    categoria:   str = Query(""),
    estado:      str = Query("A"),
    vendedor_id: str = Query(""),
):
    datos   = get_ventas(fecha_ini, fecha_fin, tipo, categoria, estado, vendedor_id)
    titulo  = f"Ventas {'Contado' if tipo=='01' else 'Crédito' if tipo=='02' else 'Contado+Crédito'}"
    filtros = f"Período: {fecha_ini} al {fecha_fin}"
    archivo = exportar_ventas_pdf(datos, titulo, filtros)
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ventas_{fecha_ini}_{fecha_fin}.pdf"}
    )

# ─────────────────────────────────────────
# REPORTE PAGOS
# ─────────────────────────────────────────
@app.get("/api/pagos")
async def pagos(
    fecha_ini:    str = Query(...),
    fecha_fin:    str = Query(...),
    tipo_pago:    str = Query(""),
    cliente_id:   str = Query(""),
    filtro_fecha: str = Query("pago"),
):
    datos = get_pagos_clientes(fecha_ini, fecha_fin, tipo_pago, cliente_id, filtro_fecha)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/pagos/excel")
async def pagos_excel(
    fecha_ini: str = Query(...),
    fecha_fin: str = Query(...),
    tipo_pago: str = Query(""),
):
    datos   = get_pagos_clientes(fecha_ini, fecha_fin, tipo_pago)
    titulo  = f"Pagos de Clientes — {fecha_ini} al {fecha_fin}"
    archivo = exportar_pagos(datos, titulo)
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=pagos_{fecha_ini}_{fecha_fin}.xlsx"}
    )

@app.get("/api/pagos/pdf")
async def pagos_pdf(
    fecha_ini: str = Query(...),
    fecha_fin: str = Query(...),
    tipo_pago: str = Query(""),
):
    datos   = get_pagos_clientes(fecha_ini, fecha_fin, tipo_pago)
    archivo = exportar_pagos_pdf(datos, "Pagos de Clientes", f"Período: {fecha_ini} al {fecha_fin}")
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=pagos_{fecha_ini}_{fecha_fin}.pdf"}
    )

# ─────────────────────────────────────────
# REPORTE COMPRAS
# ─────────────────────────────────────────
@app.get("/api/compras")
async def compras(
    fecha_ini:         str  = Query(...),
    fecha_fin:         str  = Query(...),
    proveedor_id:      str  = Query(""),
    estado:            str  = Query(""),
    moneda:            str  = Query(""),
    excluir_itservice: bool = Query(False),
):
    datos = get_compras(fecha_ini, fecha_fin, proveedor_id, estado, moneda, excluir_itservice)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/compras/lineas")
async def compras_lineas(documento_id: int = Query(...)):
    return {"lineas": get_lineas_compra(documento_id)}

@app.get("/api/compras/excel")
async def compras_excel(
    fecha_ini:    str = Query(...),
    fecha_fin:    str = Query(...),
    proveedor_id: str = Query(""),
    estado:       str = Query(""),
    moneda:       str = Query(""),
):
    datos   = get_compras(fecha_ini, fecha_fin, proveedor_id, estado, moneda)
    titulo  = f"Compras — {fecha_ini} al {fecha_fin}"
    archivo = exportar_compras(datos, titulo)
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=compras_{fecha_ini}_{fecha_fin}.xlsx"}
    )

@app.get("/api/compras/pdf")
async def compras_pdf(
    fecha_ini:    str = Query(...),
    fecha_fin:    str = Query(...),
    proveedor_id: str = Query(""),
    estado:       str = Query(""),
    moneda:       str = Query(""),
):
    datos   = get_compras(fecha_ini, fecha_fin, proveedor_id, estado, moneda)
    archivo = exportar_compras_pdf(datos, "Compras", f"Período: {fecha_ini} al {fecha_fin}")
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=compras_{fecha_ini}_{fecha_fin}.pdf"}
    )

# ─────────────────────────────────────────
# REPORTE PRODUCTOS VENDIDOS
# ─────────────────────────────────────────
@app.get("/api/productos")
async def productos(
    fecha_ini:  str = Query(...),
    fecha_fin:  str = Query(...),
    estado:     str = Query("A"),
    busqueda:   str = Query(""),
    tipo_item:  str = Query(""),
):
    datos = get_productos(fecha_ini, fecha_fin, estado, busqueda, tipo_item)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/productos/excel")
async def productos_excel(
    fecha_ini: str = Query(...),
    fecha_fin: str = Query(...),
    estado:    str = Query("A"),
    busqueda:  str = Query(""),
    tipo_item: str = Query(""),
):
    datos  = get_productos(fecha_ini, fecha_fin, estado, busqueda, tipo_item)
    labels = {"0": "Bienes", "1": "Servicios"}
    titulo = f"Productos Vendidos — {fecha_ini} al {fecha_fin}"
    if tipo_item in labels:
        titulo += f"  |  Tipo: {labels[tipo_item]}"
    if busqueda:
        titulo += f"  |  Búsqueda: {busqueda}"
    archivo = exportar_productos(datos, titulo)
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=productos_{fecha_ini}_{fecha_fin}.xlsx"}
    )

@app.get("/api/productos/pdf")
async def productos_pdf(
    fecha_ini: str = Query(...),
    fecha_fin: str = Query(...),
    estado:    str = Query("A"),
    busqueda:  str = Query(""),
    tipo_item: str = Query(""),
):
    datos   = get_productos(fecha_ini, fecha_fin, estado, busqueda, tipo_item)
    labels  = {"0": "Bienes", "1": "Servicios"}
    titulo  = "Productos Vendidos"
    filtros = f"Período: {fecha_ini} al {fecha_fin}"
    if tipo_item in labels:
        filtros += f"  |  Tipo: {labels[tipo_item]}"
    if busqueda:
        filtros += f"  |  Búsqueda: {busqueda}"
    archivo  = exportar_productos_pdf(datos, titulo, filtros)
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=productos_{fecha_ini}_{fecha_fin}.pdf"}
    )

# ─────────────────────────────────────────
# REPORTE CUENTAS X COBRAR
# ─────────────────────────────────────────
@app.get("/api/cxp")
async def cxp(busqueda: str = Query(""), excluir_itservice: bool = Query(False)):
    datos = get_cxp(busqueda, excluir_itservice)
    total_saldo = sum(r["saldo"] for r in datos)
    return {"datos": datos, "count": len(datos), "total_saldo": total_saldo}

@app.get("/api/cxp/documentos")
async def cxp_documentos(proveedor_id: int = Query(...)):
    docs = get_documentos_proveedor(proveedor_id)
    return {"documentos": docs}

@app.get("/api/cxp/calendario")
async def cxp_calendario(fecha_ini: str = Query(...), fecha_fin: str = Query(...)):
    docs = get_calendario_pagos(fecha_ini, fecha_fin)
    return {"documentos": docs}

@app.get("/api/cxp/lineas")
async def cxp_lineas(documento_id: int = Query(...)):
    return {"lineas": get_lineas_compra(documento_id)}

@app.get("/api/cxc")
async def cxc(categoria: str = Query(""), busqueda: str = Query("")):
    datos = get_cxc(categoria, busqueda)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/cxc/lineas")
async def cxc_lineas(pv_id: int = Query(...)):
    lineas = get_lineas_factura(pv_id)
    return {"lineas": lineas}

@app.get("/api/cxc/excel")
async def cxc_excel(categoria: str = Query(""), busqueda: str = Query("")):
    datos   = get_cxc(categoria, busqueda)
    titulo  = "Cuentas por Cobrar"
    archivo = exportar_cxc(datos, titulo)
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=cxc.xlsx"}
    )

@app.get("/api/cxc/pdf")
async def cxc_pdf(categoria: str = Query(""), busqueda: str = Query("")):
    datos   = get_cxc(categoria, busqueda)
    archivo = exportar_cxc_pdf(datos, "Cuentas por Cobrar")
    return StreamingResponse(
        io.BytesIO(archivo),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cxc.pdf"}
    )

# ─────────────────────────────────────────
# REPORTE INVENTARIO
# ─────────────────────────────────────────
@app.get("/api/inventario")
async def inventario(
    categoria:    str = Query(""),
    estado_stock: str = Query("todos"),
    busqueda:     str = Query(""),
    ind_series:   str = Query(""),
):
    datos = get_inventario(categoria, estado_stock, busqueda, ind_series)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/inventario/seriales")
async def inventario_seriales(id_producto: str = Query(...)):
    return {"seriales": get_seriales_producto(id_producto)}

# ─────────────────────────────────────────
# REPORTE INVENTARIO AJUSTES (duplicado de Inventario)
# ─────────────────────────────────────────
@app.get("/api/inventario-ajustes")
async def inventario_ajustes(
    fecha_ini:    str = Query(...),
    fecha_fin:    str = Query(...),
    categoria:    str = Query(""),
    estado_stock: str = Query("todos"),
    busqueda:     str = Query(""),
    ind_series:   str = Query(""),
):
    datos = get_inventario_ajustes(fecha_ini, fecha_fin, categoria, estado_stock, busqueda, ind_series)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/inventario-ajustes/seriales")
async def inventario_ajustes_seriales(id_producto: str = Query(...)):
    return {"seriales": get_seriales_producto(id_producto)}

class AjusteItem(BaseModel):
    id_producto:  str
    codigo_id:    int
    conteo:       float
    sistema:      float
    costo_prom:   float = 0.0

class AjustePayload(BaseModel):
    items:         list[AjusteItem]
    observaciones: str = ""

@app.post("/api/inventario-ajustes/aplicar")
async def inventario_ajustes_aplicar(request: Request, payload: AjustePayload):
    session  = request.session
    usuario  = session.get("usuario", "sistema")
    items    = [i.model_dump() for i in payload.items]
    obs      = payload.observaciones or f"Ajuste físico — usuario: {usuario}"
    resultado = aplicar_ajuste_fisico(items, usuario, obs)
    return resultado

@app.get("/api/inventario-ajustes/historial")
async def inventario_ajustes_historial(
    fecha_ini: str = Query(...),
    fecha_fin: str = Query(...),
    usuario:   str = Query(""),
):
    datos = get_historial_ajustes(fecha_ini, fecha_fin, usuario)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/inventario-ajustes/historial/lineas")
async def inventario_ajustes_historial_lineas(
    id_documento: int = Query(...),
    id_tipodoc:   str = Query(...),
    id_concepto:  str = Query(...),
):
    lineas = get_detalle_ajuste(id_documento, id_tipodoc, id_concepto)
    return {"lineas": lineas}

@app.get("/api/compras-ventas/grafico")
async def compras_ventas_grafico(
    fecha_ini:  str = Query(...),
    fecha_fin:  str = Query(...),
    agrupacion: str = Query("mes"),
):
    datos = get_compras_ventas_grafico(fecha_ini, fecha_fin, agrupacion)
    return {"datos": datos}

# ─────────────────────────────────────────
# REPORTE TALLER
# ─────────────────────────────────────────
@app.get("/api/taller")
async def taller(
    fecha_ini:    str = Query(...),
    fecha_fin:    str = Query(...),
    tipo_id:      str = Query(""),
    estado:       str = Query(""),
    busqueda:     str = Query(""),
    filtro_fecha: str = Query("ingreso"),
):
    datos = get_taller(fecha_ini, fecha_fin, tipo_id, estado, busqueda, filtro_fecha)
    return {"datos": datos, "count": len(datos)}

@app.get("/api/taller/lineas")
async def taller_lineas(no_orden: int = Query(...)):
    return {"lineas": get_detalle_taller(no_orden)}

@app.get("/api/taller/siguiente-orden")
async def taller_siguiente_orden():
    return {"no_orden": get_siguiente_no_orden()}

@app.get("/api/taller/clientes")
async def taller_clientes(busqueda: str = Query("")):
    return {"clientes": buscar_clientes(busqueda)}

@app.get("/api/taller/agenda")
async def taller_agenda(fecha: str = Query(...)):
    return {"ordenes": get_agenda_dia(fecha)}

@app.get("/api/taller/agenda-mes")
async def taller_agenda_mes(year: int = Query(...), month: int = Query(...)):
    return {"dias": get_agenda_mes(year, month)}

@app.get("/api/taller/ordenes-antiguas")
async def taller_ordenes_antiguas(year: int = Query(...), month: int = Query(...)):
    return {"ordenes": get_ordenes_antiguas(year, month)}

@app.get("/api/taller/st003")
async def taller_st003(fecha_ini: str = Query(...), fecha_fin: str = Query(...)):
    datos = get_servicios_st003(fecha_ini, fecha_fin)
    return {"datos": datos, "count": len(datos)}


@app.post("/api/taller/crear")
async def taller_crear(request: Request):
    data    = await request.json()
    usuario = request.session.get("usuario", "sistema")
    return crear_orden(data, usuario)

@app.patch("/api/taller/reordenar-dia")
async def taller_reordenar_dia(request: Request):
    data = await request.json()
    return reordenar_dia(data["ordenes"])

@app.patch("/api/taller/mover-orden")
async def taller_mover_orden(request: Request):
    data = await request.json()
    return mover_orden(int(data["no_orden"]), data["nueva_fecha"])

@app.get("/api/taller/orden")
async def taller_orden(no_orden: int = Query(...)):
    orden  = get_orden_completa(no_orden)
    lineas = get_detalle_taller(no_orden) if orden else []
    return {"orden": orden, "lineas": lineas}

@app.get("/api/taller/boleta-pdf")
async def taller_boleta_pdf(no_orden: int = Query(...), descargar: int = Query(0)):
    from fastapi.responses import Response as FResponse
    orden = get_orden_completa(no_orden)
    if not orden:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Orden no encontrada"}, status_code=404)
    pdf_bytes = exportar_boleta_pdf(orden)
    disposition = "attachment" if descargar else "inline"
    return FResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename=boleta_{no_orden}.pdf'},
    )

@app.get("/api/categorias-producto")
async def categorias_producto():
    return {"datos": get_categorias_producto()}

# ─────────────────────────────────────────
# ÓRDENES DE COMPRA (Syma M_ tables)
# ─────────────────────────────────────────

@app.get("/api/oc/siguiente-no")
async def oc_siguiente_no():
    return {"no_oc": get_siguiente_no_oc()}

@app.get("/api/oc/historial")
async def oc_historial(fecha_ini: str = Query(...), fecha_fin: str = Query(...),
                       estado: str = Query("")):
    return {"datos": get_historial_oc(fecha_ini, fecha_fin, estado)}

@app.get("/api/oc/{oc_id}")
async def oc_detalle(oc_id: int):
    oc = get_oc(oc_id)
    if not oc:
        raise HTTPException(status_code=404, detail="OC no encontrada")
    return oc

@app.post("/api/oc/crear")
async def oc_crear(request: Request):
    data    = await request.json()
    usuario = request.session.get("usuario", "sistema")
    return crear_oc(data, usuario)

@app.patch("/api/oc/{oc_id}/estado")
async def oc_estado(oc_id: int, request: Request):
    data = await request.json()
    return actualizar_estado_oc(oc_id, data["estado"])

@app.delete("/api/oc/{oc_id}")
async def oc_eliminar(oc_id: int):
    return eliminar_oc(oc_id)

@app.get("/api/oc/{oc_id}/pdf")
async def oc_pdf(oc_id: int, descargar: int = Query(0)):
    from fastapi.responses import Response as FResponse
    oc = get_oc(oc_id)
    if not oc:
        raise HTTPException(status_code=404, detail="OC no encontrada")
    pdf_bytes   = exportar_oc_pdf(oc)
    disposition = "attachment" if descargar else "inline"
    return FResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename={oc["no_oc"]}.pdf'},
    )

# ─────────────────────────────────────────
# ARRANQUE
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=APP_HOST, port=APP_PORT, reload=True)
