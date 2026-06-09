# Especificación Técnica y Arquitectura: Módulo de Remisiones (LIS)

Este documento detalla la estructura, funcionamiento y lógica de negocio para la implementación del **Módulo de Remisiones** dentro del ecosistema **LisCore / CitasLab**. El módulo gestiona de forma unificada la logística de traslado de muestras y asignación de pruebas tanto de forma **Local** (entre sedes del laboratorio) como **Externa** (derivación hacia laboratorios de referencia externos).

---

## 1. Arquitectura de Datos y Relaciones

El módulo se compone de cuatro (4) tablas principales que se acoplan directamente a la base de datos actual (`Headquarters`, `SamplesOrder`, `OrdersDetails` y `AppUsers`).

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

### Sentencias SQL de Creación (PostgreSQL)

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

CREATE SEQUENCE public."ExternalReferenceLaboratories_erl_id_seq" AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public."ExternalReferenceLaboratories_erl_id_seq" OWNED BY public."ExternalReferenceLaboratories".erl_id;
ALTER TABLE ONLY public."ExternalReferenceLaboratories" ALTER COLUMN erl_id SET DEFAULT nextval('public."ExternalReferenceLaboratories_erl_id_seq"'::regclass);

-- 2. Cabecera Logística de Remisiones
CREATE TABLE public."Remissions" (
    rem_id integer NOT NULL,
    rem_consecutive character varying(50) NOT NULL,
    rem_type character varying(20) NOT NULL, -- 'LOCAL' o 'EXTERNAL'
    rem_origin_headquarter_id integer NOT NULL,
    rem_dest_headquarter_id integer,
    rem_dest_external_lab_id integer,
    rem_state integer NOT NULL, -- 1: Pendiente, 2: Enviado, 3: Recibido Completo, 4: Recibido con Novedad, 5: Cancelado
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

CREATE SEQUENCE public."Remissions_rem_id_seq" AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public."Remissions_rem_id_seq" OWNED BY public."Remissions".rem_id;
ALTER TABLE ONLY public."Remissions" ALTER COLUMN rem_id SET DEFAULT nextval('public."Remissions_rem_id_seq"'::regclass);

-- 3. Detalle de Ítems Remitidos (Muestra y Examen)
CREATE TABLE public."RemissionDetails" (
    remd_id integer NOT NULL,
    remd_remission_id integer NOT NULL,
    remd_sample_order_id integer NOT NULL,
    remd_order_detail_id integer NOT NULL,
    remd_item_state integer NOT NULL, -- 1: Cargado, 2: Recibido Conforme, 3: Rechazado en Destino
    remd_rejection_reason text,
    remd_received_by_user_id integer,
    remd_updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT pk_remission_details PRIMARY KEY (remd_id)
);

CREATE SEQUENCE public."RemissionDetails_remd_id_seq" AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public."RemissionDetails_remd_id_seq" OWNED BY public."RemissionDetails".remd_id;
ALTER TABLE ONLY public."RemissionDetails" ALTER COLUMN remd_id SET DEFAULT nextval('public."RemissionDetails_remd_id_seq"'::regclass);

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

CREATE SEQUENCE public."RemissionStatesLog_rsl_id_seq" AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public."RemissionStatesLog_rsl_id_seq" OWNED BY public."RemissionStatesLog".rsl_id;
ALTER TABLE ONLY public."RemissionStatesLog" ALTER COLUMN rsl_id SET DEFAULT nextval('public."RemissionStatesLog_rsl_id_seq"'::regclass);

-- 5. Llaves Foráneas (Constraints)
ALTER TABLE ONLY public."Remissions"
    ADD CONSTRAINT fk_remission_origin_headquarter FOREIGN KEY (rem_origin_headquarter_id) REFERENCES public."Headquarters"(id),
    ADD CONSTRAINT fk_remission_dest_headquarter FOREIGN KEY (rem_dest_headquarter_id) REFERENCES public."Headquarters"(id),
    ADD CONSTRAINT fk_remission_dest_external FOREIGN KEY (rem_dest_external_lab_id) REFERENCES public."ExternalReferenceLaboratories"(erl_id),
    ADD CONSTRAINT fk_remission_user_creates FOREIGN KEY (rem_created_by_user_id) REFERENCES public."AppUsers"(usr_id);

ALTER TABLE ONLY public."RemissionDetails"
    ADD CONSTRAINT fk_rem_detail_parent FOREIGN KEY (remd_remission_id) REFERENCES public."Remissions"(rem_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_rem_detail_sample FOREIGN KEY (remd_sample_order_id) REFERENCES public."SamplesOrder"(so_id),
    ADD CONSTRAINT fk_rem_detail_order_detail FOREIGN KEY (remd_order_detail_id) REFERENCES public."OrdersDetails"(od_id),
    ADD CONSTRAINT fk_rem_detail_user_receiver FOREIGN KEY (remd_received_by_user_id) REFERENCES public."AppUsers"(usr_id);

ALTER TABLE ONLY public."RemissionStatesLog"
    ADD CONSTRAINT fk_rem_log_parent FOREIGN KEY (rsl_remission_id) REFERENCES public."Remissions"(rem_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_rem_log_user FOREIGN KEY (rsl_changed_by_user_id) REFERENCES public."AppUsers"(usr_id);
```

---

<h2>2. Flujo de Trabajo Funcional (Estados de la Remisión)</h2>

El ciclo de vida del proceso de remisión debe seguir estrictamente los siguientes estados en el backend:

1. **Pendiente (`rem_state = 1`):** La remisión está en creación. El usuario en la sede de origen agrega tubos (`SamplesOrder`) y sus respectivos exámenes (`OrdersDetails`). Las muestras aún están físicamente en la sede de origen.
2. **Enviado / En Ruta (`rem_state = 2`):** Se consolida el envío, se asigna el transportador (`rem_courier_name`) y la temperatura. Las muestras salen del laboratorio de origen.
3. **Proceso de Recepción en Destino:** El laboratorio destino (o sede interna destino) evalúa ítem por ítem dentro de `"RemissionDetails"`:
   * Si aprueba el ítem: `remd_item_state = 2` (Conforme).
   * Si rechaza el ítem (Ej: Hemólisis, muestra mal marcada): `remd_item_state = 3` (Rechazado) y se llena obligatoriamente `remd_rejection_reason`.
4. **Cierre Automático de Cabecera:**
   * **Recibido Completo (`rem_state = 3`):** Si el 100% de los ítems de `RemissionDetails` fueron marcados como *Recibido Conforme* (`2`).
   * **Recibido con Novedad (`rem_state = 4`):** Si al menos un ítem fue *Rechazado* (`3`).
5. **Cancelado (`rem_state = 5`):** Solo permitido si la remisión está en estado *Pendiente*. Libera las muestras inmediatamente.

---

## 3. Requerimientos de Implementación Backend (FastAPI / Django)

El desarrollador backend debe estructurar los endpoints siguiendo REST y aplicando reglas estrictas de negocio transaccionales.

### A. Endpoints Mandatorios a Desarrollar

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/v1/remissions` | Crea la cabecera en estado Pendiente. Genera el consecutivo automático. |
| `POST` | `/api/v1/remissions/{id}/items` | Agrega un array de ítems (par de `so_id` y `od_id`) al detalle de la remisión. |
| `DELETE`| `/api/v1/remissions/{id}/items/{detail_id}` | Elimina un ítem de la remisión (solo si está Pendiente). |
| `PATCH` | `/api/v1/remissions/{id}/ship` | Cambia el estado a Enviado (`2`). Registra transportador y temperatura de salida. |
| `PATCH` | `/api/v1/remissions/{id}/receive-item` | Procesa la recepción unitaria de un examen en el destino. Actualiza el estado del ítem. |
| `POST` | `/api/v1/external-laboratories` | CRUD de laboratorios de referencia externos. |

### B. Lógica de Negocio Crítica y Validaciones (Reglas del Backend)

El desarrollador backend debe validar e implementar los siguientes comportamientos por código:

#### 1. Generación del Consecutivo (`rem_consecutive`)
* No delegar al autoincremental secuencial. Debe seguir un formato legible de auditoría, por ejemplo: `REM-[AÑO]-[SEDE_ORIGEN_ID]-[SECUENCIAL]`.
* *Ejemplo:* `REM-2026-1-0043`

#### 2. Transaccionalidad Atómica en el Cambio de Estados
* Cada vez que cambie `rem_state` en la tabla `"Remissions"`, se **debe** insertar un registro de auditoría en `"RemissionStatesLog"`. Esto debe ocurrir dentro de una misma transacción SQL (`db.begin()`, `@transaction.atomic` o `async with session.begin()`).

#### 3. Control Mutex de Destinos (Integridad de Negocio)
* Si `rem_type == 'LOCAL'`, la API debe validar que `rem_dest_headquarter_id` pertenezca a un ID válido de `"Headquarters"` y que sea **diferente** a `rem_origin_headquarter_id`.
* Si `rem_type == 'EXTERNAL'`, la API debe validar que `rem_dest_external_lab_id` pertenezca a `"ExternalReferenceLaboratories"`.
* Si se envían datos cruzados o ambos destinos en el payload, el backend debe responder con un código HTTP `422 Unprocessable Entity` o `400 Bad Request`.

#### 4. Mutación de Estados del Examen en el Core LIS
* Al cambiar la remisión a estado **Enviado (`rem_state = 2`)**, los registros correspondientes en la tabla `"OrdersDetails"` deben actualizar de forma automática su estado interno a un código que represente *"Remitido / Muestra en Tránsito"* para alertar a los usuarios de la interfaz que la muestra no está en la sede actual.
* Si el ítem es **Rechazado en Destino (`remd_item_state = 3`)**, el backend debe revertir el estado en `"OrdersDetails"` a *"Muestra Rechazada"* o *"Pendiente Toma de Muestra"* para reingresar el flujo en el módulo de toma de muestras del LIS y notificar al bacteriólogo.

#### 5. Validación de Muestras ya Remitidas
* Al intentar agregar un ítem (`so_id` y `od_id`) a una remisión, el backend debe comprobar que ese par **no se encuentre** actualmente en otra remisión activa cuyo estado sea *Pendiente (1)* o *Enviado (2)*. Una muestra en tránsito o lista para despacho no puede ser duplicada en dos viajes simultáneos.

---

## 4. Estructura de Payloads (Esquemas de Entrada/Salida Pydantic / Serializers)

Para asegurar la correcta comunicación de los datos, el backend debe procesar los siguientes formatos de JSON:

### Creación de la Cabecera (`POST /api/v1/remissions`)
```json
{
  "rem_type": "EXTERNAL",
  "rem_origin_headquarter_id": 1,
  "rem_dest_headquarter_id": null,
  "rem_dest_external_lab_id": 3,
  "rem_observations": "Muestras de alta complejidad para secuenciación genética de la orden 1042."
}
```

### Adición de Ítems (`POST /api/v1/remissions/{id}/items`)
```json
{
  "items": [
    {
      "remd_sample_order_id": 450,
      "remd_order_detail_id": 891
    },
    {
      "remd_sample_order_id": 450,
      "remd_order_detail_id": 892
    }
  ]
}
```

### Despacho de la Remisión (`PATCH /api/v1/remissions/{id}/ship`)
```json
{
  "rem_courier_name": "Servientrega - Guía #91023941",
  "rem_temperature_courier": "Refrigerado (2°C a 8°C)"
}
```

### Recepción Unitaria en Destino (`PATCH /api/v1/remissions/{id}/receive-item`)
```json
{
  "remd_id": 128,
  "remd_item_state": 3,
  "remd_rejection_reason": "Tubo llegó quebrado debido al transporte. Muestra no apta para procesamiento."
}
```

---

## 5. Próxima Fase: Integración HL7 / Interoperabilidad (Opcional)

Si el laboratorio externo de referencia cuenta con canal de interoperabilidad, el backend deberá implementar un servicio (Worker en segundo plano) con la siguiente lógica:

1. Al pasar la remisión externa a estado **Enviado (2)**, disparar un webhook o generar un mensaje **HL7 OMR^O01** (Order Message) conteniendo los datos demográficos del paciente y la prueba solicitada (`OrdersDetails`), enviándolo a la API del laboratorio de destino.
2. Exponer un endpoint de recepción de resultados (`/api/v1/integrations/reference-results`) para que el laboratorio externo, una vez procese la muestra, haga un `POST` con un mensaje **HL7 ORU^R01** (Observation Result), permitiendo al backend del LIS mapear el resultado directamente a la tabla del sistema mediante el identificador único `remd_order_detail_id`.