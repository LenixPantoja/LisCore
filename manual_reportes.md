# Manual de Creación de Reportes Dinámicos — LisCore

> **Audiencia:** Administradores del sistema / desarrolladores que necesiten crear o modificar reportes dinámicos.  
> **Base URL:** `http://localhost:8000/api/reports`

---

## Índice

1. [¿Qué es un Reporte Dinámico?](#1-qué-es-un-reporte-dinámico)
2. [¿Dónde se almacena un reporte?](#2-dónde-se-almacena-un-reporte)
3. [Estructura completa de un reporte](#3-estructura-completa-de-un-reporte)
4. [Tipos de parámetros disponibles](#4-tipos-de-parámetros-disponibles)
5. [Cómo escribir la consulta SQL](#5-cómo-escribir-la-consulta-sql)
6. [Cómo escribir la plantilla HTML](#6-cómo-escribir-la-plantilla-html)
7. [Crear un reporte paso a paso (con ejemplos reales)](#7-crear-un-reporte-paso-a-paso)
8. [Modificar un reporte existente](#8-modificar-un-reporte-existente)
9. [Ejecutar un reporte](#9-ejecutar-un-reporte)
10. [Exportar a PDF](#10-exportar-a-pdf)
11. [Errores comunes y cómo corregirlos](#11-errores-comunes-y-cómo-corregirlos)
12. [Permisos RBAC requeridos](#12-permisos-rbac-requeridos)

---

## 1. ¿Qué es un Reporte Dinámico?

Un **Reporte Dinámico** es una definición almacenada en la base de datos que contiene:

- Una **consulta SQL** que extrae los datos que se quieren mostrar.
- Una **plantilla HTML** (con sintaxis Jinja2) que define cómo se presentan esos datos.
- Una lista de **parámetros** (filtros) que el usuario final completa antes de ejecutar el reporte.

El sistema ejecuta el SQL con los parámetros recibidos, renderiza el HTML con los resultados y lo devuelve listo para mostrar en pantalla o exportar a PDF. **No hay archivos de código que modificar** — todo se gestiona vía API.

---

## 2. ¿Dónde se almacena un reporte?

Los reportes se guardan en la base de datos PostgreSQL en dos tablas:

| Tabla | Contenido |
|---|---|
| `"DynamicReports"` | Datos principales del reporte (nombre, SQL, plantilla HTML) |
| `"ReportParameters"` | Parámetros / filtros asociados a cada reporte |

**No se crean archivos en el servidor.** Todo se administra exclusivamente a través de la API REST.

---

## 3. Estructura completa de un reporte

### 3.1 Datos del reporte (`DynamicReports`)

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `dr_name` | string (máx. 200) | ✅ Sí | Nombre legible del reporte, p. ej. `"Órdenes por Fecha"` |
| `dr_description` | string | No | Descripción corta del propósito del reporte |
| `dr_sql_query` | string | ✅ Sí | Consulta SQL de solo lectura (`SELECT` o `WITH`) |
| `dr_html_template` | string | ✅ Sí | Plantilla HTML con Jinja2 para mostrar los resultados |
| `dr_active` | boolean | No (default `true`) | `false` oculta el reporte de la lista sin borrarlo |

### 3.2 Datos de cada parámetro (`ReportParameters`)

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `rp_name` | string (máx. 100) | ✅ Sí | Nombre interno, **debe coincidir exactamente** con el `:parametro` en el SQL |
| `rp_label` | string (máx. 100) | ✅ Sí | Etiqueta visible para el usuario, p. ej. `"Fecha de inicio"` |
| `rp_type` | string | ✅ Sí | Tipo de control del formulario (ver sección 4) |
| `rp_required` | boolean | No (default `false`) | Si es `true`, el reporte no se ejecuta si falta este parámetro |
| `rp_default_value` | string | No | Valor por defecto en formato texto (p. ej. `"2026-01-01"`) |
| `rp_source_query` | string | No | SQL que genera las opciones para `select` / `multiselect` |
| `rp_order_index` | integer | No (default `0`) | Orden visual de los parámetros en el formulario |

---

## 4. Tipos de parámetros disponibles

| `rp_type` | Control en formulario | Formato del valor enviado en `params` |
|---|---|---|
| `date` | Selector de fecha | `"YYYY-MM-DD"` → p. ej. `"2026-05-13"` |
| `datetime` | Selector de fecha y hora | `"YYYY-MM-DDTHH:MM:SS"` → p. ej. `"2026-05-13T08:00:00"` |
| `text` | Caja de texto libre | Cualquier texto, p. ej. `"García"` |
| `number` | Campo numérico | Número entero o decimal, p. ej. `42` o `"42"` |
| `select` | Lista desplegable (opción única) | El valor seleccionado según `rp_source_query` |
| `multiselect` | Lista desplegable (múltiples) | Array de valores seleccionados |
| `checkbox` | Casilla verdadero/falso | `"true"` o `"false"` |
| `textarea` | Área de texto largo | Texto libre |

> **Nota técnica:** El sistema convierte automáticamente los tipos `date`, `datetime` y `number` de texto a objetos Python antes de enviarlos a PostgreSQL. El frontend puede enviar las fechas siempre como strings `"YYYY-MM-DD"`.

---

## 5. Cómo escribir la consulta SQL

### Reglas obligatorias

1. **Solo `SELECT` o `WITH ... SELECT`.** El sistema rechaza cualquier SQL que contenga `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `EXEC`, `GRANT` o `REVOKE`.
2. **Sin punto y coma al final.** El sistema lo ignora, pero es buena práctica omitirlo.
3. **Los parámetros se referencian con `:nombre_del_parametro`** (dos puntos + el `rp_name` exacto).
4. **Los nombres de tablas van entre comillas dobles** porque el esquema usa PascalCase: `"Orders"`, `"Patients"`, `"TestsLab"`, etc.

### Nombres de columnas importantes

| Entidad | Columna correcta | Nota |
|---|---|---|
| Nombre del paciente | `pt_firts_name` | Hay un typo en el original de la BD: `firts`, no `first` |
| Segundo nombre | `pt_middle_name` | |
| Apellido | `pt_last_name` | |
| Segundo apellido | `pt_second_last_name` | |
| Concatenar nombre completo | `pt_firts_name \|\| ' ' \|\| pt_last_name AS paciente` | |

### Ejemplo mínimo

```sql
SELECT
    o.od_id          AS orden,
    p.pt_firts_name || ' ' || p.pt_last_name AS paciente,
    o.od_date        AS fecha
FROM "Orders" o
JOIN "Patients" p ON p.pt_id = o.od_patient_id
WHERE o.od_date BETWEEN :fecha_inicio AND :fecha_fin
ORDER BY o.od_date DESC
```

- `:fecha_inicio` y `:fecha_fin` son los `rp_name` de los parámetros que se definan.
- Los alias (`AS orden`, `AS paciente`) se convierten en los nombres de columna disponibles en la plantilla HTML.

### CTEs (WITH)

```sql
WITH activos AS (
    SELECT od_id, od_patient_id, od_date
    FROM "Orders"
    WHERE od_cancelled = false
      AND od_date BETWEEN :fecha_inicio AND :fecha_fin
)
SELECT
    a.od_id   AS orden,
    p.pt_firts_name || ' ' || p.pt_last_name AS paciente,
    a.od_date AS fecha
FROM activos a
JOIN "Patients" p ON p.pt_id = a.od_patient_id
ORDER BY a.od_date
```

---

## 6. Cómo escribir la plantilla HTML

La plantilla usa **sintaxis Jinja2**. El motor inyecta dos variables:

| Variable | Tipo | Descripción |
|---|---|---|
| `data` | Lista de dicts | Cada elemento es una fila del resultado del SQL. Las claves son los alias de las columnas (`AS nombre`) |
| `params` | Dict | Los valores de los filtros enviados por el usuario (para mostrarlo en el encabezado del reporte) |

### Ejemplo de plantilla básica

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: Arial, sans-serif; font-size: 12px; }
    h2   { color: #2c3e50; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th    { background: #2c3e50; color: white; padding: 6px 8px; text-align: left; }
    td    { border-bottom: 1px solid #ddd; padding: 5px 8px; }
    tr:nth-child(even) { background: #f2f2f2; }
    .resumen { margin-top: 16px; font-weight: bold; }
  </style>
</head>
<body>
  <h2>Órdenes del período</h2>
  <p>
    Desde: <strong>{{ params.fecha_inicio }}</strong>
    &nbsp;—&nbsp;
    Hasta: <strong>{{ params.fecha_fin }}</strong>
  </p>

  {% if data %}
  <table>
    <thead>
      <tr>
        <th># Orden</th>
        <th>Paciente</th>
        <th>Fecha</th>
      </tr>
    </thead>
    <tbody>
      {% for row in data %}
      <tr>
        <td>{{ row.orden }}</td>
        <td>{{ row.paciente }}</td>
        <td>{{ row.fecha }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <p class="resumen">Total de registros: {{ data | length }}</p>
  {% else %}
  <p>No se encontraron resultados para el período seleccionado.</p>
  {% endif %}
</body>
</html>
```

### Acceso a columnas

- Si el SQL define `pt_firts_name || ' ' || pt_last_name AS paciente`, accedes con `row.paciente`.
- Si el SQL no usa alias, el nombre de columna es el de la base de datos: `row.pt_firts_name`.
- **Usa siempre alias** para que los nombres sean legibles en la plantilla.

---

## 7. Crear un reporte paso a paso

### Paso 1 — Diseñar el SQL en un cliente de BD

Antes de crear el reporte vía API, **prueba el SQL directamente en DBeaver, pgAdmin o similar**. Verifica que:
- El SQL devuelve los datos esperados.
- Todos los alias son correctos.
- Las columnas referenciadas existen con ese nombre exacto en la BD.

### Paso 2 — Llamar a `POST /api/reports/dynamic`

**Endpoint:** `POST http://localhost:8000/api/reports/dynamic`  
**Permiso requerido:** `Reports:DynamicCreate`  
**Content-Type:** `application/json`

**Cuerpo de la petición:**

```json
{
  "dr_name": "Órdenes por Fecha",
  "dr_description": "Lista todas las órdenes de laboratorio en un rango de fechas",
  "dr_sql_query": "SELECT o.od_id AS orden, p.pt_firts_name || ' ' || p.pt_last_name AS paciente, o.od_date AS fecha FROM \"Orders\" o JOIN \"Patients\" p ON p.pt_id = o.od_patient_id WHERE o.od_date BETWEEN :fecha_inicio AND :fecha_fin ORDER BY o.od_date DESC",
  "dr_html_template": "<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"UTF-8\"><style>body{font-family:Arial,sans-serif;font-size:12px}table{width:100%;border-collapse:collapse}th{background:#2c3e50;color:white;padding:6px}td{border-bottom:1px solid #ddd;padding:5px}</style></head><body><h2>Órdenes del período</h2><p>Desde: <b>{{ params.fecha_inicio }}</b> — Hasta: <b>{{ params.fecha_fin }}</b></p>{% if data %}<table><thead><tr><th># Orden</th><th>Paciente</th><th>Fecha</th></tr></thead><tbody>{% for row in data %}<tr><td>{{ row.orden }}</td><td>{{ row.paciente }}</td><td>{{ row.fecha }}</td></tr>{% endfor %}</tbody></table><p>Total: {{ data|length }}</p>{% else %}<p>Sin resultados.</p>{% endif %}</body></html>",
  "dr_active": true,
  "parameters": [
    {
      "rp_name": "fecha_inicio",
      "rp_label": "Fecha de inicio",
      "rp_type": "date",
      "rp_required": true,
      "rp_default_value": "2026-01-01",
      "rp_source_query": null,
      "rp_order_index": 0
    },
    {
      "rp_name": "fecha_fin",
      "rp_label": "Fecha de fin",
      "rp_type": "date",
      "rp_required": true,
      "rp_default_value": "2026-12-31",
      "rp_source_query": null,
      "rp_order_index": 1
    }
  ]
}
```

**Respuesta exitosa (201 Created):**

```json
{
  "dr_id": 1,
  "dr_name": "Órdenes por Fecha",
  "dr_description": "Lista todas las órdenes de laboratorio en un rango de fechas",
  "dr_active": true
}
```

Guarda el `dr_id` devuelto — lo necesitas para las siguientes llamadas.

### Paso 3 — Verificar el reporte creado

```
GET http://localhost:8000/api/reports/dynamic/1
```

La respuesta incluye todos los parámetros con sus opciones resueltas (para tipos `select`/`multiselect`).

### Paso 4 — Ejecutar el reporte con datos de prueba

```
POST http://localhost:8000/api/reports/dynamic/1/run
```

```json
{
  "params": {
    "fecha_inicio": "2026-05-01",
    "fecha_fin": "2026-05-13"
  }
}
```

Si la respuesta tiene `"total_rows": 0`, el SQL es correcto pero no hay datos en ese rango. No es un error.

---

## 8. Modificar un reporte existente

**Endpoint:** `PUT http://localhost:8000/api/reports/dynamic/{id}`  
**Permiso requerido:** `Reports:DynamicUpdate`

Puedes enviar solo los campos que quieres cambiar. Si envías `parameters`, **reemplaza la lista completa**.

**Ejemplo — corregir solo el SQL:**

```json
{
  "dr_sql_query": "SELECT o.od_id AS orden, p.pt_firts_name || ' ' || p.pt_last_name AS paciente, o.od_date AS fecha FROM \"Orders\" o JOIN \"Patients\" p ON p.pt_id = o.od_patient_id WHERE o.od_date BETWEEN :fecha_inicio AND :fecha_fin ORDER BY o.od_date DESC"
}
```

**Ejemplo — agregar un parámetro adicional:**

```json
{
  "parameters": [
    {
      "rp_name": "fecha_inicio",
      "rp_label": "Fecha de inicio",
      "rp_type": "date",
      "rp_required": true,
      "rp_default_value": "2026-01-01",
      "rp_source_query": null,
      "rp_order_index": 0
    },
    {
      "rp_name": "fecha_fin",
      "rp_label": "Fecha de fin",
      "rp_type": "date",
      "rp_required": true,
      "rp_default_value": "2026-12-31",
      "rp_source_query": null,
      "rp_order_index": 1
    },
    {
      "rp_name": "laboratorio_id",
      "rp_label": "Laboratorio",
      "rp_type": "select",
      "rp_required": false,
      "rp_default_value": null,
      "rp_source_query": "SELECT lb_id AS value, lb_name AS label FROM \"Laboratories\" WHERE lb_active = true ORDER BY lb_name",
      "rp_order_index": 2
    }
  ]
}
```

> **Importante:** Al enviar `parameters` en un `PUT`, la lista completa de parámetros anteriores es **reemplazada**. Si omites un parámetro que existía, se elimina.

---

## 9. Ejecutar un reporte

**Endpoint:** `POST http://localhost:8000/api/reports/dynamic/{id}/run`  
**Permiso requerido:** `Reports:DynamicRun`

```json
{
  "params": {
    "rp_name_del_parametro_1": "valor1",
    "rp_name_del_parametro_2": "valor2"
  }
}
```

- Las **claves** del objeto `params` deben ser exactamente los `rp_name` definidos en los parámetros.
- Los parámetros con `rp_required: true` son obligatorios; si faltan, la API responde con `422`.

**Respuesta (200 OK):**

```json
{
  "report_id": 1,
  "report_name": "Órdenes por Fecha",
  "total_rows": 47,
  "html": "<!DOCTYPE html>...HTML renderizado completo..."
}
```

El campo `html` contiene el HTML listo para insertar en el frontend con `innerHTML` (usando `DomSanitizer` en Angular).

---

## 10. Exportar a PDF

**Endpoint:** `POST http://localhost:8000/api/reports/dynamic/{id}/export-pdf`  
**Permiso requerido:** `Reports:DynamicExportPdf`

El cuerpo es idéntico al de `/run`:

```json
{
  "params": {
    "fecha_inicio": "2026-05-01",
    "fecha_fin": "2026-05-13"
  }
}
```

**Respuesta (200 OK):**

```json
{
  "filename": "reporte_1_Órdenes_por_Fecha.pdf",
  "base64_pdf": "JVBERi0xLjQ...",
  "report_name": "Órdenes por Fecha",
  "total_rows": 47
}
```

**En Angular, para abrir/descargar el PDF:**

```typescript
const bytes = atob(response.base64_pdf);
const arr   = new Uint8Array(bytes.length).map((_, i) => bytes.charCodeAt(i));
const blob  = new Blob([arr], { type: 'application/pdf' });
const url   = URL.createObjectURL(blob);
window.open(url);  // abre en nueva pestaña
// o para descarga directa:
const a  = document.createElement('a');
a.href   = url;
a.download = response.filename;
a.click();
```

---

## 11. Errores comunes y cómo corregirlos

| Error | Causa | Solución |
|---|---|---|
| `"Solo se permiten consultas SELECT"` | El SQL contiene `INSERT`, `UPDATE`, etc. | Revisa el SQL; elimina cualquier palabra prohibida |
| `"El parámetro requerido X no fue enviado"` | Falta un parámetro marcado como `rp_required: true` en el body `params` | Incluye el parámetro con su `rp_name` exacto |
| `"column pt_name does not exist"` | Se usó un nombre de columna que no existe en la BD | Usar `pt_firts_name` (con el typo) y `pt_last_name` |
| `"invalid input for query argument"` | Se envió una fecha como string pero el SQL espera un tipo PostgreSQL | El sistema convierte automáticamente si `rp_type` es `date`. Verifica que `rp_type` sea correcto en el parámetro |
| `"Error al renderizar la plantilla"` | Hay un error de sintaxis Jinja2 en `dr_html_template` | Revisar la plantilla: llaves mal cerradas `{{ }}` o bloques `{% %}` incorrectos |
| `"Reporte dinámico con id=X no encontrado"` | El ID no existe o el reporte está inactivo (`dr_active: false`) | Verificar el ID con `GET /api/reports/dynamic` |
| `"La consulta SQL debe iniciar con SELECT"` | La consulta comienza con espacio o comentario antes del SELECT | Eliminar espacios o comentarios al inicio del SQL |

### Regla de oro para fechas

Siempre que el SQL filtre por una columna de tipo `DATE` o `TIMESTAMP`, el parámetro **debe tener `rp_type: "date"` o `rp_type: "datetime"`** respectivamente. De lo contrario PostgreSQL recibe un string y falla.

---

## 12. Permisos RBAC requeridos

| Operación | Permiso necesario |
|---|---|
| Listar reportes | `Reports:DynamicList` |
| Ver detalle de un reporte | `Reports:DynamicRead` |
| Crear reporte | `Reports:DynamicCreate` |
| Editar reporte | `Reports:DynamicUpdate` |
| Eliminar reporte | `Reports:DynamicDelete` |
| Ejecutar reporte | `Reports:DynamicRun` |
| Exportar a PDF | `Reports:DynamicExportPdf` |

Estos permisos se asignan a roles desde el módulo de administración de roles. Si un usuario recibe `403 Forbidden`, verificar que su rol tenga el permiso correspondiente.

---

## Resumen rápido — Checklist para crear un reporte

- [ ] 1. Diseñar y probar el SQL en DBeaver/pgAdmin con datos reales
- [ ] 2. Verificar que todos los nombres de columna existen (cuidado con `pt_firts_name`)
- [ ] 3. Usar alias claros (`AS nombre_columna`) en todas las columnas del SELECT
- [ ] 4. Definir un `rp_name` por cada `:parametro` usado en el WHERE
- [ ] 5. Asignar el `rp_type` correcto a cada parámetro (especialmente `date` para fechas)
- [ ] 6. Marcar `rp_required: true` en los parámetros sin los cuales el SQL no tiene sentido
- [ ] 7. Escribir la plantilla HTML usando `{% for row in data %}` y `row.alias_columna`
- [ ] 8. Llamar a `POST /api/reports/dynamic` con el JSON completo
- [ ] 9. Probar con `POST /api/reports/dynamic/{id}/run` con valores de parámetros reales
- [ ] 10. Si el HTML se ve bien, probar `POST /api/reports/dynamic/{id}/export-pdf`
