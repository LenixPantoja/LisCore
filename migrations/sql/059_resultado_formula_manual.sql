-- =============================================================================
-- 059 - Resultado de fórmula escrito a mano
-- =============================================================================
-- Cuando una prueba calculada por fórmula (ej. GLOBULINAS = PROT-ALB) recibe un
-- valor escrito por el usuario, el backend lo marca con l_formula_manual = true
-- y deja de recalcularlo. Si el usuario borra el valor (o limpia el resultado),
-- se desmarca y la prueba vuelve a calcularse sola.
--
-- Seguro de correr varias veces. No modifica datos existentes: todas las filas
-- quedan en false (automático), que es el comportamiento actual.
-- En PostgreSQL 11+ agregar una columna con DEFAULT constante es instantáneo.
-- =============================================================================

ALTER TABLE "Laboratories"
    ADD COLUMN IF NOT EXISTS l_formula_manual BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN "Laboratories".l_formula_manual IS
    'true = resultado de fórmula escrito a mano por el usuario; no se recalcula.';

-- Verificación
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'Laboratories' AND column_name = 'l_formula_manual';
