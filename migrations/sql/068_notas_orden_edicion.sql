-- =============================================================================
-- 068 - Notas de la orden: fecha de modificación
-- =============================================================================
-- Permite marcar como "Editada" una nota que su autor modificó. Solo agrega
-- una columna vacía (NULL = nunca editada). No modifica datos existentes.
-- Requiere el script 067. Seguro de correr varias veces.
-- =============================================================================

BEGIN;

ALTER TABLE "OrderNotes" ADD COLUMN IF NOT EXISTS on_updated_at TIMESTAMP NULL;

COMMENT ON COLUMN "OrderNotes".on_updated_at IS 'Última modificación hecha por el autor (NULL = sin editar)';

COMMIT;

-- Verificación
SELECT count(*) FILTER (WHERE on_updated_at IS NOT NULL) AS notas_editadas, count(*) AS total
FROM "OrderNotes";
