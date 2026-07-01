# Especificación Técnica y Arquitectura: Módulo de Remisiones y Seroteca (LIS)

Este documento detalla la estructura, funcionamiento y lógica de negocio para la implementación del **Módulo de Remisiones** y el **Módulo de Seroteca** dentro del ecosistema **LisCore / CitasLab**. El módulo de remisiones gestiona la logística de traslado de muestras (Local y Externa). El módulo de seroteca gestiona el almacenamiento físico de muestras en freezers/refrigeradores usando gradillas configurables.

---

## 1. Arquitectura de Datos y Relaciones

### 1.1 Remisiones

El módulo de remisiones se compone de cuatro (4) tablas principales que se acoplan a la base de datos actual (`Headquarters`, `SamplesOrder`, `OrdersDetails` y `AppUsers`).

```
 +----------------------------------+          +------------------------+
 |   ExternalReferenceLaboratories  |          |      Headquarters      |
 +----------------------------------+          +------------------------+
 | erl_id (PK)                      |          | id (PK)                |
 +-------------------+--------------+          +-----------+------------+
                     |                                     |
                     | 0..* | 0..*
                     +-----------------+   +---------------+
                                       |   | (Origen / Destino Local)
                                     v v v v
                        +-------------------------------+
                        |          Remissions           |
                        +-------------------------------+
                        | rem_id (PK)                   |
                        | rem_origin_headquarter_id(FK) |
                        | rem_dest_headquarter_id (FK)  |
                        | rem_dest_external_lab_id (FK) |
                        | rem_created_by_user_id (FK)   |
                        +---------------+---------------+
                                        |
                                        | 1
                                        |
                                        | 0..*
                                      v v
                        +-------------------------------+
                        |        RemissionDetails       |
                        +-------------------------------+
                        | remd_id (PK)                  |
                        | remd_remission_id (FK)        |
                        | remd_sample_order_id (FK) ----+---> (SamplesOrder)
                        | remd_order_detail_id (FK) ----+---> (OrdersDetails)
                        +-------------------------------+
```

### 1.2 Seroteca — Tipos de Gradilla

El módulo de seroteca gestiona el almacenamiento físico de muestras mediante:

- **Serotecas**: Unidades de almacenamiento (freezer, refrigerador, gabinete)
- **Tipos de Gradilla**: Templates predefinidos de racks (filas × columnas) con días de almacenamiento
- **Gradillas**: Racks físicos dentro de una seroteca, que pueden basarse en un TipoGradilla
- **Posiciones**: Celdas individuales (auto-generadas al crear la gradilla)

```
 +------------------+          +--------------------------+
 |    Serotecas     |          |     TiposGradilla        |
 +------------------+          +--------------------------+
 | s_id (PK)        |          | tg_id (PK)               |
 | s_name           |          | tg_name                  |
 | s_headquarter_id |          | tg_rows                  |
 +--------+---------+          | tg_cols                  |
          |                    | tg_storage_days          |
          | 1                  +------------+-------------+
          |                                 |
          | 0..*                            | 0..* (opcional)
        v v                              v v
 +--------------------------------------------------+
 |                    Gradillas                       |
 +--------------------------------------------------+
 | g_id (PK)                                         |
 | g_name                                            |
 | g_seroteca_id (FK → Serotecas)                    |
 | g_tipo_gradilla_id (FK → TiposGradilla, nullable) |
 | g_rows, g_cols                                    |
 +--------------------+-----------------------------+
                      |
                      | 1
                      | 0..*
                    v v
 +--------------------------------------------------+
 |               GradillaPosiciones                  |
 +--------------------------------------------------+
 | gp_id (PK)                                        |
 | gp_gradilla_id (FK)                               |
 | gp_row, gp_col                                    |
 | gp_sample_id (FK → SamplesOrder, nullable)        |
 | gp_occupied                                       |
 +--------------------------------------------------+
```

### 1.3 Sentencias SQL de Creación

#### Tablas de Remisiones

```sql
-- 1. Directorio de laboratorios externos de referencia
CREATE TABLE public."ExternalReferenceLaboratories" (
    erl_id integer NOT NULL,
    erl_nit character varying(255) NOT NULL,
    erl_name character varying(255) NOT NULL,
    erl_address character varying(255),
    erl_phone character varying(255),
    erl_mail character varying(255),
    erl_active boolean DEFAULT true NOT NULL,
    erl_created_at timestamp without time zone DEFAULT now(),
    erl_updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT pk_external_ref_laboratories PRIMARY KEY (erl_id)
);

-- 2. Cabecera Logística de Remisiones
CREATE TABLE public."Remissions" (
    rem_id integer NOT NULL,
    rem_consecutive character varying(50) NOT NULL,
    rem_type character varying(20) NOT NULL,
    rem_origin_headquarter_id integer NOT NULL,
    rem_dest_headquarter_id integer,
    rem_dest_external_lab_id integer,
    rem_state integer NOT NULL,
    rem_courier_name character varying(255),
    rem_temperature_courier character varying(100),
    rem_observations text,
    rem_created_by_user_id integer NOT NULL,
    rem_created_at timestamp without time zone DEFAULT now() NOT NULL,
    rem_sent_at timestamp without time zone,
    rem_received_at timestamp without time zone,
    CONSTRAINT pk_remissions PRIMARY KEY (rem_id),
    CONSTRAINT chk_remission_type CHECK (rem_type IN ('LOCAL', 'EXTERNAL')),
    CONSTRAINT chk_remission_destination CHECK (
        (rem_type = 'LOCAL' AND rem_dest_headquarter_id IS NOT NULL AND rem_dest_external_lab_id IS NULL) OR
        (rem_type = 'EXTERNAL' AND rem_dest_external_lab_id IS NOT NULL AND rem_dest_headquarter_id IS NULL)
    )
);

-- 3. Detalle de Ítems Remitidos
CREATE TABLE public."RemissionDetails" (
    remd_id integer NOT NULL,
    remd_remission_id integer NOT NULL,
    remd_sample_order_id integer NOT NULL,
    remd_order_detail_id integer NOT NULL,
    remd_item_state integer NOT NULL,
    remd_rejection_reason text,
    remd_received_by_user_id integer,
    remd_updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT pk_remission_details PRIMARY KEY (remd_id)
);

-- 4. Historial de Auditoría de Estados
CREATE TABLE public."RemissionStatesLog" (
    rsl_id integer NOT NULL,
    rsl_remission_id integer NOT NULL,
    rsl_state_before integer,
    rsl_state_after integer NOT NULL,
    rsl_changed_by_user_id integer NOT NULL,
    rsl_notes text,
    rsl_created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT pk_remission_states_log PRIMARY KEY (rsl_id)
);
```

#### Tablas de Seroteca — Tipos de Gradilla

```sql
-- 5. Tipos de Gradilla (templates de racks)
CREATE TABLE "TiposGradilla" (
    tg_id SERIAL PRIMARY KEY,
    tg_name VARCHAR(255) NOT NULL,
    tg_rows INTEGER NOT NULL,
    tg_cols INTEGER NOT NULL,
    tg_storage_days INTEGER NOT NULL DEFAULT 30,
    tg_active BOOLEAN NOT NULL DEFAULT TRUE,
    tg_created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    tg_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- 6. Agregar FK de tipo de gradilla en Gradillas
ALTER TABLE "Gradillas"
ADD COLUMN g_tipo_gradilla_id INTEGER,
ADD CONSTRAINT fk_gradilla_tipo_gradilla
    FOREIGN KEY (g_tipo_gradilla_id)
    REFERENCES "TiposGradilla"(tg_id)
    ON DELETE SET NULL;
```

---

## 2. Flujo de Trabajo Funcional (Estados de la Remisión)

El ciclo de vida del proceso de remisión debe seguir estrictamente los siguientes estados:

1. **Pendiente (`rem_state = 1`):** La remisión está en creación. El usuario en la sede de origen agrega tubos (`SamplesOrder`) y sus respectivos exámenes (`OrdersDetails`).
2. **Enviado / En Ruta (`rem_state = 2`):** Se consolida el envío, se asigna el transportador (`rem_courier_name`) y la temperatura.
3. **Proceso de Recepción en Destino:** El laboratorio destino evalúa ítem por ítem:
   - Conforme: `remd_item_state = 2`
   - Rechazado: `remd_item_state = 3` (requiere `remd_rejection_reason`)
4. **Cierre Automático de Cabecera:**
   - **Recibido Completo (`rem_state = 3`):** 100% de ítems recibidos conforme.
   - **Recibido con Novedad (`rem_state = 4`):** Al menos un ítem rechazado.
5. **Cancelado (`rem_state = 5`):** Solo si está Pendiente.

---

## 3. Requerimientos de Implementación Backend

### A. Endpoints de Remisiones

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/remissions` | Crea cabecera en estado Pendiente. |
| `POST` | `/remissions/{id}/items` | Agrega array de ítems (`so_id` + `od_id`). |
| `DELETE`| `/remissions/{id}/items/{detail_id}` | Elimina ítem (solo Pendiente). |
| `PATCH` | `/remissions/{id}/ship` | Cambia estado a Enviado (2). |
| `PATCH` | `/remissions/{id}/receive-item` | Procesa recepción unitaria. |
| `POST` | `/external-laboratories` | CRUD laboratorios externos. |

### B. Endpoints de Seroteca — Tipos de Gradilla

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/seroteca/tipos-gradilla` | Crear tipo de gradilla (template) |
| `GET` | `/seroteca/tipos-gradilla` | Listar tipos (búsqueda, filtro active_only) |
| `GET` | `/seroteca/tipos-gradilla/{tg_id}` | Obtener detalle de un tipo |
| `PATCH` | `/seroteca/tipos-gradilla/{tg_id}` | Actualizar tipo de gradilla |
| `DELETE` | `/seroteca/tipos-gradilla/{tg_id}` | Eliminar tipo de gradilla |

**Crear una gradilla desde un tipo:**

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/seroteca/serotecas/{s_id}/racks` | Crear gradilla. Si se envía `g_tipo_gradilla_id`, hereda rows/cols del template |

### C. Lógica de Negocio Crítica

#### Generación del Consecutivo (`rem_consecutive`)
Formato: `REM-[AÑO]-[SEDE_ORIGEN_ID]-[SECUENCIAL]`. Ejemplo: `REM-2026-1-0043`

#### Transaccionalidad Atómica
Cada cambio de `rem_state` inserta un registro en `RemissionStatesLog` dentro de la misma transacción.

#### Control de Destinos
- `LOCAL`: `rem_dest_headquarter_id` requerido, diferente a `rem_origin_headquarter_id`
- `EXTERNAL`: `rem_dest_external_lab_id` requerido

#### Tipos de Gradilla (Seroteca)
- **Creación de tipo**: Define nombre, filas (1-100), columnas (1-100) y días de almacenamiento (1-3650)
- **Uso al crear gradilla**: Si se envía `g_tipo_gradilla_id`, el backend auto-completa `g_rows` y `g_cols` desde el template
- **Independencia**: Se pueden crear gradillas sin tipo (especificando rows/cols manualmente)
- **Permiso requerido**: `Seroteca:ManageRackTypes`

#### Mutación de Estados del Examen
- Al enviar (`rem_state = 2`), `OrdersDetails` se actualiza a "Remitido / En Tránsito"
- Si ítem es Rechazado (`remd_item_state = 3`), se revierte a "Muestra Rechazada"

#### Validación de Muestras ya Remitidas
Un par (`so_id`, `od_id`) no puede estar en dos remisiones activas (estados 1 o 2) simultáneamente.

---

## 4. Estructura de Payloads

### Creación de Cabecera de Remisión (`POST /remissions`)
```json
{
  "rem_type": "EXTERNAL",
  "rem_origin_headquarter_id": 1,
  "rem_dest_headquarter_id": null,
  "rem_dest_external_lab_id": 3,
  "rem_observations": "Muestras de alta complejidad para secuenciación genética."
}
```

### Adición de Ítems (`POST /remissions/{id}/items`)
```json
{
  "items": [
    { "remd_sample_order_id": 450, "remd_order_detail_id": 891 },
    { "remd_sample_order_id": 450, "remd_order_detail_id": 892 }
  ]
}
```

### Crear Tipo de Gradilla (`POST /seroteca/tipos-gradilla`)
```json
{
  "tg_name": "Gradilla 10x10",
  "tg_rows": 10,
  "tg_cols": 10,
  "tg_storage_days": 90
}
```

### Crear Gradilla desde Tipo (`POST /seroteca/serotecas/{s_id}/racks`)
```json
{
  "g_name": "Rack VPH Mayo",
  "g_tipo_gradilla_id": 1
}
```
> El backend hereda automáticamente `g_rows=10`, `g_cols=10` del tipo.

### Actualizar Tipo de Gradilla (`PATCH /seroteca/tipos-gradilla/{tg_id}`)
```json
{
  "tg_name": "Gradilla 10x10 Modificada",
  "tg_storage_days": 120,
  "tg_active": true
}
```

---

## 5. Permisos RBAC

### Remisiones
| Permiso | Descripción |
| :--- | :--- |
| `Remissions:View` | Ver y listar remisiones |
| `Remissions:Create` | Crear remisiones y agregar/quitar ítems |
| `Remissions:Ship` | Enviar remisiones |
| `Remissions:Receive` | Procesar recepción de ítems en destino |
| `Remissions:Cancel` | Cancelar remisiones pendientes |
| `Remissions:ManageExternalLabs` | CRUD de laboratorios externos |

### Seroteca
| Permiso | Descripción |
| :--- | :--- |
| `Seroteca:Create` | Crear serotecas |
| `Seroteca:List` | Listar serotecas |
| `Seroteca:GetOne` | Ver detalle de seroteca |
| `Seroteca:Update` | Actualizar seroteca |
| `Seroteca:Delete` | Eliminar seroteca |
| `Seroteca:ManageRacks` | CRUD de gradillas/racks |
| `Seroteca:ManageRackTypes` | CRUD de tipos de gradilla (templates) |
| `Seroteca:StoreSample` | Almacenar/retirar muestras |
| `Tracking:Log` | Registrar eventos de seguimiento |
| `Tracking:Read` | Consultar historial de trazabilidad |

---

## 6. Migraciones

| # | Archivo | Descripción |
| :--- | :--- | :--- |
| 022 | `022_seed_remissions_permissions.py` | Siembra permisos de Remissions |
| 026 | `026_create_tipos_gradilla_table.py` | Crea tabla `TiposGradilla` + FK en `Gradillas` |
| 027 | `027_seed_seroteca_tipos_gradilla_permissions.py` | Siembra permiso `Seroteca:ManageRackTypes` |

---

## 7. Próxima Fase: Integración HL7 / Interoperabilidad (Opcional)

Si el laboratorio externo cuenta con canal de interoperabilidad:
1. Al enviar remisión externa (`rem_state = 2`), disparar mensaje **HL7 OMR^O01** con datos del paciente y pruebas.
2. Exponer endpoint `/integrations/reference-results` para recibir **HL7 ORU^R01** con resultados mapeados por `remd_order_detail_id`.