# Scripts SQL para bases de clientes

Scripts para aplicar a mano en la base PostgreSQL de cada cliente. Se usan porque en las bases de producción las migraciones se aplicaron manualmente (no existe la tabla `alembic_version`), y algunos índices quedaron sin crear.

| Script | Qué hace | ¿Toca datos? |
|---|---|---|
| `054_indices_faltantes.sql` | Crea 12 índices de rendimiento e integridad | No, solo agrega índices |

## 054 · Índices faltantes

### Por qué

- **Rendimiento:** buscar una orden por número (Laboratorio, Plan de Trabajo, Resultados), la trazabilidad de una orden, las órdenes de un paciente y los filtros por sede o área hacían recorrer la tabla completa. Con pocas órdenes no se nota; con decenas de miles, esas pantallas se vuelven lentas.
- **Integridad:** `ux_inboundorders_io_number_request` impide que una misma solicitud del HIS (Centralink) se registre dos veces si el HIS la reenvía casi al mismo tiempo.

### Antes de ejecutar

1. **Haga un respaldo** de la base del cliente (`pg_dump`), como con cualquier cambio en producción.
2. Puede correrlo **con el sistema en uso**: los índices se crean con `CONCURRENTLY`, que no bloquea las tablas. Igual es preferible hacerlo en horario de poco movimiento.
3. **No lo ejecute dentro de una transacción** (`BEGIN … COMMIT`): `CREATE INDEX CONCURRENTLY` no lo permite.

### Opción A — psql (recomendada)

Ejecuta el archivo completo, sentencia por sentencia, y se detiene en el primer error:

```powershell
psql "host=IP_DEL_SERVIDOR port=5432 dbname=NOMBRE_BD user=postgres" -v ON_ERROR_STOP=1 -f migrations/sql/054_indices_faltantes.sql
```

(Pide la contraseña. En Linux es el mismo comando.)

### Opción B — pgAdmin

1. Abra el *Query Tool* sobre la base del cliente.
2. Ejecute **primero solo el bloque 0** (verificación previa): selecciónelo y presione F5. Debe devolver **0 filas**.
3. Ejecute el resto del archivo. Si pgAdmin muestra *"CREATE INDEX CONCURRENTLY cannot run inside a transaction block"*, ejecute las sentencias `CREATE INDEX` **una por una** (seleccionando cada línea y F5), o use la opción A.

### Si la verificación previa devuelve filas

Hay solicitudes del HIS duplicadas y el índice único fallará. Revíselas antes de seguir:

```sql
SELECT io_id, io_number_request, io_created_at
FROM "InboundOrders"
WHERE io_number_request IN (
  SELECT io_number_request FROM "InboundOrders"
  WHERE io_number_request IS NOT NULL
  GROUP BY 1 HAVING count(*) > 1)
ORDER BY io_number_request, io_id;
```

Decida con el cliente cuál registro conservar. Puede ejecutar el resto del script sin el índice único (bloque 2) y crearlo después de depurar.

### Cómo saber que quedó bien

El último bloque del script lista los 12 índices. Todos deben aparecer con `valido = true`.

Si alguno aparece con `valido = false` (un `CONCURRENTLY` interrumpido deja el índice a medias), bórrelo y vuelva a correr el script:

```sql
DROP INDEX CONCURRENTLY IF EXISTS "nombre_del_indice";
```

### Deshacer (normalmente no es necesario)

```sql
DROP INDEX CONCURRENTLY IF EXISTS "ix_orders_o_number";
-- … uno por cada índice de la lista
```

## Configuración recomendada de PostgreSQL (opcional)

En `postgresql.conf` del servidor de cada cliente (requiere reiniciar PostgreSQL):

| Parámetro | Valor sugerido | Para qué |
|---|---|---|
| `shared_buffers` | ~25 % de la RAM (ej. `2GB` con 8 GB) | Caché de datos en memoria; por defecto es 128 MB |
| `effective_cache_size` | ~70 % de la RAM | Ayuda al planificador a elegir índices |
| `idle_in_transaction_session_timeout` | `5min` | Libera conexiones que quedaron trabadas en una transacción |
| `log_min_duration_statement` | `1000` | Registra en el log las consultas de más de 1 segundo |
| `max_connections` | `100` o más | El backend usa hasta 80 (4 workers × 20); súbalo si otros servicios usan la misma base |
