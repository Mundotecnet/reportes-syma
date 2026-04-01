# BITÁCORA TÉCNICA — Reportes MUNDOTEC
**Sistema:** FastAPI + SQL Server Syma
**Servidor:** Ubuntu 192.168.88.250:8000
**Ruta local:** `/Users/lroot/Downloads/reportes-syma`
**Ruta servidor:** `/home/lroot/reportes-syma`
**Última actualización:** 2026-04-01

---

## FRASES CLAVE DE SESIÓN

| Frase del usuario | Acción de Claude |
|-------------------|-----------------|
| `"lee la bitácora"` | `Read BITACORA_TECNICA.md` → contexto completo cargado |
| `"cierra la sesión"` | Actualizar bitácora + `git commit` + `git push servidor main` |
| `"realiza respaldo"` | `cp -r reportes-syma reportes-syma-backup-$(date +%Y%m%d-%H%M%S)` |

---

## ══ ESTADO ACTUAL DEL SISTEMA ══

### Versión activa: `v1.0.0`
### Git: rama `main` — remoto `servidor` (ssh://lroot@192.168.88.250/home/lroot/reportes-syma)

### Módulos funcionando al 100%
| Módulo | Tab ID | Descripción |
|--------|--------|-------------|
| Ventas | `ventas` | Facturas contado/crédito con filtros y exportación |
| Pago de Clientes | `pagos` | Pagos recibidos |
| Compras | `compras` | Facturas de proveedores con detalle de líneas |
| Productos Vendidos | `productos` | Artículos facturados agrupados |
| Cuentas x Cobrar | `cxc` | Saldo pendiente clientes |
| Cuentas x Pagar | `cxp` | Saldo pendiente proveedores con detalle y calendario |
| Calendario Pagos | `cal-pagos` | Pagos futuros a proveedores |
| Inventario Ajustes | `inv-ajustes` | Conteo físico y ajuste de inventario |
| Historial Ajustes | `hist-ajustes` | Historial de ajustes realizados |
| Compra-Venta | `cv` | Gráfico comparativo compras vs ventas |
| **Taller** | `taller` | Órdenes de servicio con filtros, días abierta, ST003 |
| **Servicio ST003** | `st003` | Servicios ST003 facturados directo en punto_venta |
| **Ingreso Taller** | `ingreso-taller` | Creación de nuevas órdenes de servicio |
| **Agenda Taller** | `agenda-taller` | Calendario mensual/semanal/diario + backlog drag&drop |
| Orden Compra | `orden-compra` | Gestión de órdenes de compra internas |
| Admin | `admin` | Gestión de roles y permisos por módulo |

### Orden de tabs en navegación
```
💰 Ventas:     ventas → pagos → productos → cxc → cv
🛒 Compras:    compras → cxp → cal-pagos
📦 Inventario: inv-ajustes → hist-ajustes
🔧 Taller:     taller → st003 → ingreso-taller → agenda-taller → orden-compra
⚙ Admin:       admin
```

### Pendientes / Ideas futuras
- [ ] Exportar reporte ST003 a Excel/PDF
- [ ] Agregar filtro de búsqueda por cliente en tab ST003
- [ ] Vincular órdenes de taller con facturas (requiere cambio en Syma — no hay campo `NO_FACTURA` en `ORDEN_SERVICIO`)

---

## PROTOCOLO OBLIGATORIO ANTES DE CUALQUIER CAMBIO

```
1. MODIFICAR archivos locales

2. COMMIT con mensaje descriptivo
   git add <archivos modificados>
   git commit -m "descripción del cambio"

3. DEPLOY AL SERVIDOR (push + reinicio)
   GIT_SSH_COMMAND="sshpass -p '87060002' ssh -o StrictHostKeyChecking=no" \
     git push servidor main
   sshpass -p '87060002' ssh -tt lroot@192.168.88.250 \
     "echo '87060002' | sudo -S systemctl restart reportes.service && \
      sleep 2 && systemctl is-active reportes.service"

4. VERIFICAR respuesta "active"

5. DOCUMENTAR en la sección "Bitácora de Cambios":
   - Número de cambio correlativo
   - Solicitud del usuario
   - Problema / causa raíz
   - Solución aplicada
   - Archivos modificados

6. AL CERRAR UN BLOQUE DE MEJORAS — crear tag de versión
   git tag -a v1.X.0 -m "descripción del release"
   GIT_SSH_COMMAND="sshpass -p '87060002' ssh -o StrictHostKeyChecking=no" \
     git push servidor main --tags
```

### Rollback a versión anterior
```bash
# Ver versiones disponibles
git tag

# Revertir localmente y en servidor
git checkout v1.0.0
sshpass -p '87060002' ssh lroot@192.168.88.250 \
  "cd /home/lroot/reportes-syma && git checkout v1.0.0"
sshpass -p '87060002' ssh -tt lroot@192.168.88.250 \
  "echo '87060002' | sudo -S systemctl restart reportes.service"
```

---

## ESTRUCTURA DEL PROYECTO

```
reportes-syma/
├── main.py                          # FastAPI app, todos los endpoints
├── db.py                            # Conexión SQL Server via pyodbc
├── config.py                        # APP_HOST, APP_PORT, SECRET_KEY
├── compras.py                       # (raíz) get_lineas_compra para compras
├── reportes/
│   ├── taller.py                    # Módulo taller (órdenes + ST003)
│   ├── ventas.py
│   ├── compras.py
│   ├── cxp.py
│   ├── cxc.py
│   ├── productos.py
│   ├── inventario.py
│   ├── inventario_ajustes.py
│   ├── compras_ventas.py
│   ├── pagos.py
│   ├── ordenes_compra.py
│   └── permisos.py                  # Roles y módulos — MODULOS_TODOS aquí
├── exports/
│   ├── excel.py
│   ├── pdf.py
│   └── pdf_oc.py
├── templates/
│   ├── index.html                   # SPA completa (todo el frontend)
│   └── login.html
└── static/
```

---

## ACCESO AL SERVIDOR

```bash
# Push y reinicio (flujo normal)
GIT_SSH_COMMAND="sshpass -p '87060002' ssh -o StrictHostKeyChecking=no" git push servidor main
sshpass -p '87060002' ssh -tt lroot@192.168.88.250 "echo '87060002' | sudo -S systemctl restart reportes.service && sleep 2 && systemctl is-active reportes.service"

# Ver logs
sshpass -p '87060002' ssh lroot@192.168.88.250 "sudo journalctl -u reportes.service -n 50"
```

---

## BASE DE DATOS (tablas clave)

| Tabla | Descripción |
|-------|-------------|
| `ORDEN_SERVICIO` | Cabecera de órdenes de taller |
| `ORDEN_SERVICIO_DETALLE` | Líneas de cada orden (productos/servicios aplicados) |
| `ORDEN_SERVICIO_TIPOS` | Catálogo de tipos de orden |
| `PUNTO_VENTA` | Facturas/tiquetes emitidos |
| `PUNTO_VENTA_DETALLE` | Líneas de cada factura |
| `Clientes` | Catálogo de clientes |
| `PRODUCTOS` | Catálogo de productos/servicios |
| `USUARIOS` | Usuarios del sistema Syma |
| `M_ROLES` | Roles del sistema de reportes |
| `M_ROL_MODULOS` | Módulos habilitados por rol |
| `M_USUARIO_ROL` | Asignación usuario → rol |

### ORDEN_SERVICIO — columnas importantes
| Columna | Descripción |
|---------|-------------|
| `NO_ORDEN` | PK |
| `FECHA` | Fecha programada del servicio |
| `FECHA_REGISTRO` | Fecha real de creación |
| `FECHA_ESTADO` | Fecha del último cambio de estado |
| `ESTADO` | **1**=Pendiente **2**=En proceso **3**=Finalizado **4**=Facturado **5**=No Reparable |
| `NO_TRAE` | Problema reportado por el cliente al ingreso |
| `ESTADO_INGRESO` | Condición física del equipo |
| `OBSERVACIONES` | Notas del técnico |
| `SECUENCIA_DIA` | Orden visual en la agenda del día |

### Códigos de servicio técnico
- `ST003` — Servicio técnico principal (cobrado por trabajo/hora)
- `ST001` — Servicio técnico alternativo

### Nota importante: ORDEN_SERVICIO vs PUNTO_VENTA
Estos dos sistemas **no están vinculados**. No existe campo `NO_FACTURA` en `ORDEN_SERVICIO`.
Algunos servicios ST003 se facturan directo en `PUNTO_VENTA` sin crear orden de taller → por eso el tab "Servicio ST003" consulta `PUNTO_VENTA_DETALLE` directamente.

---

## PERMISOS Y NAVEGACIÓN — CHECKLIST AL AGREGAR UN TAB NUEVO

Cuando se agrega un nuevo tab hay **9 lugares** que actualizar:

| # | Archivo | Lugar | Acción |
|---|---------|-------|--------|
| 1 | `index.html` | Panel HTML | Agregar `<div id="tab-X" class="panel">` |
| 2 | `index.html` | `GRUPOS_NAV` | Agregar `'X'` en `tabs:[]` del grupo |
| 3 | `index.html` | `TAB_LABELS` instancia 1 (~línea 1388) | Agregar `x:'Label'` |
| 4 | `index.html` | `TAB_LABELS` instancia 2 (~línea 4707) | Agregar `x:'Label'` |
| 5 | `index.html` | `MODULO_LABELS` (~línea 4702) | Agregar `x:'Label'` |
| 6 | `index.html` | `MODULOS_ORDEN` (~línea 4710) | Agregar `'x'` en posición correcta |
| 7 | `index.html` | Array fechas por defecto (~línea 1313) | Agregar `'x-fi'` y `'x-ff'` si tiene fechas |
| 8 | `permisos.py` | `MODULOS_TODOS` | Agregar `'x'` |
| 9 | `permisos.py` | `MODULOS_POR_ROL_DEFAULT` | Agregar al rol correspondiente |

---

## BACKUPS MANUALES

| Fecha | Directorio |
|-------|-----------|
| 2026-04-01 11:29 | `reportes-syma-backup-20260401-112936` |
| 2026-04-01 12:27 | `reportes-syma-backup-20260401-122711` |

> A partir de v1.0.0 el control de versiones se maneja con **Git** (ver protocolo arriba).

---

## ADVERTENCIAS / GOTCHAS

1. **Caché del navegador** — Después de cambios en `index.html` el usuario debe hacer `Cmd+Shift+R` (Mac) o `Ctrl+Shift+R` (Windows).
2. **Importación colisionada** — `get_lineas_compra` existe en `compras.py` y `cxp.py`. En `main.py` la de CXP se importa con alias `get_lineas_compra_cxp`.
3. **TAB_LABELS duplicado** — Hay DOS instancias de este dict en `index.html`. Siempre actualizar ambas.
4. **SSH interactivo** — Nunca usar `pkill` vía SSH (mata la sesión). Siempre usar `systemctl restart`.
5. **Días abierta** — Solo se muestra en estados 1 y 2. El contador se detiene al pasar a estado 3, 4 o 5 usando `FECHA_ESTADO` como fecha de cierre.

---

## BITÁCORA DE CAMBIOS

### [SESIÓN 1] Correcciones base

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 1 | Fix | `get_lineas_compra` de `cxp.py` sobreescribía import de `compras.py` → lista vacía. Solución: alias `get_lineas_compra_cxp` | `main.py` |
| 2 | Fix | Función duplicada `toggleLineasCompra` — segunda definición sobreescribía la primera | `index.html` |
| 3 | Fix | Campos incorrectos en panel calendario CXP (`costo_unitario` → `costo_unit`, `l.linea` → `unidad`) | `index.html` |

### [SESIÓN 1] Módulo Taller

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 4 | Fix | Campo problema del cliente era `NO_TRAE`, no encontrado inicialmente. Agregado a queries y al INSERT | `taller.py` |
| 5 | Fix | `ESTADOS_TALLER` incorrectos. Confirmados: 1=Pendiente 2=En proceso 3=Finalizado 4=Facturado 5=No Reparable | `taller.py`, `index.html` |
| 6 | Nuevo | Contador `dias_abierta` con semáforo 🟢🟡🔴. Se detiene en estados 3/4/5 usando `FECHA_ESTADO` | `taller.py`, `index.html` |
| 7 | Fix | Etiqueta "Ingresada" → "Pendiente" en filtro de estado | `index.html` |
| 8 | Nuevo | Columna y métrica Total Servicio ST003 en reporte Taller (LEFT JOIN a `ORDEN_SERVICIO_DETALLE`) | `taller.py`, `index.html` |
| 9 | Nuevo | Panel "Órdenes Antiguas" (backlog) en Agenda con drag & drop para reasignar al calendario | `taller.py`, `main.py`, `index.html` |

### [SESIÓN 2] Tab Servicio ST003

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 10 | Nuevo | Tab "Servicio ST003" entre Taller e Ingreso Taller. Query a `PUNTO_VENTA_DETALLE` WHERE `ID_PRODUCTO='ST003'`. Endpoint `GET /api/taller/st003` | `taller.py`, `main.py`, `permisos.py`, `index.html` |
| 11 | Fix | Tab ST003 no aparecía en panel Admin. Faltaban 4 referencias en `index.html` + `permisos.py` | `index.html`, `permisos.py` |
| 12 | Fix | Tab ST003 mostraba ST001 también. Cambiar `IN ('ST003','ST001')` → `= 'ST003'` | `taller.py` |
| 13 | Fix | Filtros del tab ST003 en vertical. Cambiar a layout horizontal con flexbox | `index.html` |

### [SESIÓN 2] Infraestructura Git

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 14 | Infra | `git init` local + `.gitignore` + commit inicial `v1.0.0` | `.gitignore`, todos |
| 15 | Infra | Servidor Ubuntu configurado como remoto `servidor`. `receive.denyCurrentBranch updateInstead` para push directo | servidor |
| 16 | Docs | Bitácora reestructurada con sección "Estado actual", frases clave de sesión y checklist de 9 pasos para nuevos tabs | `BITACORA_TECNICA.md` |

---
*Actualizar esta bitácora al cierre de cada sesión con `"cierra la sesión"`*
