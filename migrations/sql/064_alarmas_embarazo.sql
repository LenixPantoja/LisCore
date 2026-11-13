-- =============================================================================
-- 064 - Alarmas y Críticos: reglas por embarazo y semanas de gestación
-- =============================================================================
-- Cada regla de valor crítico puede aplicar a:
--   TODAS          → cualquier paciente (como hasta ahora)
--   EMBARAZADA     → solo órdenes marcadas como embarazo (Orders.o_pregnated),
--                    opcionalmente en un rango de semanas (Orders.o_week_pregnated)
--   NO_EMBARAZADA  → solo pacientes no embarazadas
-- Si hay varias reglas para la misma prueba, se usa la más específica
-- (embarazo con semanas > embarazo > sexo > edad).
--
-- Requiere el 062. Seguro de correr varias veces. No borra datos.
-- =============================================================================

BEGIN;

ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_pregnancy VARCHAR(15) NOT NULL DEFAULT 'TODAS';
ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_min_week  INTEGER NULL;
ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_max_week  INTEGER NULL;

ALTER TABLE "CriticalRules" DROP CONSTRAINT IF EXISTS ck_cr_pregnancy;
ALTER TABLE "CriticalRules" ADD CONSTRAINT ck_cr_pregnancy
    CHECK (cr_pregnancy IN ('TODAS', 'EMBARAZADA', 'NO_EMBARAZADA'));

ALTER TABLE "CriticalRules" DROP CONSTRAINT IF EXISTS ck_cr_weeks;
ALTER TABLE "CriticalRules" ADD CONSTRAINT ck_cr_weeks
    CHECK ((cr_min_week IS NULL OR cr_min_week BETWEEN 0 AND 45)
       AND (cr_max_week IS NULL OR cr_max_week BETWEEN 0 AND 45)
       AND (cr_min_week IS NULL OR cr_max_week IS NULL OR cr_min_week <= cr_max_week)
       AND (cr_pregnancy = 'EMBARAZADA' OR (cr_min_week IS NULL AND cr_max_week IS NULL)));

COMMIT;

-- Verificación
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'CriticalRules' AND column_name IN ('cr_pregnancy', 'cr_min_week', 'cr_max_week');
