-- =============================================================================
-- 067 - Notas de la orden por usuario
-- =============================================================================
-- Permite que el bacteriólogo (o cualquier usuario del laboratorio) agregue
-- notas a una orden desde Validación de Resultados. Cada nota guarda quién
-- la escribió y cuándo. La nota de ingreso (Orders.o_note) no cambia y se
-- sigue mostrando como la primera nota, a nombre de quien creó la orden.
--
-- Solo crea una tabla nueva: no modifica datos existentes. Seguro de correr
-- varias veces.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS "OrderNotes" (
    on_id         SERIAL PRIMARY KEY,
    on_order_id   INTEGER      NOT NULL REFERENCES "Orders"(o_id) ON DELETE CASCADE,
    on_text       TEXT         NOT NULL,
    on_user_id    INTEGER      NULL REFERENCES "AppUsers"(usr_id),
    on_created_at TIMESTAMP    NOT NULL DEFAULT (now() AT TIME ZONE 'America/Bogota'),
    CONSTRAINT ck_ordernotes_text CHECK (btrim(on_text) <> '')
);

CREATE INDEX IF NOT EXISTS ix_ordernotes_order ON "OrderNotes"(on_order_id, on_created_at);

COMMENT ON TABLE "OrderNotes" IS 'Notas agregadas a la orden por los usuarios del laboratorio (autor y fecha)';

COMMIT;

-- Verificación
SELECT count(*) AS notas_registradas FROM "OrderNotes";
