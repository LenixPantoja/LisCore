# Guía de Integración Frontend: Módulo de Remisiones y Seroteca (Angular)

Este documento describe cómo integrar los módulos de **Remisiones** y **Seroteca (Tipos de Gradilla)** del backend **LisCore** en una aplicación **Angular**. Cubre la estructura de servicios, modelos TypeScript, componentes sugeridos y flujo de trabajo de la UI.

---

## 1. Base URL y Autenticación

Todas las peticiones deben incluir el token JWT en el header `Authorization`:

```
Authorization: Bearer <token>
```

Realizar login contra `POST /api/users/login` para obtener el token.

Módulos y prefijos:
- **Remisiones:** `{base_url}/api/v1/remissions/...`
- **Laboratorios Externos:** `{base_url}/api/v1/external-laboratories/...`
- **Seroteca:** `{base_url}/api/v1/seroteca/...`

---

## 2. Modelos TypeScript (Interfaces)

### 2.1 Remisiones (`remission.model.ts`)

```typescript
// ── External Reference Laboratories ───────────────────────────

export interface ExternalLab {
  erl_id: number;
  erl_nit: string;
  erl_name: string;
  erl_address?: string;
  erl_phone?: string;
  erl_mail?: string;
  erl_active: boolean;
  erl_created_at: string;
  erl_updated_at: string;
}

export interface ExternalLabCreate {
  erl_nit: string;
  erl_name: string;
  erl_address?: string;
  erl_phone?: string;
  erl_mail?: string;
  erl_active?: boolean;
}

export interface ExternalLabUpdate {
  erl_nit?: string;
  erl_name?: string;
  erl_address?: string;
  erl_phone?: string;
  erl_mail?: string;
  erl_active?: boolean;
}

// ── Remission ──────────────────────────────────────────────────

export interface Remission {
  rem_id: number;
  rem_consecutive: string;
  rem_type: 'LOCAL' | 'EXTERNAL';
  rem_origin_headquarter_id: number;
  rem_dest_headquarter_id?: number;
  rem_dest_external_lab_id?: number;
  rem_state: RemissionState;
  rem_courier_name?: string;
  rem_temperature_courier?: string;
  rem_observations?: string;
  rem_created_by_user_id: number;
  rem_created_at: string;
  rem_sent_at?: string;
  rem_received_at?: string;
}

export type RemissionState = 1 | 2 | 3 | 4 | 5;

export const RemissionStateLabels: Record<RemissionState, string> = {
  1: 'Pendiente',
  2: 'Enviado / En Ruta',
  3: 'Recibido Completo',
  4: 'Recibido con Novedad',
  5: 'Cancelado',
};

export interface RemissionCreate {
  rem_type: 'LOCAL' | 'EXTERNAL';
  rem_origin_headquarter_id: number;
  rem_dest_headquarter_id?: number;
  rem_dest_external_lab_id?: number;
  rem_observations?: string;
}

export interface HeadquarterInfo {
  name?: string;
}

export interface UserInfo {
  usr_login?: string;
  full_name?: string;
}

export interface RemissionDetail {
  rem_id: number;
  rem_consecutive: string;
  rem_type: string;
  origin_headquarter?: HeadquarterInfo | null;
  dest_headquarter?: HeadquarterInfo | null;
  dest_external_lab?: ExternalLab | null;
  created_by_user?: UserInfo | null;
  details: RemissionDetailItem[];
}

export interface RemissionDetailItem {
  remd_id: number;
  remd_remission_id: number;
  remd_sample_order_id: number;
  remd_order_detail_id: number;
  remd_item_state: ItemState;
  remd_rejection_reason?: string;
  remd_received_by_user_id?: number;
  remd_updated_at: string;
}

export type ItemState = 1 | 2 | 3;

export const ItemStateLabels: Record<ItemState, string> = {
  1: 'Cargado',
  2: 'Recibido Conforme',
  3: 'Rechazado en Destino',
};

export interface AddItemsRequest {
  items: {
    remd_sample_order_id: number;
    remd_order_detail_id: number;
  }[];
}

export interface ShipRequest {
  rem_courier_name?: string;
  rem_temperature_courier?: string;
}

export interface ReceiveItemRequest {
  remd_id: number;
  remd_item_state: 2 | 3;
  remd_rejection_reason?: string;
}

export interface CancelRequest {
  notes?: string;
}
```

### 2.2 Seroteca — Tipos de Gradilla (`seroteca.model.ts`)

```typescript
// ── Tipo de Gradilla (template de rack) ────────────────────────

export interface TipoGradilla {
  tg_id: number;
  tg_name: string;
  tg_rows: number;
  tg_cols: number;
  tg_storage_days: number;   // días de almacenamiento (1-3650)
  tg_active: boolean;
  tg_created_at: string;
  tg_updated_at: string;
}

export interface TipoGradillaCreate {
  tg_name: string;
  tg_rows: number;            // 1-100
  tg_cols: number;            // 1-100
  tg_storage_days: number;    // 1-3650
}

export interface TipoGradillaUpdate {
  tg_name?: string;
  tg_rows?: number;
  tg_cols?: number;
  tg_storage_days?: number;
  tg_active?: boolean;
}

// ── Gradilla (rack) ────────────────────────────────────────────

export interface Gradilla {
  g_id: number;
  g_name: string;
  g_seroteca_id: number;
  g_tipo_gradilla_id?: number;
  g_rows: number;
  g_cols: number;
  g_active: boolean;
  g_created_by?: number;
  g_created_at: string;
  g_updated_at: string;
}

/** Crear una gradilla. Si se envía g_tipo_gradilla_id, rows/cols se heredan del template */
export interface GradillaCreate {
  g_name: string;
  g_seroteca_id: number;
  g_tipo_gradilla_id?: number;   // opcional — hereda dimensiones del tipo
  g_rows?: number;               // opcional si se usó g_tipo_gradilla_id
  g_cols?: number;               // opcional si se usó g_tipo_gradilla_id
}

// ── Paginated Responses ────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface MessageResponse {
  success: boolean;
  message: string;
}
```

---

## 3. Servicios Angular

### 3.1 External Labs Service (`external-lab.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  ExternalLab,
  ExternalLabCreate,
  ExternalLabUpdate,
  PaginatedResponse,
  MessageResponse,
} from '@core/models/remission.model';

@Injectable({ providedIn: 'root' })
export class ExternalLabService {
  private base = `${environment.apiUrl}/api/external-laboratories`;

  constructor(private http: HttpClient) {}

  list(activeOnly = true): Observable<PaginatedResponse<ExternalLab>> {
    return this.http.get<PaginatedResponse<ExternalLab>>(this.base, {
      params: { active_only: activeOnly },
    });
  }

  getById(id: number): Observable<ExternalLab> {
    return this.http.get<ExternalLab>(`${this.base}/${id}`);
  }

  create(data: ExternalLabCreate): Observable<ExternalLab> {
    return this.http.post<ExternalLab>(this.base, data);
  }

  update(id: number, data: ExternalLabUpdate): Observable<ExternalLab> {
    return this.http.put<ExternalLab>(`${this.base}/${id}`, data);
  }

  delete(id: number): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/${id}`);
  }
}
```

### 3.2 Remissions Service (`remission.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  Remission, RemissionDetail, RemissionCreate,
  RemissionCreatedResponse, AddItemsRequest, AddItemsResponse,
  ShipRequest, ReceiveItemRequest, CancelRequest,
  PaginatedResponse, MessageResponse,
} from '@core/models/remission.model';

@Injectable({ providedIn: 'root' })
export class RemissionService {
  private base = `${environment.apiUrl}/api/remissions`;

  constructor(private http: HttpClient) {}

  create(data: RemissionCreate): Observable<RemissionCreatedResponse> {
    return this.http.post<RemissionCreatedResponse>(this.base, data);
  }

  list(filters?: {
    state?: number; type?: string; origin_hq_id?: number;
    skip?: number; limit?: number;
  }): Observable<PaginatedResponse<Remission>> {
    let params = new HttpParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params = params.set(key, String(value));
        }
      });
    }
    return this.http.get<PaginatedResponse<Remission>>(this.base, { params });
  }

  getById(id: number): Observable<RemissionDetail> {
    return this.http.get<RemissionDetail>(`${this.base}/${id}`);
  }

  addItems(remissionId: number, data: AddItemsRequest): Observable<AddItemsResponse> {
    return this.http.post<AddItemsResponse>(`${this.base}/${remissionId}/items`, data);
  }

  removeItem(remissionId: number, detailId: number): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/${remissionId}/items/${detailId}`);
  }

  ship(remissionId: number, data: ShipRequest): Observable<MessageResponse> {
    return this.http.patch<MessageResponse>(`${this.base}/${remissionId}/ship`, data);
  }

  receiveItem(remissionId: number, data: ReceiveItemRequest): Observable<MessageResponse> {
    return this.http.patch<MessageResponse>(`${this.base}/${remissionId}/receive-item`, data);
  }

  cancel(remissionId: number, data?: CancelRequest): Observable<MessageResponse> {
    return this.http.patch<MessageResponse>(`${this.base}/${remissionId}/cancel`, data ?? {});
  }
}
```

### 3.3 Tipos de Gradilla Service (`tipo-gradilla.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  TipoGradilla, TipoGradillaCreate, TipoGradillaUpdate,
  PaginatedResponse, MessageResponse,
} from '@core/models/seroteca.model';

@Injectable({ providedIn: 'root' })
export class TipoGradillaService {
  private base = `${environment.apiUrl}/api/seroteca/tipos-gradilla`;

  constructor(private http: HttpClient) {}

  list(filters?: {
    search?: string;
    active_only?: boolean;
    skip?: number;
    limit?: number;
  }): Observable<PaginatedResponse<TipoGradilla>> {
    let params = new HttpParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params = params.set(key, String(value));
        }
      });
    }
    return this.http.get<PaginatedResponse<TipoGradilla>>(this.base, { params });
  }

  getById(tg_id: number): Observable<TipoGradilla> {
    return this.http.get<TipoGradilla>(`${this.base}/${tg_id}`);
  }

  create(data: TipoGradillaCreate): Observable<TipoGradilla> {
    return this.http.post<TipoGradilla>(this.base, data);
  }

  update(tg_id: number, data: TipoGradillaUpdate): Observable<TipoGradilla> {
    return this.http.patch<TipoGradilla>(`${this.base}/${tg_id}`, data);
  }

  delete(tg_id: number): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/${tg_id}`);
  }
}
```

---

## 4. Mapeo de Permisos RBAC

### Remisiones

| Permiso | Endpoint(s) | UI Componentes |
|---------|-------------|----------------|
| `Remissions:View` | GET list, GET byId | Tabla de remisiones, detalle, lista de labs externos |
| `Remissions:Create` | POST create, POST items, DELETE items | Formulario crear remisión, agregar/quitar ítems |
| `Remissions:Ship` | PATCH ship | Botón "Enviar" en detalle de remisión |
| `Remissions:Receive` | PATCH receive-item | Panel de recepción de ítems en destino |
| `Remissions:Cancel` | PATCH cancel | Botón "Cancelar" (visible solo en Pendiente) |
| `Remissions:ManageExternalLabs` | CRUD external labs | CRUD de laboratorios externos |

### Seroteca

| Permiso | Endpoint(s) | UI Componentes |
|---------|-------------|----------------|
| `Seroteca:List` | GET serotecas | Listado de serotecas |
| `Seroteca:Create` | POST serotecas | Formulario crear seroteca |
| `Seroteca:GetOne` | GET serotecas/{id} | Detalle de seroteca |
| `Seroteca:Update` | PATCH serotecas/{id} | Editar seroteca |
| `Seroteca:Delete` | DELETE serotecas/{id} | Eliminar seroteca |
| `Seroteca:ManageRacks` | CRUD racks | CRUD de gradillas/racks dentro de una seroteca |
| `Seroteca:ManageRackTypes` | CRUD tipos-gradilla | CRUD de tipos de gradilla (templates) |
| `Seroteca:StoreSample` | POST store, DELETE release | Almacenar/retirar muestras en posiciones |
| `Tracking:Log` | POST samples/track | Registrar eventos de seguimiento |
| `Tracking:Read` | GET samples/{barcode}/history | Consultar historial de trazabilidad |

---

## 5. Estructura de Componentes Sugerida

```
src/app/pages/remissions/
├── remission-list/                 # Listado paginado con filtros
├── remission-create/               # Formulario de creación
├── remission-detail/               # Vista detalle de una remisión
├── remission-receive/              # Panel de recepción de ítems
└── external-labs/                  # CRUD de laboratorios externos

src/app/pages/seroteca/
├── seroteca-list/                  # Listado de serotecas
├── seroteca-form/                  # Crear/editar seroteca
├── seroteca-detail/                # Detalle con gradillas y posiciones
├── gradilla-positions/             # Vista de posiciones de una gradilla
├── tipo-gradilla-list/             # Listado de tipos de gradilla
└── tipo-gradilla-form/             # Crear/editar tipo de gradilla
```

---

## 6. Flujos de Pantalla

### 6.1 Remisiones — Listado

- **Ruta:** `/remissions`
- **Filtros:** Estado, Tipo (LOCAL/EXTERNAL), Sede Origen
- **Columnas:** Consecutivo, Tipo, Origen, Destino, Estado, Fecha Creación, Acciones
- **Badges de estado:**
  - `1 (Pendiente)` → Azul claro
  - `2 (Enviado)` → Naranja
  - `3 (Recibido Completo)` → Verde
  - `4 (Recibido con Novedad)` → Amarillo
  - `5 (Cancelado)` → Rojo
- **Acciones:** Ver detalle (siempre), Cancelar (solo estado=1 y permiso `Remissions:Cancel`)

### 6.2 Remisiones — Crear

- **Ruta:** `/remissions/create`
- **Campos:**
  1. **Tipo de Remisión** (radio buttons: LOCAL / EXTERNAL)
  2. **Sede Origen** (dropdown de `Headquarters`)
  3. **Destino:** LOCAL → dropdown de sedes (excluir origen). EXTERNAL → dropdown de labs externos activos
  4. **Observaciones** (textarea opcional)
- Al crear, redirigir al detalle para agregar ítems.

### 6.3 Remisiones — Detalle

- **Ruta:** `/remissions/:id`
- **Secciones:** Cabecera, Tabla de ítems, Historial de estados
- **Botones contextuales:**
  - Pendiente (1): Agregar ítems, Quitar ítems, Enviar, Cancelar
  - Enviado (2): Recibir ítems
  - Resto: Solo lectura

### 6.4 Remisiones — Enviar

- **Modal** con campos: Transportador, Temperatura
- `PATCH /api/remissions/{id}/ship`

### 6.5 Remisiones — Recibir Ítem

- **Ruta:** `/remissions/:id/receive`
- Tabla de ítems con botones: ✅ Recibido Conforme, ❌ Rechazado (requiere motivo)
- Al procesar todos, la cabecera se cierra automáticamente.

### 6.6 Tipos de Gradilla — Listado

- **Ruta:** `/seroteca/tipos-gradilla`
- **Filtros:** Búsqueda por nombre, activos/inactivos
- **Columnas:** Nombre, Filas, Columnas, Días de almacenamiento, Activo, Acciones
- **Acciones:** Crear (botón superior), Editar, Eliminar (desactivar)
- **Permiso requerido:** `Seroteca:ManageRackTypes`

### 6.7 Tipos de Gradilla — Formulario

- **Ruta:** `/seroteca/tipos-gradilla/create` o `/seroteca/tipos-gradilla/:id/edit`
- **Campos:**
  - **Nombre** (ej: "Gradilla 10x10", "Positivos VPH", "Gradilla 5x10")
  - **Nro Filas** (1-100)
  - **Nro Columnas** (1-100)
  - **Días de almacenamiento** (1-3650)
- **Endpoints:**
  - `POST /api/seroteca/tipos-gradilla` → Crear
  - `PATCH /api/seroteca/tipos-gradilla/{tg_id}` → Actualizar

### 6.8 Crear Gradilla desde un Tipo

Al crear una gradilla dentro de una seroteca (`POST /api/seroteca/serotecas/{s_id}/racks`):
- El formulario permite seleccionar un **Tipo de Gradilla** (dropdown de tipos activos)
- Si se selecciona un tipo, los campos `g_rows` y `g_cols` se auto-completan desde el template y se deshabilitan
- También se puede crear una gradilla sin tipo (especificando filas/columnas manualmente)
- **Payload de ejemplo** usando tipo:
  ```json
  { "g_name": "Rack VPH Mayo", "g_seroteca_id": 1, "g_tipo_gradilla_id": 2 }
  ```
- **Payload sin tipo:**
  ```json
  { "g_name": "Rack Manual", "g_seroteca_id": 1, "g_rows": 8, "g_cols": 12 }
  ```

---

## 7. Configuración de Rutas (app-routing.module.ts)

```typescript
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PermissionGuard } from '@core/guards/permission.guard';

const routes: Routes = [
  // ── Remisiones ──────────────────────────────────────────────
  {
    path: 'remissions',
    canActivate: [PermissionGuard],
    data: { permission: 'Remissions:View' },
    children: [
      { path: '', component: RemissionListComponent },
      { path: 'create', component: RemissionCreateComponent,
        data: { permission: 'Remissions:Create' } },
      { path: ':id', component: RemissionDetailComponent },
      { path: ':id/receive', component: RemissionReceiveComponent,
        data: { permission: 'Remissions:Receive' } },
    ],
  },
  {
    path: 'external-laboratories',
    canActivate: [PermissionGuard],
    data: { permission: 'Remissions:View' },
    children: [
      { path: '', component: ExternalLabListComponent },
      { path: 'create', component: ExternalLabFormComponent,
        data: { permission: 'Remissions:ManageExternalLabs' } },
      { path: ':id/edit', component: ExternalLabFormComponent,
        data: { permission: 'Remissions:ManageExternalLabs' } },
    ],
  },

  // ── Seroteca — Tipos de Gradilla ────────────────────────────
  {
    path: 'seroteca/tipos-gradilla',
    canActivate: [PermissionGuard],
    data: { permission: 'Seroteca:ManageRackTypes' },
    children: [
      { path: '', component: TipoGradillaListComponent },
      { path: 'create', component: TipoGradillaFormComponent },
      { path: ':id/edit', component: TipoGradillaFormComponent },
    ],
  },
];
```

---

## 8. Consideraciones de UX

1. **Confirmaciones:** Antes de Enviar, Cancelar, Rechazar ítem o Eliminar tipo de gradilla, mostrar diálogo de confirmación.
2. **Notificaciones:** Usar toast/snackbar para feedback de operaciones exitosas o errores.
3. **Loading states:** Mostrar spinners durante peticiones (crear, enviar, recibir).
4. **Manejo de errores 422:** El backend retorna `422 Unprocessable Entity` con `detail`. Mostrar el mensaje al usuario.
5. **Actualización en tiempo real:** Al recibir un ítem, refrescar la tabla y el estado de la cabecera.
6. **Badges de estado de ítems:**
   - Cargado (1) → Gris
   - Recibido Conforme (2) → Verde
   - Rechazado (3) → Rojo
7. **Tipo de Gradilla:** Al seleccionar un tipo en el formulario de creación de gradilla, deshabilitar campos de filas/columnas (se heredan del template).

---

## 9. Resumen de Endpoints API

### Remisiones

| Método | URL | Body | Respuesta |
|--------|-----|------|-----------|
| `GET` | `/api/remissions` | — (query params) | `PaginatedResponse<Remission>` |
| `POST` | `/api/remissions` | `RemissionCreate` | `RemissionCreatedResponse` |
| `GET` | `/api/remissions/{id}` | — | `RemissionDetail` |
| `POST` | `/api/remissions/{id}/items` | `AddItemsRequest` | `AddItemsResponse` |
| `DELETE` | `/api/remissions/{id}/items/{detailId}` | — | `MessageResponse` |
| `PATCH` | `/api/remissions/{id}/ship` | `ShipRequest` | `MessageResponse` |
| `PATCH` | `/api/remissions/{id}/receive-item` | `ReceiveItemRequest` | `MessageResponse` |
| `PATCH` | `/api/remissions/{id}/cancel` | `CancelRequest` | `MessageResponse` |
| `GET` | `/api/external-laboratories` | — | `PaginatedResponse<ExternalLab>` |
| `POST` | `/api/external-laboratories` | `ExternalLabCreate` | `ExternalLab` |
| `GET` | `/api/external-laboratories/{id}` | — | `ExternalLab` |
| `PUT` | `/api/external-laboratories/{id}` | `ExternalLabUpdate` | `ExternalLab` |
| `DELETE` | `/api/external-laboratories/{id}` | — | `MessageResponse` |

### Seroteca — Tipos de Gradilla

| Método | URL | Body | Respuesta | Permiso |
|--------|-----|------|-----------|---------|
| `GET` | `/api/seroteca/tipos-gradilla` | — (query: search, active_only, skip, limit) | `PaginatedResponse<TipoGradilla>` | `Seroteca:ManageRackTypes` |
| `POST` | `/api/seroteca/tipos-gradilla` | `TipoGradillaCreate` | `TipoGradilla` | `Seroteca:ManageRackTypes` |
| `GET` | `/api/seroteca/tipos-gradilla/{tg_id}` | — | `TipoGradilla` | `Seroteca:ManageRackTypes` |
| `PATCH` | `/api/seroteca/tipos-gradilla/{tg_id}` | `TipoGradillaUpdate` | `TipoGradilla` | `Seroteca:ManageRackTypes` |
| `DELETE` | `/api/seroteca/tipos-gradilla/{tg_id}` | — | `{"detail":"Tipo de gradilla deleted"}` | `Seroteca:ManageRackTypes` |

### Seroteca — Crear Gradilla desde Tipo

| Método | URL | Body | Nota |
|--------|-----|------|------|
| `POST` | `/api/seroteca/serotecas/{s_id}/racks` | `{g_name, g_tipo_gradilla_id?}` | Si se envía `g_tipo_gradilla_id`, rows/cols se heredan automáticamente |