# Guía de Integración Frontend: Módulo de Remisiones (Angular)

Este documento describe cómo integrar el módulo de **Remisiones** del backend **LisCore** en una aplicación **Angular**. Cubre la estructura de servicios, modelos TypeScript, componentes sugeridos y flujo de trabajo de la UI.

---

## 1. Base URL y Autenticación

Todas las peticiones deben incluir el token JWT en el header `Authorization`:

```
Authorization: Bearer <token>
```

Realizar login contra `POST /api/users/login` para obtener el token.

---

## 2. Modelos TypeScript (Interfaces)

Crear los siguientes modelos en `src/app/core/models/remission.model.ts`:

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
  erl_created_at: string;  // ISO datetime
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
  rem_consecutive: string;        // REM-2026-1-0043
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
  // ... same fields as Remission
  origin_headquarter?: HeadquarterInfo | null;
  dest_headquarter?: HeadquarterInfo | null;
  dest_external_lab?: ExternalLab | null;
  created_by_user?: UserInfo | null;
  details: RemissionDetailItem[];
}

// ── Remission Detail Items ──────────────────────────────────────

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

// ── Ship / Receive / Cancel ────────────────────────────────────

export interface ShipRequest {
  rem_courier_name?: string;
  rem_temperature_courier?: string;
}

export interface ReceiveItemRequest {
  remd_id: number;
  remd_item_state: 2 | 3;           // 2=Conforme, 3=Rechazado
  remd_rejection_reason?: string;    // Obligatorio si estado es 3
}

export interface CancelRequest {
  notes?: string;
}

// ── Paginated Responses ────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface MessageResponse {
  success: boolean;
  message: string;
}

export interface RemissionCreatedResponse {
  success: boolean;
  rem_id: number;
  rem_consecutive: string;
  message: string;
}

export interface AddItemsResponse {
  success: boolean;
  items_count: number;
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
  Remission,
  RemissionDetail,
  RemissionCreate,
  RemissionCreatedResponse,
  AddItemsRequest,
  AddItemsResponse,
  ShipRequest,
  ReceiveItemRequest,
  CancelRequest,
  PaginatedResponse,
  MessageResponse,
} from '@core/models/remission.model';

@Injectable({ providedIn: 'root' })
export class RemissionService {
  private base = `${environment.apiUrl}/api/remissions`;

  constructor(private http: HttpClient) {}

  /** Crear cabecera de remisión */
  create(data: RemissionCreate): Observable<RemissionCreatedResponse> {
    return this.http.post<RemissionCreatedResponse>(this.base, data);
  }

  /** Listar remisiones con filtros */
  list(filters?: {
    state?: number;
    type?: string;
    origin_hq_id?: number;
    skip?: number;
    limit?: number;
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

  /** Obtener detalle completo (incluye items y logs) */
  getById(id: number): Observable<RemissionDetail> {
    return this.http.get<RemissionDetail>(`${this.base}/${id}`);
  }

  /** Agregar ítems a la remisión */
  addItems(remissionId: number, data: AddItemsRequest): Observable<AddItemsResponse> {
    return this.http.post<AddItemsResponse>(`${this.base}/${remissionId}/items`, data);
  }

  /** Eliminar un ítem de la remisión */
  removeItem(remissionId: number, detailId: number): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/${remissionId}/items/${detailId}`);
  }

  /** Enviar remisión */
  ship(remissionId: number, data: ShipRequest): Observable<MessageResponse> {
    return this.http.patch<MessageResponse>(`${this.base}/${remissionId}/ship`, data);
  }

  /** Recibir ítem en destino */
  receiveItem(remissionId: number, data: ReceiveItemRequest): Observable<MessageResponse> {
    return this.http.patch<MessageResponse>(`${this.base}/${remissionId}/receive-item`, data);
  }

  /** Cancelar remisión */
  cancel(remissionId: number, data?: CancelRequest): Observable<MessageResponse> {
    return this.http.patch<MessageResponse>(`${this.base}/${remissionId}/cancel`, data ?? {});
  }
}
```

---

## 4. Mapeo de Permisos RBAC

Cada endpoint requiere un permiso específico. Al construir la UI, oculta/muestra componentes según los permisos del rol del usuario:

| Permiso | Endpoint(s) | UI Componentes |
|---------|-------------|----------------|
| `Remissions:View` | GET list, GET byId, GET external labs | Tabla de remisiones, detalle, lista de labs externos |
| `Remissions:Create` | POST create, POST items, DELETE items | Formulario crear remisión, agregar/quitar ítems |
| `Remissions:Ship` | PATCH ship | Botón "Enviar" en detalle de remisión |
| `Remissions:Receive` | PATCH receive-item | Panel de recepción de ítems en destino |
| `Remissions:Cancel` | PATCH cancel | Botón "Cancelar" (visible solo en Pendiente) |
| `Remissions:ManageExternalLabs` | CRUD external labs | CRUD de laboratorios externos (módulo maestros) |

Obtener los permisos del usuario desde el endpoint `GET /api/users/me` o del servicio de autenticación.

---

## 5. Estructura de Componentes Sugerida

```
src/app/pages/remissions/
├── remission-list/                 # Listado paginado con filtros
│   ├── remission-list.component.ts
│   ├── remission-list.component.html
│   └── remission-list.component.scss
├── remission-create/               # Formulario de creación
│   ├── remission-create.component.ts
│   ├── remission-create.component.html
│   └── remission-create.component.scss
├── remission-detail/               # Vista detalle de una remisión
│   ├── remission-detail.component.ts
│   ├── remission-detail.component.html
│   └── remission-detail.component.scss
├── remission-receive/              # Panel de recepción de ítems
│   ├── remission-receive.component.ts
│   ├── remission-receive.component.html
│   └── remission-receive.component.scss
└── external-labs/                  # CRUD de laboratorios externos
    ├── external-lab-list.component.ts
    ├── external-lab-form.component.ts
    └── ...
```

---

## 6. Flujos de Pantalla

### 6.1 Pantalla: Listado de Remisiones

- **Ruta:** `/remissions`
- **Filtros:** Estado (dropdown con los 5 estados), Tipo (LOCAL/EXTERNAL), Sede Origen
- **Columnas sugeridas:** Consecutivo, Tipo, Origen, Destino, Estado, Fecha Creación, Acciones
- **Badge de estado** con colores:
  - `1 (Pendiente)` → Azul claro
  - `2 (Enviado)` → Naranja
  - `3 (Recibido Completo)` → Verde
  - `4 (Recibido con Novedad)` → Amarillo
  - `5 (Cancelado)` → Rojo
- **Acciones:**
  - Ver detalle (siempre)
  - Cancelar (solo si estado === 1 y permiso `Remissions:Cancel`)

### 6.2 Pantalla: Crear Remisión

- **Ruta:** `/remissions/create`
- **Campos:**
  1. **Tipo de Remisión** (radio buttons: LOCAL / EXTERNAL)
  2. **Sede Origen** (dropdown de `Headquarters`, cargar desde `GET /api/headquarters`)
  3. **Destino:**
     - Si LOCAL → Dropdown de `Headquarters` (excluir sede origen)
     - Si EXTERNAL → Dropdown de `ExternalReferenceLaboratories` activos
  4. **Observaciones** (textarea opcional)
- **Validaciones antes de submit:**
  - Para LOCAL: destino ≠ origen
  - Para EXTERNAL: laboratorio externo seleccionado
- **Al crear:** Redirigir a la pantalla de detalle de la nueva remisión para agregar ítems.

### 6.3 Pantalla: Detalle de Remisión

- **Ruta:** `/remissions/:id`
- **Secciones:**
  1. **Cabecera:** Consecutivo, tipo, origen, destino, estado, fechas, transportador, temperatura
  2. **Ítems (tabla):** Muestra (so_id), Examen (od_id), Estado del ítem
  3. **Historial de Estados:** Línea de tiempo con cambios de estado
- **Botones contextuales según estado y permisos:**
  - **Pendiente (1):** Agregar ítems, Quitar ítems, Enviar, Cancelar
  - **Enviado (2):** Recibir ítems (abre modal o panel de recepción)
  - **Recibido (3/4) o Cancelado (5):** Solo lectura

### 6.4 Panel: Agregar Ítems

- **Modal o sección en detalle** con:
  - Selector de `SamplesOrder` (so_id) con búsqueda por orden o paciente
  - Selector de `OrdersDetails` (od_id) filtrado por la muestra seleccionada
  - Botón "Agregar" (puede agregar varios pares)
  - Validación: el backend rechazará ítems duplicados en remisiones activas
- **POST** a `/api/remissions/{id}/items` con el array de pares

### 6.5 Panel: Enviar Remisión

- **Modal** con campos:
  - Transportador (`rem_courier_name`) — texto libre (ej: "Servientrega - Guía #123")
  - Temperatura (`rem_temperature_courier`) — texto libre (ej: "Refrigerado 2°C a 8°C")
- **PATCH** a `/api/remissions/{id}/ship`
- **Efecto:** El backend cambia el estado a "Enviado" y marca los `OrdersDetails` asociados como "En Tránsito" (od_state=90)

### 6.6 Panel: Recibir Ítem (en Destino)

- **Ruta o modal:** `/remissions/:id/receive`
- **Tabla de ítems** cargados con dos botones por ítem:
  - ✅ **Recibido Conforme** → PATCH `remd_item_state=2`
  - ❌ **Rechazado** → Muestra campo para `remd_rejection_reason` obligatorio, PATCH `remd_item_state=3`
- **Al procesar todos los ítems:** La cabecera se cierra automáticamente a "Recibido Completo" o "Recibido con Novedad"

### 6.7 CRUD: Laboratorios Externos

- **Ruta:** `/external-laboratories`
- **Formulario:** NIT, Nombre, Dirección, Teléfono, Email, Activo (toggle)
- **Listado:** Tabla con filtro de activos/inactivos
- **Endpoints:** CRUD estándar sobre `/api/external-laboratories`

---

## 7. Configuración de Rutas (app-routing.module.ts)

```typescript
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PermissionGuard } from '@core/guards/permission.guard';

const routes: Routes = [
  {
    path: 'remissions',
    canActivate: [PermissionGuard],
    data: { permission: 'Remissions:View' },
    children: [
      {
        path: '',
        component: RemissionListComponent,
      },
      {
        path: 'create',
        component: RemissionCreateComponent,
        canActivate: [PermissionGuard],
        data: { permission: 'Remissions:Create' },
      },
      {
        path: ':id',
        component: RemissionDetailComponent,
      },
      {
        path: ':id/receive',
        component: RemissionReceiveComponent,
        canActivate: [PermissionGuard],
        data: { permission: 'Remissions:Receive' },
      },
    ],
  },
  {
    path: 'external-laboratories',
    canActivate: [PermissionGuard],
    data: { permission: 'Remissions:View' },
    children: [
      { path: '', component: ExternalLabListComponent },
      { path: 'create', component: ExternalLabFormComponent, data: { permission: 'Remissions:ManageExternalLabs' } },
      { path: ':id/edit', component: ExternalLabFormComponent, data: { permission: 'Remissions:ManageExternalLabs' } },
    ],
  },
];
```

---

## 8. Consideraciones de UX

1. **Confirmaciones:** Antes de Enviar, Cancelar o Rechazar un ítem, mostrar diálogo de confirmación.
2. **Notificaciones:** Usar toast/snackbar para feedback de operaciones exitosas o errores.
3. **Loading states:** Mostrar spinners durante peticiones (crear, enviar, recibir).
4. **Manejo de errores 422:** El backend retorna `422 Unprocessable Entity` con el mensaje en `detail`. Mostrar este mensaje al usuario (ej: "El ítem ya está en otra remisión activa").
5. **Actualización en tiempo real:** Al recibir un ítem, refrescar la tabla de ítems y el estado de la cabecera (puede haber cambiado automáticamente).
6. **Badges de estado de ítems:**
   - Cargado (1) → Gris
   - Recibido Conforme (2) → Verde
   - Rechazado (3) → Rojo

---

## 9. Resumen de Endpoints API

| Método | URL | Body | Respuesta |
|--------|-----|------|-----------|
| `GET` | `/api/remissions` | — (query params opcionales) | `PaginatedResponse<Remission>` |
| `POST` | `/api/remissions` | `RemissionCreate` | `RemissionCreatedResponse` |
| `GET` | `/api/remissions/{id}` | — | `RemissionDetail` |
| `POST` | `/api/remissions/{id}/items` | `AddItemsRequest` | `AddItemsResponse` |
| `DELETE` | `/api/remissions/{id}/items/{detailId}` | — | `MessageResponse` |
| `PATCH` | `/api/remissions/{id}/ship` | `ShipRequest` | `MessageResponse` |
| `PATCH` | `/api/remissions/{id}/receive-item` | `ReceiveItemRequest` | `MessageResponse` |
| `PATCH` | `/api/remissions/{id}/cancel` | `CancelRequest` (opcional) | `MessageResponse` |
| `GET` | `/api/external-laboratories` | — | `PaginatedResponse<ExternalLab>` |
| `POST` | `/api/external-laboratories` | `ExternalLabCreate` | `ExternalLab` |
| `GET` | `/api/external-laboratories/{id}` | — | `ExternalLab` |
| `PUT` | `/api/external-laboratories/{id}` | `ExternalLabUpdate` | `ExternalLab` |
| `DELETE` | `/api/external-laboratories/{id}` | — | `MessageResponse` |