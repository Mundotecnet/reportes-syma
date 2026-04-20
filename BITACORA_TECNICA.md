# BITÁCORA TÉCNICA — Reportes MUNDOTEC
**Sistema:** FastAPI + SQL Server Syma
**Servidor:** `mserver` — Ubuntu 22.04 — IP `192.168.88.250`
**Ruta del proyecto:** `/home/lroot/reportes-syma`
**Entorno de trabajo:** Claude Code corre directamente en el servidor
**Última actualización:** 2026-04-18

---

## FRASES CLAVE DE SESIÓN

| Frase del usuario | Acción de Claude |
|-------------------|-----------------|
| `"iniciamos sesión en reportes"` | Leer esta bitácora → contexto completo cargado |
| `"iniciamos sesión en mundotec"` | Leer `/home/lroot/mundotec-web/BITACORA.md` |
| `"cierra la sesión"` | Actualizar bitácora + `git commit` |
| `"hacer respaldo"` / `"realiza respaldo"` | Ejecutar `bash /home/lroot/scripts/backup_reportes.sh` |
| `"lamb"` | Ejecutar `bash /home/lroot/scripts/generar_documentos.sh` — regenera ambos PDFs y los copia al disco externo |

---

## ══ ESTADO ACTUAL DEL SISTEMA ══

### Versión activa: `v1.1.0`
### Git: rama `main` — remoto `servidor` (ssh://lroot@192.168.88.250/home/lroot/reportes-syma)

### Módulos funcionando al 100%
| Módulo | Tab ID | Descripción |
|--------|--------|-------------|
| **Dashboard** | `dashboard` | Métricas consolidadas: ventas, compras, bienes/servicios, crédito, CXC, CXP por moneda |
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
| **Garantías** | `garantias` | Seguimiento de garantías ligadas a órdenes de taller — pasos, archivos adjuntos, bitácora de cambios, PDF e email |
| Orden Compra | `orden-compra` | Gestión de órdenes de compra internas |
| **Facturas en Proceso** | `fproceso` | Facturas ESTADO='P' con detalle expandible, seriales y resumen acumulado por producto |
| **Cierre de Caja** | `cierre-caja` | Resumen diario de ventas + cobros CXC por forma de pago. Auto-carga + navegación ◀▶ días |
| **Caja Chica** | `caja-chica` | Registro de gastos diarios (fletes, aseo, guarda) con foto. Monto se resta del efectivo en cierre |
| **Control Efectivo** | `depositos` | Acumulado de efectivo neto (ventas - caja chica) vs depósitos bancarios. Registra depósitos con foto comprobante |
| Admin | `admin` | Gestión de roles y permisos por módulo |

### Orden de tabs en navegación
```
📊 Dashboard:  dashboard
💰 Ventas:     ventas → pagos → productos → cxc → cv → fproceso
🛒 Compras:    compras → cxp → cal-pagos
📦 Inventario: inv-ajustes → hist-ajustes
🔧 Taller:     taller → st003 → ingreso-taller → agenda-taller → orden-compra → garantias
🏦 Caja/Banco: cierre-caja → caja-chica → depositos
⚙ Admin:       admin
```

### Pendientes / Ideas futuras
- [ ] Exportar reporte ST003 a Excel/PDF
- [ ] Agregar filtro de búsqueda por cliente en tab ST003
- [ ] Vincular órdenes de taller con facturas (requiere cambio en Syma — no hay campo `NO_FACTURA` en `ORDEN_SERVICIO`)
- [ ] Exportar cierre de caja a PDF

---

## PROTOCOLO OBLIGATORIO ANTES DE CUALQUIER CAMBIO

> Claude Code corre **directamente en el servidor** (`mserver` / `192.168.88.250`).
> No hay sincronización Mac↔servidor. Se edita y commitea en el servidor mismo.

```
1. MODIFICAR archivos en /home/lroot/reportes-syma/

2. COMMIT con mensaje descriptivo
   git add <archivos modificados>
   git commit -m "descripción del cambio"

3. REINICIAR SERVICIO (si es necesario)
   sudo systemctl restart reportes.service
   sudo systemctl is-active reportes.service

4. VERIFICAR respuesta "active"

5. DOCUMENTAR en la sección "Bitácora de Cambios":
   - Número de cambio correlativo
   - Solicitud del usuario
   - Problema / causa raíz
   - Solución aplicada
   - Archivos modificados

6. AL CERRAR UN BLOQUE DE MEJORAS — crear tag de versión
   git tag -a v1.X.0 -m "descripción del release"
```

### Rollback a versión anterior
```bash
# Ver versiones disponibles
git tag

# Revertir
git checkout v1.0.0
sudo systemctl restart reportes.service
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
# Reiniciar servicio
sudo systemctl restart reportes.service
sudo systemctl is-active reportes.service

# Ver logs
sudo journalctl -u reportes.service -n 50
```

---

## BASE DE DATOS (tablas clave)

### Convención de tablas nuevas (M_ prefix)
> **REGLA:** Toda tabla creada por el sistema de reportes debe residir en la **misma base de datos SQL Server Syma** y usar el prefijo **`M_`** para diferenciarlas de las tablas originales del sistema SYMA.
> - Cuenta: `sa` (permisos completos confirmados)
> - Servidor: `192.168.88.250` (pyodbc via `db.py`)
> - Nunca usar SQLite (`banco.db`) para nuevas tablas

### Tablas SYMA originales (solo lectura)

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
| `ETransac` | Transacciones CXC (ID_CONCEPTO='02', STATUS='A'). **OJO:** usar `Clientes.SALDO` para totales CXC, no `ETransac.SALDO_DOC` (ETransac tiene facturas históricas duplicadas) |
| `ETransacP` | Transacciones CXP (ID_CONCEPTO='01', STATUS='A', SALDO_DOC>0) |
| `COMPRAS` | Facturas de proveedores. ID_MONEDA: 'CRC' o 'USD'. PROVEEDOR_ID=178 = IT SERVICE S.A. |
| `PUNTO_VENTA` | Estados: 'A'=Activa, 'P'=En Proceso (120 docs), 'C'=Cancelada |
| `PUNTO_VENTA_DETALLE` | Columna `SERIES` = serial del producto (puede ser NULL). NO tiene columna `LINEA`, ordenar por `ID_CP` |
| `CAJAS_TRANS` | Entradas/salidas manuales de caja (TIPO_ID='E'/'S', ESTADO='A') |
| `TipoPago` | Catálogo: 01=Efectivo, 02=Tarjeta, 03=Cheque, 04=Transf/Depósito, 06=Sinpe Móvil, 07=Plataforma Digital |

### Tablas M_ del sistema de reportes (creadas por nosotros en SQL Server Syma)

| Tabla | Descripción | DDL resumen |
|-------|-------------|-------------|
| `M_ROLES` | Roles del sistema de reportes | `id INT IDENTITY PK, nombre NVARCHAR(100), descripcion NVARCHAR(255)` |
| `M_ROL_MODULOS` | Módulos habilitados por rol | `rol_id INT FK, modulo NVARCHAR(50)` |
| `M_USUARIO_ROL` | Asignación usuario → rol | `login NVARCHAR(10), rol_id INT FK` |
| `M_ORDENES_COMPRA` | Órdenes de compra internas | Ver `reportes/ordenes_compra.py` |
| `M_OC_LINEAS` | Líneas de cada OC | Ver `reportes/ordenes_compra.py` |
| `M_AJUSTES` | Cabecera de ajustes de inventario | Ver `reportes/inventario_ajustes.py` |
| `M_AJUSTES_DETALLE` | Líneas de cada ajuste de inventario | Ver `reportes/inventario_ajustes.py` |
| `M_CAJA_CHICA` | Gastos diarios de caja chica | `ID INT IDENTITY PK, FECHA DATE, DETALLE NVARCHAR(255), MONTO DECIMAL(15,2), FOTO_PATH NVARCHAR(500), USUARIO NVARCHAR(100), CREADO_EN DATETIME DEFAULT GETDATE()` |
| `M_DEPOSITOS` | Depósitos bancarios registrados | `ID INT IDENTITY PK, FECHA DATE, BANCO NVARCHAR(100), MONTO DECIMAL(15,2), NOTAS NVARCHAR(500), FOTO_PATH NVARCHAR(500), USUARIO NVARCHAR(100), CREADO_EN DATETIME DEFAULT GETDATE()` |
| `M_GARANTIAS` | Cabecera de garantías por orden de taller | `ID INT IDENTITY PK, NO_ORDEN INT, ESTADO NVARCHAR(20), NO_FACT_COMPRA/VENTA, FECHAS, ARCHIVOS, NO_GUIA, TRANSPORTISTA, FECHA_ENVIO, RESOLUCION, NOTAS, USUARIO, CREADO_EN, ACTUALIZADO_EN` |
| `M_GARANTIAS_BITACORA` | Historial de cambios por garantía | `ID INT IDENTITY PK, GARANTIA_ID INT FK, FECHA DATETIME, DETALLE NVARCHAR(1000), USUARIO NVARCHAR(100)` |

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

---

## SISTEMA DE RESPALDO

### Esquema de capas

```
/home/lroot/reportes-syma/          ← Repo de trabajo
        │
        ├── git push backup main
        │         └── /home/lroot/backups/reportes-syma.git       ← Bare repo (historial permanente)
        │
        └── git bundle create
                  ├── /home/lroot/backups/reportes_git_FECHA.bundle     ← Snapshot diario (14 días)
                  └── /mnt/backup-ext/MUNDOTEC/backups-servidor/        ← Disco externo (si conectado)
```

> **Nota:** La BD está en SQL Server externo (`192.168.10.15`). Su respaldo depende del servidor SQL Server, no de este script.

### Archivos generados
| Archivo | Contenido | Retención |
|---------|-----------|-----------|
| `reportes-syma.git/` | Bare repo — historial git completo | Permanente |
| `reportes_git_FECHA.bundle` | Snapshot portátil del historial | 14 días |
| `reportes_static_FECHA.tar.gz` | Fotos de garantías, caja chica, depósitos | 14 días |

### Scripts
| Script | Función | Cron |
|--------|---------|------|
| `backup_reportes.sh` | Git + Static + SQL Server (si no corrió antes) | 02:30 AM diario |

### Disco externo
| Campo | Valor |
|-------|-------|
| Punto de montaje | `/mnt/backup-ext` |
| Carpeta | `/mnt/backup-ext/MUNDOTEC/backups-servidor/` |
| UUID | `1CFE7C05FE7BD60C` (NTFS, 932 GB) |
| fstab | `nofail` — servidor arranca aunque no esté conectado |

### Log
`/home/lroot/backups/backup_reportes.log`

---

## PROTOCOLO DE RESPALDO

### Respaldo manual
```bash
bash /home/lroot/scripts/backup_reportes.sh
```

### Verificar último respaldo
```bash
tail -20 /home/lroot/backups/backup_reportes.log
```

### Restaurar código
```bash
# Desde bare repo (historial completo)
git clone /home/lroot/backups/reportes-syma.git reportes-syma-restaurado

# Desde bundle diario (snapshot portátil)
git clone /home/lroot/backups/reportes_git_FECHA.bundle reportes-syma-restaurado
```

### Ver historial completo del bare repo
```bash
git --git-dir=/home/lroot/backups/reportes-syma.git log --oneline
```

### Restaurar archivos estáticos (fotos)
```bash
tar -xzf /home/lroot/backups/reportes_static_FECHA.tar.gz -C /home/lroot/reportes-syma/
```

---

## BACKUPS MANUALES (histórico)

| Fecha | Directorio |
|-------|-----------|
| 2026-04-01 11:29 | `reportes-syma-backup-20260401-112936` |
| 2026-04-01 12:27 | `reportes-syma-backup-20260401-122711` |
| 2026-04-07 11:01 | `reportes-syma-backup-20260407-110123` |
| 2026-04-07 19:26 | `reportes-syma-backup-20260407-192602` |

> A partir de v1.0.0 el control de versiones se maneja con **Git** (ver protocolo arriba).

---

## ADVERTENCIAS / GOTCHAS

1. **Caché del navegador** — Después de cambios en `index.html` el usuario debe hacer `Cmd+Shift+R` (Mac) o `Ctrl+Shift+R` (Windows).
2. **Importación colisionada** — `get_lineas_compra` existe en `compras.py` y `cxp.py`. En `main.py` la de CXP se importa con alias `get_lineas_compra_cxp`.
3. **TAB_LABELS duplicado** — Hay DOS instancias de este dict en `index.html`. Siempre actualizar ambas.
4. **SSH interactivo** — Nunca usar `pkill` vía SSH (mata la sesión). Siempre usar `systemctl restart`.
5. **Días abierta** — Solo se muestra en estados 1 y 2. El contador se detiene al pasar a estado 3, 4 o 5 usando `FECHA_ESTADO` como fecha de cierre.
6. **CXC saldo correcto** — Siempre usar `Clientes.SALDO` (118 clientes ≈ ₡10.5M). `ETransac.SALDO_DOC` devuelve 4x más porque incluye transacciones históricas. Confirmado contra reporte Excel de Syma.
7. **IT SERVICE PROVEEDOR_ID=178** — `IT SERVICE SOCIEDAD ANONIMA`. Excluir de Compras y CXP con checkbox. En Dashboard CXP es exclusión permanente por parámetro `excluir_itservice`.
8. **Monedas en Dashboard** — Ventas: `PUNTO_VENTA.ID_MONEDA`. CXC: `Clientes.ID_MONEDA`. CXP: `ETransacP.ID_MONEDA`. Detectar USD con `RTRIM(ISNULL(ID_MONEDA,'CRC')) = 'USD'`.
9. **PUNTO_VENTA_DETALLE sin LINEA** — No existe columna `LINEA`. Usar `ID_CP` para ordenar líneas de detalle.
10. **Efectivo en PUNTO_VENTA** — El efectivo real es `TOTAL - MONTO_TARJETAS - MONTO_CHEQUES - MONTO_TRANSFERENCIAS`, PERO solo cuando `ID_CONCEPTO='01'` (contado). Para `ID_CONCEPTO='02'` (crédito) el efectivo es 0 aunque `MONTO_*=0`. Siempre usar `CASE WHEN ID_CONCEPTO='01' THEN ... ELSE 0`.
11. **Tablas nuevas → SQL Server con prefijo M_** — Nunca crear tablas en SQLite. Toda tabla nueva va en SQL Server Syma (misma conexión de `db.py`) con prefijo `M_` para distinguirlas de las tablas originales de SYMA.

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

### [SESIÓN 3] Dashboard General + Excluir IT SERVICE

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 17 | Nuevo | Tab `dashboard` como primer grupo de navegación. Métricas: ventas (contado/crédito), compras (CRC/USD), bienes/servicios, recuperación crédito, saldo CXC, saldo CXP | `reportes/dashboard.py`, `main.py`, `index.html`, `permisos.py` |
| 18 | Nuevo | Botones de período rápido: "Este mes", "Mes anterior", "Este año" en dashboard | `index.html` |
| 19 | Nuevo | Proveedor IT SERVICE (PROVEEDOR_ID=178) excluible con checkbox en tabs Compras y CXP | `reportes/compras.py`, `reportes/cxp.py`, `main.py`, `index.html` |
| 20 | Nuevo | Checkbox "Sin IT SERVICE" en Dashboard — filtra saldo CXP | `reportes/dashboard.py`, `main.py`, `index.html` |

### [SESIÓN 4] Dashboard — Separación por moneda + Fix CXC

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 21 | Nuevo | Saldo CXP en dashboard separado en colones y dólares (`ETransacP.ID_MONEDA`) | `reportes/dashboard.py`, `index.html` |
| 22 | Nuevo | Ventas en dashboard separadas en colones y dólares (`PUNTO_VENTA.ID_MONEDA`) | `reportes/dashboard.py`, `index.html` |
| 23 | Nuevo | Saldo CXC en dashboard separado en colones y dólares | `reportes/dashboard.py`, `index.html` |
| 24 | Fix | **CXC dashboard incorrecto**: usaba `ETransac.SALDO_DOC` (₡44.6M / 412 facturas) en lugar de `Clientes.SALDO` (₡10.5M / 118 clientes). Auditado contra Excel de Syma. Corregido a `FROM Clientes WHERE ESTADO='A' AND SALDO>0` | `reportes/dashboard.py`, `index.html` |
| 25 | Fix | `usd()` formatter no estaba en scope global. Movido junto a `crc()` en línea 1372 para que `cargarDashboard()` pueda usarlo | `index.html` |

### [SESIÓN 5] Tab Facturas en Proceso

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 26 | Nuevo | Tab `fproceso` en grupo Ventas. Lista facturas `PUNTO_VENTA.ESTADO='P'` con filtros fecha y búsqueda. Endpoint `GET /api/facturas-proceso` | `reportes/facturas_proceso.py`, `main.py`, `permisos.py`, `index.html` |
| 27 | Nuevo | Detalle expandible por factura (clic en fila): líneas con código, descripción, cantidad, precio, importe, IVA, total | `index.html` |
| 28 | Nuevo | Serial por línea de detalle: muestra etiqueta naranja `📋 SERIAL` si `PUNTO_VENTA_DETALLE.SERIES` tiene valor | `reportes/facturas_proceso.py`, `index.html` |
| 29 | Nuevo | Resumen acumulado por producto al pie del reporte: agrupa todas las líneas, ordena por total DESC, muestra N° documentos donde aparece cada producto como chips azules | `index.html` |
| 30 | Fix | `ORDER BY pvd.LINEA` fallaba — columna inexistente. Corregido a `ORDER BY pvd.ID_CP` | `reportes/facturas_proceso.py` |

### [SESIÓN 6] Cierre de Caja + Caja Chica + Migración SQL Server

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 31 | Nuevo | Módulo **Cierre de Caja** (`cierre-caja`). Query optimizado: 2 aggregados + 2 detalles. Ventas del día por forma de pago (solo contado suma efectivo; crédito va a columna CXC separada). Cobros CXC del día desde `ETransac`. CAJAS_TRANS para entradas/salidas manuales | `reportes/cierre_caja.py`, `main.py`, `permisos.py`, `index.html` |
| 32 | Fix | Facturas crédito (`ID_CONCEPTO='02'`) sumaban en efectivo porque formula `TOTAL-0-0-0=TOTAL`. Corregido con `CASE WHEN ID_CONCEPTO='01' THEN ... ELSE 0` en query. Columna CXC separada en tabla | `reportes/cierre_caja.py`, `index.html` |
| 33 | Fix | Columna "Forma Pago" mostraba "Efectivo" para facturas crédito (JOIN a TipoPago devuelve '01'). Corregido en JS: `r.concepto==='02' ? 'CXC' : r.forma_pago` | `index.html` |
| 34 | Nuevo | Módulo **Caja Chica** (`caja-chica`). Registro de gastos diarios (Fletes, Aseo, Guarda) con Fecha, Detalle, Monto y foto adjunta. Foto guardada en `static/caja_chica/`. Total del día se descuenta del efectivo en cierre de caja | `reportes/caja_chica.py`, `main.py`, `permisos.py`, `index.html` |
| 35 | Infra | **Migración SQLite → SQL Server**: Caja Chica inicialmente usaba `banco.db` (SQLite). Creada tabla `M_CAJA_CHICA` en SQL Server Syma (cuenta `sa`). `reportes/caja_chica.py` reescrito para usar `ejecutar_query`/`get_connection` de `db.py`. Eliminada dependencia de `sqlite3`. `cc_init()` ahora solo crea directorio de fotos | `reportes/caja_chica.py`, `main.py` |
| 36 | Docs | **Convención M_ prefix**: Toda tabla nueva debe residir en SQL Server Syma con prefijo `M_`. Documentado en bitácora como regla. Inventario de todas las tablas M_ existentes | `BITACORA_TECNICA.md` |

### [SESIÓN 9] — 2026-04-12 — Sistema de respaldo automático + Git versioning

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 41 | Infra | Script `/home/lroot/scripts/backup_reportes.sh` — respaldo nocturno automático | nuevo script |
| 42 | Infra | Bare repo git `/home/lroot/backups/reportes-syma.git` — remoto `backup` permanente | git config |
| 43 | Infra | Bundle diario `reportes_git_FECHA.bundle` — snapshot portátil del historial completo | script |
| 44 | Infra | Static tar.gz `reportes_static_FECHA.tar.gz` — fotos garantías, caja chica, depósitos | script |
| 45 | Infra | Cron 02:30 AM diario para ejecución automática | crontab |
| 46 | Infra | Retención 14 días — limpieza automática de respaldos antiguos | script |
| 47 | Fix | `.gitignore` actualizado — excluye banco.db, static/uploads, query_tipos.py, reportes/index.html duplicado | `.gitignore` |
| 48 | Docs | Bitácora actualizada — Sesiones 8 y 9, tablas M_GARANTIAS, versión v1.1.0 | `BITACORA_TECNICA.md` |

---

### [SESIÓN 8] — 2026-04-09 — Módulo Garantías + PDF + Fix fuentes Unicode

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 37 | Nuevo | Tabla `M_GARANTIAS` en SQL Server — cabecera de garantía por orden de taller (facturas compra/venta, guía envío, resolución, archivos adjuntos) | SQL Server |
| 38 | Nuevo | Tabla `M_GARANTIAS_BITACORA` en SQL Server — historial de cambios por garantía con timestamp y usuario | SQL Server |
| 39 | Nuevo | `reportes/garantias.py` — CRUD completo: `get_garantias`, `get_garantia_detalle`, `crear_garantia`, `actualizar_garantia`, `agregar_nota_bitacora` | `reportes/garantias.py` |
| 40 | Nuevo | Tab `garantias` en grupo 🔧 Taller. Flujo de pasos: Nuevo → Documentado → Enviado → Resuelto. Archivos adjuntos subibles (fact. compra, fact. venta, guía). Bitácora de notas por garantía | `templates/index.html`, `reportes/permisos.py` |
| 41 | Nuevo | Endpoints: `GET /api/garantias`, `GET /api/garantias/{id}`, `POST /api/garantias`, `PUT /api/garantias/{id}`, `POST /api/garantias/{id}/nota`, `POST /api/garantias/{id}/archivo` | `main.py` |
| 42 | Nuevo | `exports/pdf_garantia.py` — genera PDF de informe de garantía con datos del equipo, pasos completados y bitácora | `exports/pdf_garantia.py` |
| 43 | Nuevo | Botón "📄 Informe PDF" + envío por email desde tab garantías. Auto-nota en bitácora al enviar | `templates/index.html`, `main.py` |
| 44 | Fix | Fuentes DejaVu (`DejaVuSans.ttf`) aplicadas a **todas** las filas de tablas en PDF — el símbolo ₡ se cortaba en filas de datos con Helvetica | `exports/pdf.py`, `exports/pdf_garantia.py` |
| 45 | Infra | `config.py` ampliado con `SMTP_HOST/PORT/USER/PASSWORD/FROM` para envío de PDFs por email | `config.py` |

---

### [SESIÓN 7] Módulo Control de Efectivo / Depósitos

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 37 | Nuevo | Tabla `M_DEPOSITOS` creada en SQL Server Syma (Fecha, Banco, Monto, Notas, FotoPath, Usuario, CreadoEn) | SQL Server |
| 38 | Nuevo | `reportes/depositos.py`: CRUD depósitos + `get_resumen_control_efectivo(fecha_ini, fecha_fin)`. Calcula efectivo diario neto (ef_ventas + ef_cobros_CXC_efectivo − caja_chica) vs depósitos, con saldo acumulado corriente por día | `reportes/depositos.py` |
| 39 | Nuevo | Endpoints: `GET/POST/DELETE /api/depositos` y `GET /api/control-efectivo`. POST acepta form multipart con foto | `main.py` |
| 40 | Nuevo | Tab `depositos` (Control Efectivo) en grupo 🏦 Caja/Banco. Métricas: acumulado período, total depositado, saldo en caja (naranja/rojo según signo), total caja chica. Tabla resumen diario con saldo corriente. Formulario de depósito con Fecha/Banco/Monto/Notas/Foto. Lista de depósitos con foto y botón eliminar | `templates/index.html`, `permisos.py` |

---

### [SESIÓN 10] — 2026-04-18 — Fix envío de correo en módulo Garantías

| # | Tipo | Descripción | Archivos |
|---|------|-------------|----------|
| 49 | Fix | **NameError `EMPRESA_NOMBRE`**: en `api_enviar_informe` el import de `config` no incluía `EMPRESA_NOMBRE` — causaba HTTP 500 al intentar enviar. Corregido agregando al import | `main.py` |
| 50 | Nuevo | **Adjuntos de archivos al correo**: el correo ahora adjunta automáticamente factura de compra, factura de venta y guía de envío si existen en disco. Se omiten sin error si no hay archivo. La nota en bitácora lista los archivos adjuntados | `main.py` |

---
*Actualizar esta bitácora al cierre de cada sesión con `"cierra la sesión"`*
