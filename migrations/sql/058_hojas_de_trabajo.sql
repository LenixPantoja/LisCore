-- =============================================================================
-- 058 · Hojas de trabajo
-- =============================================================================
--
-- Crea el módulo de hojas de trabajo: una hoja agrupa estudios (en un orden)
-- para generar e imprimir el Plan de Trabajo de esos estudios.
--
--   WorkSheets        hoja: nombre, descripción, sede (NULL = todas), sector,
--                     columna libre al imprimir, activa
--   WorkSheetStudies  estudios de cada hoja y su orden de impresión
--
-- Permisos (se asignan a los roles que ya tienen el permiso equivalente):
--   WorkSheets:List   → roles con StudiesLab:List   (usar hojas en Planes de Trabajo)
--   WorkSheets:Manage → roles con StudiesLab:Update (crear/editar hojas y estudios)
--
-- Solo agrega tablas y permisos; no modifica datos existentes.
-- Se puede ejecutar varias veces. pgAdmin (F5) o psql.
-- =============================================================================

CREATE TABLE IF NOT EXISTS "WorkSheets" (
    ws_id                   SERIAL PRIMARY KEY,
    ws_name                 VARCHAR(150) NOT NULL,
    ws_description          TEXT,
    ws_headquarter_id       INTEGER REFERENCES "Headquarters"(id),
    ws_work_group_id        INTEGER REFERENCES "Work_groups"(wg_id),
    ws_include_free_column  BOOLEAN NOT NULL DEFAULT FALSE,
    ws_active               BOOLEAN NOT NULL DEFAULT TRUE,
    ws_created_at           TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'America/Bogota'),
    ws_updated_at           TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'America/Bogota')
);

CREATE TABLE IF NOT EXISTS "WorkSheetStudies" (
    wss_id            SERIAL PRIMARY KEY,
    wss_worksheet_id  INTEGER NOT NULL REFERENCES "WorkSheets"(ws_id) ON DELETE CASCADE,
    wss_study_id      INTEGER NOT NULL REFERENCES "StudiesLab"(id) ON DELETE CASCADE,
    wss_order         INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_worksheet_study UNIQUE (wss_worksheet_id, wss_study_id)
);

CREATE INDEX IF NOT EXISTS ix_worksheetstudies_worksheet ON "WorkSheetStudies" (wss_worksheet_id);
CREATE INDEX IF NOT EXISTS ix_worksheetstudies_study     ON "WorkSheetStudies" (wss_study_id);

-- Permisos
INSERT INTO "Permissions" (p_name, p_description, p_module)
SELECT v.p_name, v.p_description, 'WorkSheets'
FROM (VALUES
    ('WorkSheets:List',   'Ver hojas de trabajo y usarlas en Planes de Trabajo'),
    ('WorkSheets:Manage', 'Crear, editar y eliminar hojas de trabajo y sus estudios')
) AS v(p_name, p_description)
WHERE NOT EXISTS (SELECT 1 FROM "Permissions" p WHERE p.p_name = v.p_name);

-- Asignarlos a los roles que ya tienen el permiso equivalente de Estudios
INSERT INTO "RolPermissions" (rp_rol_id, rp_permission_id, rp_active)
SELECT DISTINCT rp.rp_rol_id, nuevo.p_id, TRUE
FROM "RolPermissions" rp
JOIN "Permissions" base  ON base.p_id = rp.rp_permission_id AND rp.rp_active
JOIN "Permissions" nuevo ON (base.p_name = 'StudiesLab:List'   AND nuevo.p_name = 'WorkSheets:List')
                         OR (base.p_name = 'StudiesLab:Update' AND nuevo.p_name = 'WorkSheets:Manage')
WHERE NOT EXISTS (SELECT 1 FROM "RolPermissions" x
                  WHERE x.rp_rol_id = rp.rp_rol_id AND x.rp_permission_id = nuevo.p_id);

-- Verificación: roles con cada permiso nuevo
SELECT p.p_name, r.r_name
FROM "RolPermissions" rp
JOIN "Permissions" p ON p.p_id = rp.rp_permission_id
JOIN "Rols" r        ON r.r_id = rp.rp_rol_id
WHERE p.p_module = 'WorkSheets'
ORDER BY p.p_name, r.r_name;
