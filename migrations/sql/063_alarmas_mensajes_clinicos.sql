-- =============================================================================
-- 063 - Alarmas y Críticos: mensaje clínico por zona
-- =============================================================================
-- Agrega a cada regla de valor crítico un mensaje clínico por zona (posible
-- patología / riesgo), p.ej. potasio > 6.5 → "Arritmia / paro cardíaco",
-- plaquetas > 1000 → "Trombosis". La alarma guarda el mensaje que aplicó.
--
-- Requiere el 062. Seguro de correr varias veces. No borra datos.
-- =============================================================================

BEGIN;

ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_msg_panic_low     VARCHAR(255) NULL;
ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_msg_critical_low  VARCHAR(255) NULL;
ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_msg_critical_high VARCHAR(255) NULL;
ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_msg_panic_high    VARCHAR(255) NULL;
ALTER TABLE "CriticalRules" ADD COLUMN IF NOT EXISTS cr_msg_delta         VARCHAR(255) NULL;

ALTER TABLE "Alarms" ADD COLUMN IF NOT EXISTS al_message VARCHAR(255) NULL;

-- Mensajes sugeridos para las reglas sugeridas del 062 (solo si están vacíos)
UPDATE "CriticalRules" r
SET cr_msg_panic_low     = COALESCE(r.cr_msg_panic_low, v.p_low),
    cr_msg_critical_low  = COALESCE(r.cr_msg_critical_low, v.c_low),
    cr_msg_critical_high = COALESCE(r.cr_msg_critical_high, v.c_high),
    cr_msg_panic_high    = COALESCE(r.cr_msg_panic_high, v.p_high)
FROM (VALUES
    ('POT',    'Arritmia cardíaca / parálisis muscular', 'Hipopotasemia: debilidad, arritmia', 'Hiperpotasemia: riesgo de arritmia', 'Arritmia grave / paro cardíaco'),
    ('SOD',    'Convulsiones / edema cerebral', 'Hiponatremia: confusión', 'Hipernatremia: deshidratación', 'Alteración de conciencia / coma'),
    ('GLU',    'Hipoglicemia: convulsiones y coma', 'Hipoglicemia', 'Hiperglicemia descompensada', 'Cetoacidosis / estado hiperosmolar, coma'),
    ('CAL',    'Tetania / convulsiones / arritmia', 'Hipocalcemia', 'Hipercalcemia', 'Arritmia / coma'),
    ('CALION', 'Tetania / convulsiones / arritmia', 'Hipocalcemia', 'Hipercalcemia', 'Arritmia / coma'),
    ('MAG',    'Arritmia / convulsiones', NULL, NULL, 'Depresión respiratoria / paro cardíaco'),
    ('HB',     'Anemia severa: hipoxia / falla cardíaca', 'Anemia moderada a severa', NULL, 'Policitemia: riesgo de trombosis'),
    ('HTO',    'Anemia severa: hipoxia', NULL, NULL, 'Hiperviscosidad: riesgo de trombosis'),
    ('PLT',    'Riesgo de hemorragia espontánea', 'Trombocitopenia: riesgo de sangrado', NULL, 'Trombosis'),
    ('WBC',    'Neutropenia: riesgo de infección grave', NULL, NULL, 'Leucemia / sepsis'),
    ('INR',    NULL, NULL, 'Anticoagulación excesiva', 'Riesgo de hemorragia grave'),
    ('PTT',    NULL, NULL, NULL, 'Riesgo de hemorragia grave'),
    ('CRE',    NULL, NULL, 'Falla renal', 'Falla renal aguda'),
    ('BILTOT', NULL, NULL, 'Hiperbilirrubinemia', 'Falla hepática / kernícterus en neonatos')
) AS v(code, p_low, c_low, c_high, p_high)
JOIN "TestsLab" t ON t.code = v.code
WHERE r.cr_test_id = t.id
  AND r.cr_note LIKE 'Sugerida%';

COMMIT;

-- Verificación
SELECT t.code, r.cr_msg_panic_low, r.cr_msg_panic_high
FROM "CriticalRules" r JOIN "TestsLab" t ON t.id = r.cr_test_id
ORDER BY t.code;
