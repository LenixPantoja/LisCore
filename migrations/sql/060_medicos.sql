-- =============================================================================
-- 060 - Médicos
-- =============================================================================
-- 1. Tabla "Medics" (maestro de médicos remitentes).
-- 2. Orders.o_medic_id: médico de la orden (opcional en la base; el front lo
--    exige al crear la orden). Las órdenes existentes quedan con NULL.
-- 3. Permisos separados por acción: Medics:List, Medics:GetOne, Medics:Create,
--    Medics:Update, Medics:Delete.
--
-- Seguro de correr varias veces. No modifica ni borra datos existentes.
-- IMPORTANTE: correr ANTES de desplegar el backend nuevo (el backend lee
-- Orders.o_medic_id).
-- =============================================================================

BEGIN;

-- 1. Tabla de médicos -----------------------------------------------------------
-- Si ya se había creado con el nombre anterior "Medicos", se renombra (conserva datos,
-- índices y la llave foránea de Orders).
DO $$
BEGIN
    IF to_regclass('public."Medicos"') IS NOT NULL AND to_regclass('public."Medics"') IS NULL THEN
        ALTER TABLE "Medicos" RENAME TO "Medics";
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS "Medics" (
    med_codigo                   SERIAL PRIMARY KEY,
    med_name                     VARCHAR(200) NOT NULL,
    med_document_number          VARCHAR(30),
    med_specialty                VARCHAR(150),
    med_card_professional_number VARCHAR(50),
    med_phone                    VARCHAR(50),
    med_mail                     VARCHAR(150),
    med_user                     VARCHAR(100),
    med_password                 VARCHAR(255),          -- hash bcrypt, nunca texto plano
    med_reset_password           BOOLEAN NOT NULL DEFAULT FALSE,
    med_is_locked                BOOLEAN NOT NULL DEFAULT FALSE,
    med_is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    med_created_at               TIMESTAMP NOT NULL DEFAULT now(),
    med_updated_at               TIMESTAMP NOT NULL DEFAULT now()
);

-- Número de documento (si la tabla ya existía sin esta columna)
ALTER TABLE "Medics" ADD COLUMN IF NOT EXISTS med_document_number VARCHAR(30);
CREATE INDEX IF NOT EXISTS ix_medics_med_document_number ON "Medics" (med_document_number);

-- Especialidad (si la tabla ya existía sin esta columna)
ALTER TABLE "Medics" ADD COLUMN IF NOT EXISTS med_specialty VARCHAR(150);

-- Usuario único (si se asigna)
CREATE UNIQUE INDEX IF NOT EXISTS ux_medics_med_user
    ON "Medics" (lower(med_user)) WHERE med_user IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_medics_med_name ON "Medics" (med_name);

-- 2. Médico en la orden ------------------------------------------------------------
ALTER TABLE "Orders" ADD COLUMN IF NOT EXISTS o_medic_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_orders_o_medic_id') THEN
        ALTER TABLE "Orders"
            ADD CONSTRAINT fk_orders_o_medic_id
            FOREIGN KEY (o_medic_id) REFERENCES "Medics"(med_codigo);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_orders_o_medic_id ON "Orders" (o_medic_id);

-- 3. Permisos (uno por acción) ----------------------------------------------------
INSERT INTO "Permissions" (p_name, p_description, p_module)
SELECT v.p_name, v.p_description, 'Medics'
FROM (VALUES
    ('Medics:List',   'Listar médicos (también para elegir el médico al crear una orden)'),
    ('Medics:GetOne', 'Ver el detalle de un médico'),
    ('Medics:Create', 'Crear médicos'),
    ('Medics:Update', 'Editar médicos'),
    ('Medics:Delete', 'Eliminar médicos')
) AS v(p_name, p_description)
WHERE NOT EXISTS (SELECT 1 FROM "Permissions" p WHERE p.p_name = v.p_name);

-- Asignación inicial:
--  - Medics:List   → roles que crean órdenes (deben poder elegir el médico)
--  - Medics:GetOne → roles que ven estudios (maestros)
--  - Create / Update / Delete → roles que editan estudios (administran maestros)
INSERT INTO "RolPermissions" (rp_rol_id, rp_permission_id, rp_active)
SELECT DISTINCT rp.rp_rol_id, nuevo.p_id, TRUE
FROM "RolPermissions" rp
JOIN "Permissions" base  ON base.p_id = rp.rp_permission_id AND rp.rp_active
JOIN "Permissions" nuevo ON (base.p_name = 'Orders:Create'     AND nuevo.p_name = 'Medics:List')
                         OR (base.p_name = 'StudiesLab:List'   AND nuevo.p_name = 'Medics:GetOne')
                         OR (base.p_name = 'StudiesLab:Update' AND nuevo.p_name IN ('Medics:List', 'Medics:Create', 'Medics:Update', 'Medics:Delete'))
WHERE NOT EXISTS (SELECT 1 FROM "RolPermissions" x
                  WHERE x.rp_rol_id = rp.rp_rol_id AND x.rp_permission_id = nuevo.p_id);

COMMIT;

-- Verificación ---------------------------------------------------------------------
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'Medics'
ORDER BY ordinal_position;

SELECT p.p_name, string_agg(r.r_name, ', ' ORDER BY r.r_id) AS roles
FROM "Permissions" p
LEFT JOIN "RolPermissions" rp ON rp.rp_permission_id = p.p_id AND rp.rp_active
LEFT JOIN "Rols" r ON r.r_id = rp.rp_rol_id
WHERE p.p_module = 'Medics'
GROUP BY p.p_name
ORDER BY p.p_name;
