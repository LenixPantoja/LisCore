-- =============================================================================
-- 069 - Cantidad de etiquetas a imprimir por estudio y por prueba
-- =============================================================================
-- Permite configurar cuántas etiquetas (stickers) se imprimen del tubo donde
-- va un estudio o una prueba. Ej.: PO = 2, Frotis = 3.
--
--   NULL = usar la cantidad general de la plantilla de etiquetas (barcodes).
--
-- Regla al imprimir: cada etiqueta de tubo se imprime la MAYOR cantidad entre
-- la plantilla general, los estudios de ese tubo y sus pruebas.
--
-- Solo agrega columnas vacías; no modifica datos existentes.
-- Seguro de correr varias veces.
-- IMPORTANTE: correr ANTES de desplegar el backend.
-- =============================================================================

BEGIN;

ALTER TABLE "StudiesLab" ADD COLUMN IF NOT EXISTS labels_to_print INTEGER NULL;
ALTER TABLE "TestsLab"   ADD COLUMN IF NOT EXISTS labels_to_print INTEGER NULL;

ALTER TABLE "StudiesLab" DROP CONSTRAINT IF EXISTS ck_studieslab_labels_to_print;
ALTER TABLE "StudiesLab" ADD CONSTRAINT ck_studieslab_labels_to_print
    CHECK (labels_to_print IS NULL OR labels_to_print BETWEEN 1 AND 20);

ALTER TABLE "TestsLab" DROP CONSTRAINT IF EXISTS ck_testslab_labels_to_print;
ALTER TABLE "TestsLab" ADD CONSTRAINT ck_testslab_labels_to_print
    CHECK (labels_to_print IS NULL OR labels_to_print BETWEEN 1 AND 20);

COMMENT ON COLUMN "StudiesLab".labels_to_print IS 'Etiquetas a imprimir del tubo de este estudio (NULL = cantidad general)';
COMMENT ON COLUMN "TestsLab".labels_to_print   IS 'Etiquetas a imprimir del tubo de esta prueba (NULL = cantidad general)';

COMMIT;

-- Verificación
SELECT 'StudiesLab' AS tabla, count(*) FILTER (WHERE labels_to_print IS NOT NULL) AS configurados FROM "StudiesLab"
UNION ALL
SELECT 'TestsLab', count(*) FILTER (WHERE labels_to_print IS NOT NULL) FROM "TestsLab";
