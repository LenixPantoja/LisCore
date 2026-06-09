Arquitectura completa de tu módulo de reportes dinámico para el LIS

Voy a darte una guía REALISTA y ESCALABLE para que puedas construirlo paso a paso con:

FastAPI
PostgreSQL
Angular
Jinja2
QUÉ VAS A CONSTRUIR

Tu sistema hará esto:

1. Crear reportes desde BD
2. Crear filtros dinámicos
3. Ejecutar SQL dinámico
4. Renderizar HTML dinámico
5. Exportar PDF
6. Mostrar reportes en Angular
FASE 1 — ESTRUCTURA DE BASE DE DATOS
TABLA 1 — reports

Aquí vive el reporte.

CREATE TABLE reports (

    id SERIAL PRIMARY KEY,

    name VARCHAR(200) NOT NULL,

    description TEXT,

    sql_query TEXT NOT NULL,

    html_template TEXT NOT NULL,

    active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW()

);
¿QUÉ GUARDA?
Campo	Función
name	Nombre reporte
sql_query	SQL dinámico
html_template	HTML + CSS + Jinja2
EJEMPLO REAL
name
Pendientes por estudio
sql_query
SELECT
    o.id,
    p.full_name,
    s.name AS estudio,
    o.created_at
FROM orders o
JOIN patients p ON p.id = o.patient_id
JOIN studies s ON s.id = o.study_id
WHERE
    o.created_at BETWEEN :fecha_inicio AND :fecha_fin
    AND o.study_id = :id_estudio
html_template
<h1>Reporte Pendientes</h1>

<table>

<tr>
   <th>Paciente</th>
   <th>Estudio</th>
</tr>

{% for row in data %}

<tr>
   <td>{{ row.full_name }}</td>
   <td>{{ row.estudio }}</td>
</tr>

{% endfor %}

</table>
TABLA 2 — report_parameters

Aquí defines los filtros.

CREATE TABLE report_parameters (

    id SERIAL PRIMARY KEY,

    report_id INTEGER REFERENCES reports(id),

    name VARCHAR(100) NOT NULL,

    label VARCHAR(100) NOT NULL,

    type VARCHAR(50) NOT NULL,

    required BOOLEAN DEFAULT FALSE,

    default_value TEXT,

    source_query TEXT,

    order_index INTEGER DEFAULT 0

);
¿QUÉ GUARDA?
Campo	Función
name	nombre variable
label	texto visual
type	date/select/text
source_query	llena selects
EJEMPLO
name	type
fecha_inicio	date
fecha_fin	date
id_estudio	select
SELECT DINÁMICO
source_query
SELECT id,name
FROM studies
ORDER BY name
FASE 2 — CREAR API BACKEND
ENDPOINT 1
Listar reportes
GET /reports
RESPUESTA
[
  {
    "id": 1,
    "name": "Pendientes por estudio"
  }
]
ENDPOINT 2
Obtener reporte + parámetros
GET /reports/1
BACKEND HACE
1. Busca reporte
report = db.query(Report).get(id)
2. Busca parámetros
params = db.query(ReportParameter)\
    .filter_by(report_id=id)\
    .all()
3. Si encuentra select

Ejecuta:

source_query
EJEMPLO
SELECT id,name FROM studies
RESPUESTA FINAL
{
  "id": 1,
  "name": "Pendientes por estudio",
  "parameters": [
    {
      "name": "fecha_inicio",
      "type": "date"
    },
    {
      "name": "fecha_fin",
      "type": "date"
    },
    {
      "name": "id_estudio",
      "type": "select",
      "options": [
        {
          "value": 1,
          "label": "Hemograma"
        }
      ]
    }
  ]
}
FASE 3 — ANGULAR CREA FORMULARIO

Angular recibe JSON.

Y renderiza dinámicamente.

SI type=date

Crea:

<input type="date">
SI type=select

Crea:

<select>
RESULTADO VISUAL
--------------------------------

Fecha Inicio [      ]

Fecha Fin    [      ]

Estudio      [ ▼ ]

             [ Ejecutar ]

--------------------------------
FASE 4 — EJECUTAR REPORTE

Usuario llena:

Fecha inicio = 2026-05-01
Fecha fin = 2026-05-08
Estudio = Hemograma
ANGULAR ENVÍA
{
  "fecha_inicio": "2026-05-01",
  "fecha_fin": "2026-05-08",
  "id_estudio": 1
}
ENDPOINT
POST /reports/1/run
FASTAPI EJECUTA SQL
result = db.execute(
    text(report.sql_query),
    params
)
POSTGRES DEVUELVE
[
  {
    "full_name": "Juan Pérez",
    "estudio": "Hemograma"
  }
]
FASE 5 — RENDERIZAR HTML
CARGAR TEMPLATE
template = Template(
   report.html_template
)
RENDERIZAR
html = template.render(
   data=data,
   params=params
)
JINJA2 REEMPLAZA
{{ row.full_name }}

Por:

Juan Pérez
RESULTADO FINAL
<table>

<tr>
   <td>Juan Pérez</td>
</tr>

</table>
FASE 6 — ANGULAR MUESTRA HTML
<div [innerHTML]="html"></div>
FASE 7 — EXPORTAR PDF

Después puedes usar:

WeasyPrint
Playwright
FLUJO COMPLETO
Usuario abre reporte
        ↓
Angular pide metadata
        ↓
FastAPI manda parámetros
        ↓
Angular crea formulario
        ↓
Usuario llena filtros
        ↓
Angular manda valores
        ↓
FastAPI ejecuta SQL
        ↓
Postgres devuelve filas
        ↓
Jinja2 genera HTML
        ↓
Angular muestra reporte
TIPOS DE PARÁMETROS QUE DEBERÍAS SOPORTAR
Tipo	Uso
text	nombre
number	edad
date	fechas
datetime	fecha y hora
select	estudio
multiselect	varios estudios
checkbox	activos
textarea	observaciones
SEGURIDAD MUY IMPORTANTE
1. SOLO SELECT

Bloquea:

DELETE
UPDATE
DROP
INSERT
2. Usuario SQL SOLO LECTURA

Crea un usuario PostgreSQL:

report_user

Con:

GRANT SELECT
3. VALIDAR PARAMS

Nunca concatenes SQL.

❌

f"WHERE id = {id}"

✅

WHERE id = :id