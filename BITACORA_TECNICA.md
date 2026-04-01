# BITÁCORA TÉCNICA — Reportes MUNDOTEC
**Sistema:** FastAPI + SQL Server Syma
**Servidor:** Ubuntu 192.168.88.250:8000
**Última actualización:** 2026-04-01

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
```
# Ver versiones disponibles
git tag

# Revertir localmente
git checkout v1.0.0

# Revertir en servidor
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
│   ├── ventas.py                    # Reporte ventas
│   ├── compras.py                   # Reporte compras
│   ├── cxp.py                       # Cuentas x pagar
│   ├── cxc.py                       # Cuentas x cobrar
│   ├── productos.py                 # Productos vendidos
│   ├── inventario.py                # Inventario
│   ├── inventario_ajustes.py        # Ajustes de inventario
│   ├── compras_ventas.py            # Gráfico compras vs ventas
│   ├── pagos.py                     # Pagos de clientes
│   ├── ordenes_compra.py            # Órdenes de compra
│   └── permisos.py                  # Roles y módulos de usuario
├── exports/
│   ├── excel.py                     # Exportación Excel
│   ├── pdf.py                       # Exportación PDF general
│   └── pdf_oc.py                    # PDF órdenes de compra
├── templates/
│   ├── index.html                   # SPA completa (todo el frontend)
│   └── login.html                   # Pantalla de login
└── static/                          # CSS, JS, imágenes estáticas
```

---

## COMANDOS DE ACCESO AL SERVIDOR

```bash
# SCP un archivo
sshpass -p '87060002' scp <local> lroot@192.168.88.250:<remoto>

# Reiniciar servicio
sshpass -p '87060002' ssh -tt lroot@192.168.88.250 \
  "echo '87060002' | sudo -S systemctl restart reportes.service"

# Ver logs del servicio
sshpass -p '87060002' ssh lroot@192.168.88.250 \
  "sudo journalctl -u reportes.service -n 50"

# Estado del servicio
sshpass -p '87060002' ssh lroot@192.168.88.250 \
  "systemctl is-active reportes.service"
```

---

## ESTRUCTURA DE BASE DE DATOS (tablas clave)

| Tabla                    | Descripción                                              |
|--------------------------|----------------------------------------------------------|
| `ORDEN_SERVICIO`         | Cabecera de órdenes de taller                            |
| `ORDEN_SERVICIO_DETALLE` | Líneas de cada orden de taller                           |
| `ORDEN_SERVICIO_TIPOS`   | Catálogo de tipos de orden                               |
| `PUNTO_VENTA`            | Facturas/tiquetes emitidos                               |
| `PUNTO_VENTA_DETALLE`    | Líneas de cada factura                                   |
| `Clientes`               | Catálogo de clientes                                     |
| `PRODUCTOS`              | Catálogo de productos/servicios                          |
| `USUARIOS`               | Usuarios del sistema Syma                                |
| `M_ROLES`                | Roles de acceso (tabla propia del sistema de reportes)   |
| `M_ROL_MODULOS`          | Módulos habilitados por rol                              |
| `M_USUARIO_ROL`          | Asignación usuario→rol                                   |

### Columnas importantes de ORDEN_SERVICIO
| Columna          | Descripción                                      |
|------------------|--------------------------------------------------|
| `NO_ORDEN`       | Número de orden (PK)                             |
| `FECHA`          | Fecha programada del servicio                    |
| `FECHA_REGISTRO` | Fecha real de creación de la orden               |
| `FECHA_ESTADO`   | Fecha del último cambio de estado                |
| `ESTADO`         | 1=Pendiente, 2=En proceso, 3=Finalizado, 4=Facturado, 5=No Reparable |
| `NO_TRAE`        | Problema reportado por el cliente                |
| `ESTADO_INGRESO` | Condición física del equipo al ingreso           |
| `OBSERVACIONES`  | Notas del técnico                                |
| `SECUENCIA_DIA`  | Orden de aparición en la agenda del día          |

### Productos de servicio técnico
- `ST003` — Servicio técnico (principal, cobrado por hora/trabajo)
- `ST001` — Servicio técnico alternativo

---

## MÓDULOS DEL SISTEMA Y NAVEGACIÓN

```javascript
// Grupos de navegación (GRUPOS_NAV en index.html)
ventas:     ['ventas','pagos','productos','cxc','cv']
compras:    ['compras','cxp','cal-pagos']
inventario: ['inv-ajustes','hist-ajustes']
taller:     ['taller','st003','ingreso-taller','agenda-taller','orden-compra']
admin:      ['admin']

// MODULOS_TODOS (permisos.py y MODULOS_ORDEN en index.html)
['ventas','pagos','compras','productos','cxc','inventario',
 'inv-ajustes','hist-ajustes','cv','taller','st003',
 'ingreso-taller','agenda-taller','orden-compra','cxp','cal-pagos','admin']
```

### Rol por defecto "Taller"
`['taller', 'st003', 'ingreso-taller', 'agenda-taller', 'orden-compra']`

---

## BACKUPS REALIZADOS

| Fecha/Hora           | Directorio de backup                                    |
|----------------------|---------------------------------------------------------|
| 2026-04-01 11:29     | `reportes-syma-backup-20260401-112936`                  |
| 2026-04-01 12:27     | `reportes-syma-backup-20260401-122711`                  |

---

## BITÁCORA DE CAMBIOS

---

### [SESIÓN 1] Correcciones base del sistema

#### 1. Fix: Líneas de Compras y CXP no cargaban
- **Problema:** `get_lineas_compra` de `cxp.py` sobreescribía la importación de `compras.py` en `main.py`. La versión de CXP usaba columna `cd.LINEA` que no existe en `COMPRAS_DETALLE` → excepción silenciosa → lista vacía.
- **Solución:** Alias en `main.py`:
  ```python
  from reportes.cxp import ..., get_lineas_compra as get_lineas_compra_cxp
  ```
- **Archivos:** `main.py`

#### 2. Fix: Función duplicada `toggleLineasCompra`
- **Problema:** Dos definiciones en `index.html`, la segunda (incorrecta) sobreescribía la primera.
- **Solución:** Eliminar la primera definición (duplicada).
- **Archivos:** `templates/index.html`

#### 3. Fix: Nombres de campos incorrectos en panel de calendario CXP
- **Problema:** El JS usaba `costo_unitario`/`l.linea` (campos de CXP) pero la API devolvía campos de compras (`costo_unit`, `unidad`).
- **Solución:** Corregir nombres de campos en el JS del panel calendario.
- **Archivos:** `templates/index.html`

---

### [SESIÓN 1] Módulo Taller — mejoras completas

#### 4. Fix: Campo "Problema / Observaciones" faltante en modal de orden
- **Problema:** No se encontraba en qué columna estaba el dato. Se consultó `INFORMATION_SCHEMA` y datos reales.
- **Resolución:** El campo es `NO_TRAE` en `ORDEN_SERVICIO` (problema reportado por el cliente).
- **Solución:** Agregar `RTRIM(ISNULL(os.NO_TRAE,'')) AS problema` en `get_orden_completa` y `get_taller`. Agregar en INSERT de `crear_orden`.
- **Archivos:** `reportes/taller.py`

#### 5. Fix: Estados de taller incorrectos
- **Problema:** El dict `ESTADOS_TALLER` tenía estados equivocados (3="En espera", 4="Finalizada", 5="Anulada").
- **Corrección confirmada por usuario:**
  - 1 = Pendiente
  - 2 = En proceso
  - 3 = Finalizado
  - 4 = Facturado
  - 5 = No Reparable
- **Archivos:** `reportes/taller.py`, `templates/index.html`

#### 6. Nuevo: Contador de días abierta (`dias_abierta`)
- **Lógica:** Contar días desde `FECHA_REGISTRO` hasta hoy. Si estado IN (3,4,5) → usar `FECHA_ESTADO` como cierre (no sigue contando).
- **SQL:**
  ```sql
  DATEDIFF(day, os.FECHA_REGISTRO,
      CASE WHEN os.ESTADO IN (3,4,5)
           THEN ISNULL(os.FECHA_ESTADO, GETDATE())
           ELSE GETDATE() END) AS dias_abierta
  ```
- **Semáforo JS:** 🟢 <4 días, 🟡 4-7 días, 🔴 ≥8 días
- **Solo visible** para estados Pendiente y En proceso (no en Finalizado/Facturado/No Reparable)
- **Archivos:** `reportes/taller.py`, `templates/index.html`

#### 7. Fix: Etiqueta "Ingresada" → "Pendiente" en filtro
- **Archivos:** `templates/index.html`

#### 8. Nuevo: Columna y métrica Total Servicio ST003
- Se agrega LEFT JOIN en `get_taller` para traer `total_st003` y `desc_st003` de `ORDEN_SERVICIO_DETALLE` WHERE `ID_PRODUCTO='ST003'`.
- Nueva columna "Servicio ST003" en tabla de taller.
- Nueva métrica "Total servicio (ST003)" en panel de métricas.
- **Archivos:** `reportes/taller.py`, `templates/index.html`

#### 9. Nuevo: Panel "Órdenes Antiguas" (backlog) en Agenda
- **Función:** `get_ordenes_antiguas(year, month)` — órdenes con ESTADO IN (1,2) y FECHA < primer día del mes consultado.
- **Endpoint:** `GET /api/taller/ordenes-antiguas`
- **UI:** Panel colapsable encima del calendario con tarjetas arrastrables.
- **Drag & Drop:** Las tarjetas del backlog se pueden arrastrar a cualquier día del calendario para reasignarlas. El origen `data-fecha="backlog"` salta la validación de mismo-día.
- **Archivos:** `reportes/taller.py`, `main.py`, `templates/index.html`

---

### [SESIÓN 2] Nuevo tab "Servicio ST003"

#### 10. Nuevo: Tab independiente "Servicio ST003" en grupo Taller
- **Solicitud:** Tab propio que muestre servicios ST003 facturados directamente desde `PUNTO_VENTA_DETALLE`, por rango de fechas.
- **Posición en menú:** Entre "Taller" y "Ingreso Taller".
- **Función backend:** `get_servicios_st003(fecha_ini, fecha_fin)`
  - Query: `PUNTO_VENTA_DETALLE` INNER JOIN `PUNTO_VENTA`
  - Filtro: `UPPER(RTRIM(pvd.ID_PRODUCTO)) = 'ST003'` y `pv.ESTADO = 'A'`
  - Una fila por línea facturada
- **Endpoint:** `GET /api/taller/st003`
- **Columnas:** Fecha, Doc #, Tipo, Cliente, Código, Descripción, Cant., Precio unit., Importe, IVA, Total
- **Métricas:** Documentos, Líneas, Subtotal, IVA, Total
- **Filtros:** Fecha inicio / Fecha fin en horizontal + botón Generar
- **Permisos:** Agregado a `MODULOS_TODOS` y rol `Taller` en `permisos.py`
- **Archivos:** `reportes/taller.py`, `main.py`, `reportes/permisos.py`, `templates/index.html`

#### 11. Fix: Tab ST003 no aparecía en panel de permisos (Admin)
- **Problema:** Tres diccionarios/arrays en `index.html` debían actualizarse: `TAB_LABELS` (hay DOS instancias), `MODULO_LABELS` y `MODULOS_ORDEN`. Solo se actualizaron algunas.
- **Solución:** Actualizar las 4 referencias + `MODULOS_TODOS` en `permisos.py`.
- **Archivos:** `templates/index.html`, `reportes/permisos.py`

#### 12. Fix: Tab ST003 mostraba ST001 también
- **Problema:** El query original filtraba `IN ('ST003','ST001')`.
- **Solución:** Cambiar a `= 'ST003'` únicamente.
- **Archivos:** `reportes/taller.py`

---

## PUNTOS TÉCNICOS IMPORTANTES

### Sobre el desfase Ventas vs Taller
- El reporte **Ventas → Productos Vendidos** filtrando ST003 muestra un total **mayor** que el reporte **Taller → Taller** filtrando Facturado.
- **Causa confirmada por usuario:** Algunos servicios ST003 se facturan **directamente** en `PUNTO_VENTA` sin crear una orden de taller. Las dos tablas (`PUNTO_VENTA_DETALLE` y `ORDEN_SERVICIO_DETALLE`) son **sistemas independientes**, sin campo de referencia cruzada (`NO_FACTURA` no existe en `ORDEN_SERVICIO`).
- **Solución implementada:** Tab "Servicio ST003" consulta directamente `PUNTO_VENTA_DETALLE` y muestra los servicios facturados independientemente del taller.

### Sobre el campo NO_TRAE
- En `ORDEN_SERVICIO`, el campo `NO_TRAE` guarda el **problema reportado por el cliente** al dejar el equipo.
- `ESTADO_INGRESO` = condición física del equipo.
- `OBSERVACIONES` = notas del técnico durante el proceso.

### Caché del navegador
- El servidor FastAPI sirve `index.html` leyendo el archivo directamente (sin headers de caché).
- Después de desplegar cambios en `index.html`, el usuario debe hacer **hard refresh** (`Cmd+Shift+R` en Mac, `Ctrl+Shift+R` en Windows) para ver los cambios.

### Sobre la navegación y permisos
Cuando se agrega un nuevo tab, hay **6 lugares** que actualizar en `index.html` + `permisos.py`:

| # | Lugar                        | Descripción                                      |
|---|------------------------------|--------------------------------------------------|
| 1 | Panel HTML `<div id="tab-X">` | El panel visual del tab                         |
| 2 | `GRUPOS_NAV`                 | Agregar a la lista `tabs:[]` del grupo           |
| 3 | `TAB_LABELS` (instancia 1)   | Label del tab en la navegación principal         |
| 4 | `TAB_LABELS` (instancia 2)   | Label del tab en el sistema de permisos          |
| 5 | `MODULO_LABELS`              | Label en los checkboxes del panel Admin          |
| 6 | `MODULOS_ORDEN`              | Orden de aparición en checkboxes del panel Admin |
| 7 | `MODULOS_TODOS` en `permisos.py` | Lista maestra de módulos del sistema         |
| 8 | `MODULOS_POR_ROL_DEFAULT`    | Agregar al rol correspondiente si aplica         |
| 9 | Fechas por defecto (si aplica) | Agregar IDs al array de inicialización         |

---

## PENDIENTES / IDEAS FUTURAS

- [ ] Exportar reporte ST003 a Excel/PDF
- [ ] Agregar filtro de búsqueda por cliente en tab ST003
- [ ] Considerar vincular órdenes de taller con facturas (requiere cambio en Syma)
- [ ] Agregar campo `NO_FACTURA` en `ORDEN_SERVICIO` para cruzar con `PUNTO_VENTA`

---

*Documento generado el 2026-04-01. Actualizar con cada sesión de cambios.*
