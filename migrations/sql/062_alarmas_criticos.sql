-- =============================================================================
-- 062 - Módulo de Alarmas y Críticos
-- =============================================================================
-- Crea:
--   1. "CriticalRules"  → valores críticos / de pánico / delta check por prueba
--                         (independientes de los rangos de referencia: el rango
--                         "CRITICO" de RangesReferences se sigue usando solo para
--                         marcar resultados alterados en el reporte).
--   2. "Alarms"         → una alarma por resultado que cruzó un límite.
--   3. "AlarmEvents"    → trazabilidad de cada alarma (detección, notificación
--                         al médico con verificación de lectura, acuse, escalamiento,
--                         cierre, notas).
--   4. Permisos: Alarms:List, Alarms:Manage, Alarms:Rules.
--   5. Reglas SUGERIDAS (INACTIVAS) para las pruebas más comunes. No generan
--      alarmas hasta que el director del laboratorio las revise y las active.
--
-- Seguro de correr varias veces. No modifica ni borra datos existentes.
-- =============================================================================

BEGIN;

-- 1. Reglas de valores críticos ----------------------------------------------
CREATE TABLE IF NOT EXISTS "CriticalRules" (
    cr_id               SERIAL PRIMARY KEY,
    cr_test_id          INTEGER      NOT NULL REFERENCES "TestsLab"(id),
    cr_gender           VARCHAR(10)  NOT NULL DEFAULT 'AMBOS',
    cr_age_type         VARCHAR(10)  NOT NULL DEFAULT 'AÑOS',
    cr_min_age          INTEGER      NULL,
    cr_max_age          INTEGER      NULL,
    cr_panic_low        NUMERIC      NULL,
    cr_critical_low     NUMERIC      NULL,
    cr_critical_high    NUMERIC      NULL,
    cr_panic_high       NUMERIC      NULL,
    cr_delta_pct        NUMERIC      NULL,
    cr_delta_days       INTEGER      NOT NULL DEFAULT 30,
    cr_notify_minutes   INTEGER      NOT NULL DEFAULT 30,
    cr_block_validation BOOLEAN      NOT NULL DEFAULT FALSE,
    cr_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    cr_note             TEXT         NULL,
    cr_created_by       INTEGER      NULL REFERENCES "AppUsers"(usr_id),
    cr_updated_by       INTEGER      NULL REFERENCES "AppUsers"(usr_id),
    cr_created_at       TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'America/Bogota'),
    cr_updated_at       TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'America/Bogota'),
    CONSTRAINT ck_cr_gender   CHECK (cr_gender IN ('AMBOS', 'MASCULINO', 'FEMENINO')),
    CONSTRAINT ck_cr_age_type CHECK (cr_age_type IN ('DIAS', 'MESES', 'AÑOS')),
    CONSTRAINT ck_cr_ages     CHECK (cr_min_age IS NULL OR cr_max_age IS NULL OR cr_min_age <= cr_max_age),
    CONSTRAINT ck_cr_has_limit CHECK (COALESCE(cr_panic_low, cr_critical_low, cr_critical_high, cr_panic_high, cr_delta_pct) IS NOT NULL),
    CONSTRAINT ck_cr_low      CHECK (cr_panic_low IS NULL OR cr_critical_low IS NULL OR cr_panic_low <= cr_critical_low),
    CONSTRAINT ck_cr_high     CHECK (cr_critical_high IS NULL OR cr_panic_high IS NULL OR cr_critical_high <= cr_panic_high),
    CONSTRAINT ck_cr_minutes  CHECK (cr_notify_minutes BETWEEN 1 AND 1440),
    CONSTRAINT ck_cr_delta    CHECK (cr_delta_pct IS NULL OR cr_delta_pct > 0)
);
CREATE INDEX IF NOT EXISTS ix_criticalrules_test ON "CriticalRules"(cr_test_id);

COMMENT ON TABLE "CriticalRules" IS 'Valores críticos, de pánico y delta por prueba. Resultado menor que pánico bajo o mayor que pánico alto = PÁNICO, menor que crítico bajo o mayor que crítico alto = CRÍTICO.';

-- 2. Alarmas ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "Alarms" (
    al_id                SERIAL PRIMARY KEY,
    al_laboratory_id     INTEGER      NOT NULL REFERENCES "Laboratories"(l_id),
    al_order_id          INTEGER      NOT NULL REFERENCES "Orders"(o_id),
    al_test_id           INTEGER      NOT NULL REFERENCES "TestsLab"(id),
    al_patient_id        INTEGER      NULL REFERENCES "Patients"(pt_id),
    al_rule_id           INTEGER      NULL REFERENCES "CriticalRules"(cr_id),
    al_level             VARCHAR(10)  NOT NULL,
    al_direction         VARCHAR(5)   NULL,
    al_value             NUMERIC      NOT NULL,
    al_last_value        NUMERIC      NULL,
    al_limit             NUMERIC      NULL,
    al_limits            JSONB        NULL,
    al_previous_value    NUMERIC      NULL,
    al_previous_date     TIMESTAMP    NULL,
    al_previous_order    VARCHAR(255) NULL,
    al_state             VARCHAR(12)  NOT NULL DEFAULT 'NUEVA',
    al_notify_minutes    INTEGER      NOT NULL DEFAULT 30,
    al_block_validation  BOOLEAN      NOT NULL DEFAULT FALSE,
    al_detected_at       TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'America/Bogota'),
    al_notified_at       TIMESTAMP    NULL,
    al_notified_by       INTEGER      NULL REFERENCES "AppUsers"(usr_id),
    al_closed_at         TIMESTAMP    NULL,
    al_closed_by         INTEGER      NULL REFERENCES "AppUsers"(usr_id),
    al_updated_at        TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'America/Bogota'),
    CONSTRAINT ck_al_level     CHECK (al_level IN ('PANICO', 'CRITICO', 'DELTA')),
    CONSTRAINT ck_al_state     CHECK (al_state IN ('NUEVA', 'NOTIFICADA', 'ACUSADA', 'ESCALADA', 'CERRADA')),
    CONSTRAINT ck_al_direction CHECK (al_direction IS NULL OR al_direction IN ('ALTO', 'BAJO'))
);
-- Una sola alarma abierta por resultado (evita duplicados entre workers)
CREATE UNIQUE INDEX IF NOT EXISTS ux_alarms_open_lab ON "Alarms"(al_laboratory_id) WHERE al_state <> 'CERRADA';
CREATE INDEX IF NOT EXISTS ix_alarms_lab      ON "Alarms"(al_laboratory_id);
CREATE INDEX IF NOT EXISTS ix_alarms_state    ON "Alarms"(al_state);
CREATE INDEX IF NOT EXISTS ix_alarms_detected ON "Alarms"(al_detected_at);
CREATE INDEX IF NOT EXISTS ix_alarms_order    ON "Alarms"(al_order_id);

-- 3. Trazabilidad -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "AlarmEvents" (
    ae_id         SERIAL PRIMARY KEY,
    ae_alarm_id   INTEGER      NOT NULL REFERENCES "Alarms"(al_id),
    ae_type       VARCHAR(20)  NOT NULL,
    ae_user_id    INTEGER      NULL REFERENCES "AppUsers"(usr_id),
    ae_user_name  VARCHAR(255) NULL,
    ae_channel    VARCHAR(20)  NULL,
    ae_contact    VARCHAR(255) NULL,
    ae_read_back  BOOLEAN      NULL,
    ae_detail     TEXT         NULL,
    ae_created_at TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'America/Bogota')
);
CREATE INDEX IF NOT EXISTS ix_alarmevents_alarm ON "AlarmEvents"(ae_alarm_id);

-- 4. Permisos -------------------------------------------------------------------
INSERT INTO "Permissions" (p_name, p_description, p_module)
SELECT v.p_name, v.p_description, 'Alarms'
FROM (VALUES
    ('Alarms:List',   'Ver la bandeja de alarmas y valores críticos (y el contador del menú)'),
    ('Alarms:Manage', 'Registrar notificación al médico, acuse, escalar, notas y cerrar alarmas'),
    ('Alarms:Rules',  'Configurar los valores críticos / de pánico por prueba')
) AS v(p_name, p_description)
WHERE NOT EXISTS (SELECT 1 FROM "Permissions" p WHERE p.p_name = v.p_name);

-- Asignación inicial:
--  - Alarms:List y Alarms:Manage → roles que validan resultados (bacteriólogos)
--  - Alarms:Rules                → roles que administran pruebas (StudiesLab:Update)
INSERT INTO "RolPermissions" (rp_rol_id, rp_permission_id, rp_active)
SELECT DISTINCT rp.rp_rol_id, nuevo.p_id, TRUE
FROM "RolPermissions" rp
JOIN "Permissions" base  ON base.p_id = rp.rp_permission_id AND rp.rp_active
JOIN "Permissions" nuevo ON (base.p_name = 'Laboratories:Validate' AND nuevo.p_name IN ('Alarms:List', 'Alarms:Manage'))
                         OR (base.p_name = 'StudiesLab:Update'     AND nuevo.p_name IN ('Alarms:List', 'Alarms:Manage', 'Alarms:Rules'))
WHERE NOT EXISTS (SELECT 1 FROM "RolPermissions" x
                  WHERE x.rp_rol_id = rp.rp_rol_id AND x.rp_permission_id = nuevo.p_id);

-- 5. Reglas sugeridas (INACTIVAS: revisar y activar desde la pantalla) ----------
-- Valores de referencia habituales en adultos; el laboratorio debe ajustarlos
-- a su política antes de activarlos.
INSERT INTO "CriticalRules" (cr_test_id, cr_panic_low, cr_critical_low, cr_critical_high, cr_panic_high,
                             cr_delta_pct, cr_notify_minutes, cr_block_validation, cr_active, cr_note)
SELECT t.id, v.panic_low, v.crit_low, v.crit_high, v.panic_high, v.delta, v.minutes, FALSE, FALSE,
       'Sugerida (adultos). Revisar y ajustar antes de activar.'
FROM (VALUES
    ('POT',  2.5,   3.0,   6.0,   6.5,   NULL::numeric, 15),
    ('SOD',  120,   125,   155,   160,   NULL, 15),
    ('GLU',  40,    50,    400,   500,   NULL, 15),
    ('CAL',  6.0,   7.0,   12.0,  13.0,  NULL, 15),
    ('CALION', 0.8, 0.9,   1.5,   1.6,   NULL, 15),
    ('MAG',  1.0,   NULL,  NULL,  4.7,   NULL, 30),
    ('HB',   7.0,   8.0,   NULL,  20.0,  30,   15),
    ('HTO',  20,    NULL,  NULL,  60,    NULL, 30),
    ('PLT',  20,    50,    NULL,  1000,  50,   15),
    ('WBC',  2.0,   NULL,  NULL,  30.0,  NULL, 15),
    ('INR',  NULL,  NULL,  4.0,   5.0,   NULL, 15),
    ('PTT',  NULL,  NULL,  NULL,  100,   NULL, 15),
    ('CRE',  NULL,  NULL,  5.0,   7.4,   100,  30),
    ('BILTOT', NULL, NULL, 15,    20,    NULL, 30)
) AS v(code, panic_low, crit_low, crit_high, panic_high, delta, minutes)
JOIN LATERAL (
    SELECT id FROM "TestsLab" WHERE code = v.code AND active ORDER BY id LIMIT 1
) t ON TRUE
WHERE NOT EXISTS (SELECT 1 FROM "CriticalRules" r WHERE r.cr_test_id = t.id);

COMMIT;

-- Verificación
SELECT 'CriticalRules' AS tabla, count(*) AS filas FROM "CriticalRules"
UNION ALL SELECT 'Alarms', count(*) FROM "Alarms"
UNION ALL SELECT 'AlarmEvents', count(*) FROM "AlarmEvents";

SELECT p.p_name, string_agg(r.r_name, ', ' ORDER BY r.r_name) AS roles
FROM "Permissions" p
LEFT JOIN "RolPermissions" rp ON rp.rp_permission_id = p.p_id AND rp.rp_active
LEFT JOIN "Rols" r ON r.r_id = rp.rp_rol_id
WHERE p.p_module = 'Alarms'
GROUP BY p.p_name;
