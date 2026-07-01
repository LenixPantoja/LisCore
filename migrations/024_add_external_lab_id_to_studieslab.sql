-- Migration: 024_add_external_lab_id_to_studieslab
-- Descripción: Agrega relación entre StudiesLab (estudios/perfiles) y ExternalReferenceLaboratories (laboratorios de referencia externos)
-- Un estudio puede estar asociado opcionalmente a un laboratorio de referencia al cual se envía para procesamiento

ALTER TABLE "StudiesLab"
ADD COLUMN external_lab_id INTEGER NULL;

ALTER TABLE "StudiesLab"
ADD CONSTRAINT fk_studieslab_external_lab
FOREIGN KEY (external_lab_id)
REFERENCES "ExternalReferenceLaboratories" (erl_id)
ON DELETE SET NULL;

CREATE INDEX idx_studieslab_external_lab_id
ON "StudiesLab" (external_lab_id);