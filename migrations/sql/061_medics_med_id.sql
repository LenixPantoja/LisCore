-- =============================================================================
-- 061 - Médicos: llave primaria med_id y med_codigo como código (VARCHAR)
-- =============================================================================
-- La tabla "Medics" se creó con med_codigo como llave numérica automática.
-- med_codigo es en realidad otro identificador del médico (texto), así que:
--   1. Se agrega med_id (SERIAL) como llave primaria. Los médicos existentes
--      quedan con med_id = su med_codigo actual (no se cruza ninguno).
--   2. med_codigo pasa a VARCHAR(30), sin autonumérico, único. Se conservan los
--      códigos actuales como texto ('1', '2', ...).
--   3. Orders.o_medic_id pasa a apuntar a "Medics".med_id.
--
-- No borra médicos ni órdenes. Seguro de correr varias veces.
-- Correr ANTES de desplegar el backend nuevo.
-- =============================================================================

BEGIN;

-- 0. La llave foránea de las órdenes se vuelve a crear al final contra med_id
ALTER TABLE "Orders" DROP CONSTRAINT IF EXISTS fk_orders_o_medic_id;

-- 1. med_id como llave primaria -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'Medics' AND column_name = 'med_id') THEN
        ALTER TABLE "Medics" ADD COLUMN med_id INTEGER;

        -- Los médicos existentes conservan su número actual
        UPDATE "Medics" SET med_id = med_codigo::integer;

        -- Las órdenes que ya tuvieran médico (apuntaban a med_codigo) quedan igual,
        -- porque med_id = med_codigo para todos los médicos existentes.

        CREATE SEQUENCE IF NOT EXISTS "Medics_med_id_seq" OWNED BY "Medics".med_id;
        PERFORM setval('"Medics_med_id_seq"', COALESCE((SELECT max(med_id) FROM "Medics"), 0) + 1, false);
        ALTER TABLE "Medics" ALTER COLUMN med_id SET DEFAULT nextval('"Medics_med_id_seq"');
        ALTER TABLE "Medics" ALTER COLUMN med_id SET NOT NULL;
    END IF;
END $$;

DO $$
DECLARE
    pk_name text;
    pk_cols text;
BEGIN
    SELECT c.conname, pg_get_constraintdef(c.oid) INTO pk_name, pk_cols
    FROM pg_constraint c
    WHERE c.conrelid = '"Medics"'::regclass AND c.contype = 'p';

    IF pk_name IS NOT NULL AND pk_cols NOT ILIKE '%(med_id)%' THEN
        EXECUTE format('ALTER TABLE "Medics" DROP CONSTRAINT %I', pk_name);
    END IF;
    IF pk_name IS NULL OR pk_cols NOT ILIKE '%(med_id)%' THEN
        ALTER TABLE "Medics" ADD CONSTRAINT medics_pkey PRIMARY KEY (med_id);
    END IF;
END $$;

-- 2. med_codigo como código de texto --------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'Medics' AND column_name = 'med_codigo' AND data_type = 'integer') THEN
        ALTER TABLE "Medics" ALTER COLUMN med_codigo DROP DEFAULT;
        ALTER TABLE "Medics" ALTER COLUMN med_codigo TYPE VARCHAR(30) USING med_codigo::text;
    END IF;
END $$;

-- La secuencia del autonumérico anterior ya no se usa
DROP SEQUENCE IF EXISTS "Medicos_med_codigo_seq";
DROP SEQUENCE IF EXISTS "Medics_med_codigo_seq";

-- Código único (no se repite entre médicos)
CREATE UNIQUE INDEX IF NOT EXISTS ux_medics_med_codigo ON "Medics" (med_codigo);

-- 3. Órdenes → med_id ----------------------------------------------------------------
ALTER TABLE "Orders"
    ADD CONSTRAINT fk_orders_o_medic_id
    FOREIGN KEY (o_medic_id) REFERENCES "Medics"(med_id);

COMMIT;

-- Verificación ---------------------------------------------------------------------
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'Medics' AND column_name IN ('med_id', 'med_codigo');

SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname IN ('medics_pkey', 'fk_orders_o_medic_id')
   OR (conrelid = '"Medics"'::regclass AND contype = 'p');

SELECT med_id, med_codigo, med_name FROM "Medics" ORDER BY med_id LIMIT 5;
