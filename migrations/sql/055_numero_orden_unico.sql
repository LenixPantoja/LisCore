-- =============================================================================
-- 055 · Corregir números de orden repetidos y volverlos únicos
-- =============================================================================
--
-- IMPORTANTE: ejecutar DESPUÉS de desplegar el backend que incluye
-- utils/Consecutives/consecutive_lock.py. El backend anterior toma el número de
-- la última orden + 1 y volvería a repetir los números asignados aquí.
--
-- Qué hace:
--   1. En cada número repetido conserva la orden más antigua y le asigna a las
--      demás el siguiente número libre de ese mismo día. También corrige sus
--      códigos de barras de muestra (SamplesOrder) y deja el cambio en la
--      trazabilidad de la orden (AppTrace).
--   2. Crea el índice único para que la base nunca acepte un número repetido.
--
-- Después de ejecutarlo: REIMPRIMA las etiquetas de las muestras de las órdenes
-- renumeradas (el bloque 1 las lista con su número nuevo).
--
-- Cómo ejecutarlo: pgAdmin (Query Tool, todo el archivo con F5) o
--   psql "host=IP port=5432 dbname=BD user=postgres" -v ON_ERROR_STOP=1 -f migrations/sql/055_numero_orden_unico.sql
-- En pgAdmin todo corre en una sola transacción: si algo falla, no cambia nada.
-- =============================================================================


-- 0. Números de orden repetidos (antes de corregir)
SELECT o_number, count(*) AS veces, array_agg(o_id ORDER BY o_id) AS ordenes
FROM "Orders"
GROUP BY o_number HAVING count(*) > 1;


-- 1. Renumerar las órdenes repetidas (todo o nada: si algo falla no cambia nada)
DO $$
DECLARE
    dup        record;
    prefix     text;
    last_num   text;
    new_seq    int;
    new_number text;
BEGIN
    FOR dup IN
        SELECT o.o_id, o.o_number
        FROM "Orders" o
        WHERE EXISTS (SELECT 1 FROM "Orders" o2
                      WHERE o2.o_number = o.o_number AND o2.o_id < o.o_id)
        ORDER BY o.o_id
    LOOP
        IF dup.o_number !~ '^[0-9]{10}$' THEN
            RAISE NOTICE 'Orden % con número % fuera del formato DDMMAACCCC: se omite, corríjala a mano',
                dup.o_id, dup.o_number;
            CONTINUE;
        END IF;

        prefix := left(dup.o_number, 6);
        -- Mismo bloqueo que usa el backend: nadie toma un número del día mientras tanto
        PERFORM pg_advisory_xact_lock(hashtext('order_number:' || prefix));

        SELECT max(o_number) INTO last_num
        FROM "Orders"
        WHERE o_number LIKE prefix || '%' AND length(o_number) = 10;

        new_seq := right(last_num, 4)::int + 1;
        IF new_seq > 9999 THEN
            RAISE EXCEPTION 'No quedan números libres para el día % (orden %)', prefix, dup.o_id;
        END IF;
        new_number := prefix || lpad(new_seq::text, 4, '0');

        UPDATE "Orders"
        SET o_number = new_number,
            o_updated_at = now() AT TIME ZONE 'America/Bogota'
        WHERE o_id = dup.o_id;

        -- El código de barras de la muestra es el número de orden + sufijo
        UPDATE "SamplesOrder"
        SET so_barcode = new_number || substr(so_barcode, 11)
        WHERE so_order_id = dup.o_id AND left(so_barcode, 10) = dup.o_number;

        INSERT INTO "AppTrace" (usr_id, order_id, operation_type, operation_description, notes, created_at)
        VALUES (NULL, dup.o_id, 7,
                'Renumeración de orden ' || dup.o_number || ' a ' || new_number,
                'El número estaba repetido con otra orden creada al mismo tiempo. Reimprimir etiquetas de las muestras.',
                now() AT TIME ZONE 'America/Bogota');

        RAISE NOTICE 'Orden %: % -> %', dup.o_id, dup.o_number, new_number;
    END LOOP;
END $$;


-- 2. Número de orden único (sin CONCURRENTLY para poder correrlo en pgAdmin;
--    con pocas miles de órdenes bloquea la tabla solo milisegundos)
CREATE UNIQUE INDEX IF NOT EXISTS ux_orders_o_number
    ON "Orders" (o_number);


-- 3. Verificación final
--    a) No debe haber números repetidos
SELECT o_number, count(*) FROM "Orders" GROUP BY o_number HAVING count(*) > 1;
--    b) Ningún código de barras de muestra compartido entre órdenes distintas
SELECT so_barcode, array_agg(DISTINCT so_order_id) AS ordenes
FROM "SamplesOrder" GROUP BY so_barcode HAVING count(DISTINCT so_order_id) > 1;
--    c) El índice debe aparecer con valido = true
SELECT c.relname AS indice, i.indisvalid AS valido
FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relname = 'ux_orders_o_number';
--    d) Órdenes renumeradas (reimprimir sus etiquetas)
SELECT t.order_id, o.o_number AS numero_nuevo, t.operation_description, t.created_at
FROM "AppTrace" t JOIN "Orders" o ON o.o_id = t.order_id
WHERE t.operation_description LIKE 'Renumeración de orden %'
ORDER BY t.created_at DESC;
