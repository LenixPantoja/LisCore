# Prueba de carga del LIS

Simula **30 usuarios** usando el sistema al mismo tiempo y mide cuánto tarda cada operación y si falla alguna.

La prueba **solo lee datos**: no crea órdenes, no carga ni valida resultados. Lo único que escribe es la traza de "Inicio de sesión" de cada usuario simulado.

## Qué simula

Cada usuario espera entre 3 y 10 segundos entre acciones, como alguien leyendo la pantalla. Las acciones se reparten así (más peso = ocurre más seguido):

| Acción | Endpoint | Peso |
|---|---|---|
| Ver lista de órdenes | `GET /orders/` | 5 |
| Abrir una orden (analitos) | `GET /orders/by-number/{n}/details` | 5 |
| Buscar órdenes por documento | `GET /orders/?search=` | 2 |
| Buscar paciente (admisión) | `GET /patients/document/{doc}` | 2 |
| Buscar estudios | `GET /studies-lab/?search=` | 2 |
| Ver trazabilidad | `GET /traces/order/{id}` | 1 |
| **Plan de Trabajo**: filtro + detalle de 30 órdenes, 6 en paralelo | `POST /orders/filter` + 30 × `details` | 1 |
| PDF de resultados (opcional, `LOAD_PDF=1`) | `POST /v2/reports/laboratory-results` | 1 |

## Antes de empezar

- **Dónde correrla:** idealmente contra un servidor de pruebas con una copia de los datos de producción y la **misma configuración** (4 workers, mismo PostgreSQL y MinIO). Contra producción solo fuera del horario de atención.
- **No uses tu PC de desarrollo como servidor**: ahí uvicorn corre con 1 proceso y los resultados no representan producción.
- **Usuarios:** crea uno o varios usuarios de prueba con permisos de laboratorio (órdenes, detalle, trazas, maestros, estudios y, si incluyes PDF, generar reportes).
- Corre Locust **desde otro equipo** distinto al servidor, para que la prueba no le quite CPU.

## Instalación (una vez)

En un entorno virtual aparte, para no mezclar Locust con las dependencias del backend:

```powershell
python -m venv .venv-load
.venv-load\Scripts\activate
pip install -r tests/load/requirements.txt
```

## Ejecutar

Desde la carpeta `Backend/Backend/LisCore`:

```powershell
$env:LOAD_USERS = "prueba1:Clave123,prueba2:Clave123,prueba3:Clave123"

# Con interfaz web (abre http://localhost:8089, pon 30 usuarios y velocidad 2)
locust -f tests/load/locustfile.py --host http://SERVIDOR:8000

# Sin interfaz: 30 usuarios, entrando 2 por segundo, durante 15 minutos, con reporte HTML
mkdir tests/load/resultados -Force
locust -f tests/load/locustfile.py --host http://SERVIDOR:8000 `
  --headless -u 30 -r 2 -t 15m `
  --csv tests/load/resultados/30usuarios --html tests/load/resultados/30usuarios.html
```

Opcionales: `$env:LOAD_PDF = "1"` (incluir PDF), `$env:LOAD_WORK_GROUP_ID = "5"` (fijar el área del Plan de Trabajo), `$env:LOAD_DAYS = "30"` (rango del Plan de Trabajo).

Recomendado: correrla primero con **10** usuarios, luego **30** y luego **50**, para ver en qué punto empieza a degradarse.

## Cómo leer el resultado

En el reporte HTML (o la pestaña *Statistics*), mira por cada fila:

- **Failures**: debe ser **0 %**. Cualquier error 500/502/504 o timeout es un problema.
- **95%ile (ms)**: el tiempo que no superan el 95 % de las peticiones. Valores de referencia:

| Operación | Bien | Revisar |
|---|---|---|
| Lista, búsquedas, paciente, trazas | < 1 s | > 2 s |
| Detalle de una orden | < 1,5 s | > 3 s |
| Plan de Trabajo (cada detalle) | < 3 s | > 6 s |
| PDF de resultados | < 5 s | > 10 s |

- Si los tiempos **suben continuamente** durante la prueba en vez de estabilizarse, el servidor no da abasto.

Mientras corre, conviene vigilar en el servidor: uso de CPU y memoria, y las conexiones abiertas de PostgreSQL (`SELECT count(*) FROM pg_stat_activity;`, límite configurado: 100).
