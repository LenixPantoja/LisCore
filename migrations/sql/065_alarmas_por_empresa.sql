-- =============================================================================
-- 065 - Alarmas y Críticos: reglas exclusivas por empresa (cliente)
-- =============================================================================
-- Una regla de valor crítico puede aplicar solo a las órdenes de una empresa
-- (Orders.o_enterprise_id), p.ej. una clínica renal con límites propios de
-- creatinina o potasio. Sin empresa = aplica a todos (como hasta ahora).
-- Si hay varias reglas para la misma prueba, la de la empresa de la orden
-- tiene prioridad sobre las generales.
--
-- Requiere el 062. Seguro de correr varias veces. No borra datos.
-- =============================================================================

BEGIN;

ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_enterprise_id INTEGER NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_criticalrules_enterprise') THEN
        ALTER TABLE "CriticalRules"
            ADD CONSTRAINT fk_criticalrules_enterprise FOREIGN KEY (cr_enterprise_id) REFERENCES "Enterprises"(en_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_criticalrules_enterprise ON "CriticalRules"(cr_enterprise_id);

COMMIT;

-- Verificación
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'CriticalRules' AND column_name = 'cr_enterprise_id';
