# Guía de Integración Frontend: Módulo de Seroteca & Tracking (Angular)

Este documento describe cómo integrar el módulo de **Seroteca & Tracking** del backend **LisCore** en una aplicación **Angular**. Cubre los endpoints REST, modelos TypeScript, servicios, componentes sugeridos y flujos de trabajo.

---

## 1. Base URL y Autenticación

Todas las peticiones deben incluir el token JWT en el header `Authorization`:

```
Authorization: Bearer <token>
```

**Prefijo base:** `{base_url}/api/v1/seroteca/...`

Ejemplo:
```
http://localhost:8000/api/v1/seroteca/serotecas
```

---

## 2. Modelos TypeScript (`seroteca.model.ts`)

Crear en `src/app/core/models/seroteca.model.ts`:

```typescript
// ── Paginación Genérica ────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface MessageResponse {
  detail: string;
}

// ── Entidades Relacionadas (lookups) ───────────────────────────

export interface LocationBasic {
  loc_id: number;
  loc_name?: string;
}

export interface HeadquarterBasic {
  id: number;
  name?: string;
}

export interface UserBasic {
  usr_id: number;
  usr_first_name?: string;
  usr_last_name?: string;
}

export interface PatientBasic {
  pt_id: number;
  pt_firts_name?: string;
  pt_middle_name?: string;
  pt_last_name?: string;
  pt_second_last_name?: string;
  full_name?: string;         // computed field
}

export interface SampleTypeBasic {
  st_id: number;
  st_sufix?: number;
}

export interface OrderBasic {
  o_id: number;
  o_number?: string;
  o_date?: string;            // date ISO
  patient?: PatientBasic;
}

export interface SampleOrderBasic {
  so_id: number;
  so_barcode?: string;
  order?: OrderBasic;
  sample_type?: SampleTypeBasic;
  order_number_with_suffix?: string;  // computed: "ORD-123-1"
}

// ── Seroteca ───────────────────────────────────────────────────

export interface Seroteca {
  s_id: number;
  s_name: string;
  s_description?: string;
  s_location_id?: number;
  s_headquarter_id?: number;
  location?: LocationBasic;
  headquarter?: HeadquarterBasic;
  s_active: boolean;
  s_created_at?: string;
  s_updated_at?: string;
}

export interface SerotecaCreate {
  s_name: string;
  s_description?: string;
  s_location_id?: number;
  s_headquarter_id?: number;
  s_active?: boolean;         // default true
}

export interface SerotecaUpdate {
  s_name?: string;
  s_description?: string;
  s_location_id?: number;
  s_headquarter_id?: number;
  s_active?: boolean;
}

// ── Tipos de Gradilla (templates) ──────────────────────────────

export interface TipoGradilla {
  tg_id: number;
  tg_name: string;
  tg_rows: number;            // 1-100
  tg_cols: number;            // 1-100
  tg_storage_days: number;    // 1-3650
  tg_active: boolean;
  tg_created_at?: string;
  tg_updated_at?: string;
}

export interface TipoGradillaCreate {
  tg_name: string;
  tg_rows: number;
  tg_cols: number;
  tg_storage_days: number;
}

export interface TipoGradillaUpdate {
  tg_name?: string;
  tg_rows?: number;
  tg_cols?: number;
  tg_storage_days?: number;
  tg_active?: boolean;
}

// ── Gradillas (racks) ──────────────────────────────────────────

export interface Gradilla {
  g_id: number;
  g_name: string;
  g_seroteca_id: number;
  g_rows: number;
  g_cols: number;
  g_active: boolean;
  g_created_by?: number;
  g_created_at?: string;
  g_updated_at?: string;
}

export interface GradillaCreate {
  g_name: string;
  g_seroteca_id: number;
  g_tipo_gradilla_id?: number;   // opcional — hereda rows/cols del tipo
  g_rows?: number;               // opcional si se usó g_tipo_gradilla_id
  g_cols?: number;               // opcional si se usó g_tipo_gradilla_id
}

export interface GradillaUpdate {
  g_name?: string;
  g_active?: boolean;
}

// ── Posiciones (celdas) ────────────────────────────────────────

export interface GradillaPosicion {
  gp_id: number;
  gp_gradilla_id: number;
  gp_row: number;
  gp_col: number;
  gp_sample_id?: number;
  gp_occupied: boolean;
  gp_stored_at?: string;
  gp_stored_by_id?: number;
  sample?: SampleOrderBasic;    // viene en GET con posiciones
}

/** Gradilla con sus posiciones (respuesta de GET /racks/{g_id}) */
export interface GradillaWithPositions extends Gradilla {
  positions: GradillaPosicion[];
}

// ── Tracking (SamplesLog) ──────────────────────────────────────

/** 0=Recibida  1=En proceso  2=Almacenada  3=Retirada  4=Descartada */
export type SampleState = 0 | 1 | 2 | 3 | 4;

export const SampleStateLabels: Record<SampleState, string> = {
  0: 'Recibida',
  1: 'En proceso',
  2: 'Almacenada',
  3: 'Retirada',
  4: 'Descartada',
};

export interface SampleLogCreate {
  barcode: string;             // so_barcode de la muestra
  log_state: SampleState;
  log_location_id?: number;
  log_observation?: string;
}

export interface SampleLogResponse {
  sl_id: number;
  log_sample_order_id?: number;
  log_state?: SampleState;
  log_location_id?: number;
  location?: LocationBasic;
  log_observation?: string;
  log_user_id?: number;
  user?: UserBasic;
  log_create_at?: string;      // formateado: dd/MM/yyyy hh:mm AM/PM
  location_name?: string;      // enriquecido
  headquarter_name?: string;   // enriquecido
}

// ── Storage Actions ────────────────────────────────────────────

export interface AutoStoreRequest {
  barcode: string;             // so_barcode
  g_id: number;                // rack ID
}

export interface ManualStoreRequest {
  barcode: string;             // so_barcode
}
```

---

## 3. Servicios Angular

### 3.1 Seroteca Service (`seroteca.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  Seroteca, SerotecaCreate, SerotecaUpdate,
  PaginatedResponse, MessageResponse,
} from '@core/models/seroteca.model';

@Injectable({ providedIn: 'root' })
export class SerotecaService {
  private base = `${environment.apiUrl}/api/seroteca/serotecas`;

  constructor(private http: HttpClient) {}

  /** Listar serotecas con filtros */
  list(filters?: {
    skip?: number;
    limit?: number;
    search?: string;
    active_only?: boolean;
    headquarter_id?: number;
  }): Observable<PaginatedResponse<Seroteca>> {
    let params = new HttpParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params = params.set(key, String(value));
        }
      });
    }
    return this.http.get<PaginatedResponse<Seroteca>>(this.base, { params });
  }

  getById(s_id: number): Observable<Seroteca> {
    return this.http.get<Seroteca>(`${this.base}/${s_id}`);
  }

  create(data: SerotecaCreate): Observable<Seroteca> {
    return this.http.post<Seroteca>(this.base, data);
  }

  update(s_id: number, data: SerotecaUpdate): Observable<Seroteca> {
    return this.http.patch<Seroteca>(`${this.base}/${s_id}`, data);
  }

  delete(s_id: number): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/${s_id}`);
  }
}
```

### 3.2 Gradilla Service (`gradilla.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  Gradilla, GradillaCreate, GradillaUpdate,
  GradillaWithPositions, GradillaPosicion,
  AutoStoreRequest, ManualStoreRequest,
  PaginatedResponse, MessageResponse,
} from '@core/models/seroteca.model';

@Injectable({ providedIn: 'root' })
export class GradillaService {
  private base = `${environment.apiUrl}/api/seroteca`;

  constructor(private http: HttpClient) {}

  /** Crear gradilla en una seroteca */
  create(s_id: number, data: GradillaCreate): Observable<Gradilla> {
    return this.http.post<Gradilla>(`${this.base}/serotecas/${s_id}/racks`, data);
  }

  /** Listar gradillas de una seroteca */
  list(s_id: number, filters?: {
    skip?: number; limit?: number; search?: string;
  }): Observable<PaginatedResponse<Gradilla>> {
    let params = new HttpParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params = params.set(key, String(value));
        }
      });
    }
    return this.http.get<PaginatedResponse<Gradilla>>(`${this.base}/serotecas/${s_id}/racks`, { params });
  }

  /** Obtener gradilla con sus posiciones */
  getById(g_id: number): Observable<GradillaWithPositions> {
    return this.http.get<GradillaWithPositions>(`${this.base}/racks/${g_id}`);
  }

  update(g_id: number, data: GradillaUpdate): Observable<Gradilla> {
    return this.http.patch<Gradilla>(`${this.base}/racks/${g_id}`, data);
  }

  delete(g_id: number): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/racks/${g_id}`);
  }

  /** Auto-almacenar muestra (busca primera posición libre) */
  autoStore(data: AutoStoreRequest): Observable<GradillaPosicion> {
    return this.http.post<GradillaPosicion>(`${this.base}/samples/store`, data);
  }

  /** Almacenar muestra en posición específica */
  manualStore(gp_id: number, data: ManualStoreRequest): Observable<GradillaPosicion> {
    return this.http.post<GradillaPosicion>(`${this.base}/positions/${gp_id}/store`, data);
  }

  /** Liberar posición (retirar muestra) */
  releasePosition(gp_id: number): Observable<GradillaPosicion> {
    return this.http.delete<GradillaPosicion>(`${this.base}/positions/${gp_id}/release`);
  }
}
```

### 3.3 Tipo de Gradilla Service (`tipo-gradilla.service.ts`)

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
    skip?: number;
    limit?: number;
    search?: string;
    active_only?: boolean;
  }): Observable<PaginatedResponse<TipoGradilla>> {
    let params = new HttpParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
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

### 3.4 Tracking Service (`tracking.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  SampleLogCreate, SampleLogResponse,
  PaginatedResponse,
} from '@core/models/seroteca.model';

@Injectable({ providedIn: 'root' })
export class TrackingService {
  private base = `${environment.apiUrl}/api/seroteca`;

  constructor(private http: HttpClient) {}

  /** Registrar evento de seguimiento en una muestra */
  logEvent(data: SampleLogCreate): Observable<any> {
    return this.http.post(`${this.base}/samples/track`, data);
  }

  /** Consultar historial de trazabilidad de una muestra por barcode */
  getHistory(barcode: string, skip = 0, limit = 50): Observable<PaginatedResponse<SampleLogResponse>> {
    const params = new HttpParams()
      .set('skip', String(skip))
      .set('limit', String(limit));
    return this.http.get<PaginatedResponse<SampleLogResponse>>(
      `${this.base}/samples/${barcode}/history`,
      { params }
    );
  }
}
```

---

## 4. Mapeo de Permisos RBAC

| Permiso | Endpoint(s) | UI Componentes |
|---------|-------------|----------------|
| `Tracking:Log` | POST `/samples/track` | Botón "Registrar evento" en detalle de muestra |
| `Tracking:Read` | GET `/samples/{barcode}/history` | Panel de historial de trazabilidad |
| `Seroteca:List` | GET `/serotecas` | Tabla/listado de serotecas |
| `Seroteca:Create` | POST `/serotecas` | Formulario crear seroteca |
| `Seroteca:GetOne` | GET `/serotecas/{s_id}` | Vista detalle de seroteca |
| `Seroteca:Update` | PATCH `/serotecas/{s_id}` | Editar seroteca |
| `Seroteca:Delete` | DELETE `/serotecas/{s_id}` | Eliminar seroteca |
| `Seroteca:ManageRacks` | CRUD `/racks`, `/racks/{g_id}` | Crear/editar/eliminar gradillas, ver posiciones |
| `Seroteca:ManageRackTypes` | CRUD `/tipos-gradilla` | CRUD de tipos de gradilla (templates) |
| `Seroteca:StoreSample` | POST `/samples/store`, POST `/positions/{gp_id}/store`, DELETE `/positions/{gp_id}/release` | Almacenar/retirar muestras |

---

## 5. Estructura de Componentes Sugerida

```
src/app/pages/seroteca/
├── seroteca-list/                    # Listado paginado de serotecas
│   ├── seroteca-list.component.ts
│   ├── seroteca-list.component.html
│   └── seroteca-list.component.scss
├── seroteca-form/                    # Formulario crear/editar seroteca
│   ├── seroteca-form.component.ts
│   ├── seroteca-form.component.html
│   └── seroteca-form.component.scss
├── seroteca-detail/                  # Detalle de seroteca con sus gradillas
│   ├── seroteca-detail.component.ts
│   ├── seroteca-detail.component.html
│   └── seroteca-detail.component.scss
├── gradilla-positions/               # Vista de posiciones de una gradilla (grid)
│   ├── gradilla-positions.component.ts
│   ├── gradilla-positions.component.html
│   └── gradilla-positions.component.scss
├── tipo-gradilla-list/               # Listado de tipos de gradilla
│   └── ...
├── tipo-gradilla-form/               # Formulario tipo de gradilla
│   └── ...
└── sample-tracking/                  # Historial de trazabilidad de una muestra
    ├── sample-tracking.component.ts
    ├── sample-tracking.component.html
    └── sample-tracking.component.scss
```

---

## 6. Flujos de Pantalla

### 6.1 Listado de Serotecas

- **Ruta:** `/seroteca`
- **Filtros:** Búsqueda por nombre, Solo activos, Sede (headquarter_id)
- **Columnas:** Nombre, Descripción, Ubicación, Sede, Activo, Acciones
- **Acciones:** Ver detalle, Editar, Eliminar (desactivar)
- **Permiso requerido:** `Seroteca:List`

### 6.2 Crear / Editar Seroteca

- **Ruta:** `/seroteca/create` o `/seroteca/:id/edit`
- **Campos:**
  - **Nombre** (requerido)
  - **Descripción** (textarea opcional)
  - **Ubicación** (dropdown de `locations`)
  - **Sede** (dropdown de `headquarters`)
  - **Activo** (toggle, default true)
- **Endpoints:**
  - `POST /api/seroteca/serotecas` → Crear
  - `PATCH /api/seroteca/serotecas/{s_id}` → Actualizar
- **Permiso requerido:** `Seroteca:Create` / `Seroteca:Update`

### 6.3 Detalle de Seroteca

- **Ruta:** `/seroteca/:id`
- **Secciones:**
  1. **Datos de la seroteca:** Nombre, descripción, ubicación, sede, estado
  2. **Gradillas (tabla):** Lista de gradillas dentro de esta seroteca con columnas: Nombre, Filas, Columnas, Activo, Acciones
     - Acciones: Ver posiciones, Editar, Eliminar
     - Botón "Nueva Gradilla" (permiso `Seroteca:ManageRacks`)
  3. **Modal / Formulario Nueva Gradilla:**
     - Nombre
     - Tipo de Gradilla (dropdown opcional — si se selecciona, filas/cols se heredan y deshabilitan)
     - Filas (manual si no hay tipo)
     - Columnas (manual si no hay tipo)
- **Permiso requerido:** `Seroteca:GetOne`

### 6.4 Vista de Posiciones de una Gradilla (Grid)

- **Ruta:** `/seroteca/gradillas/:g_id`
- **Vista principal:** Grid visual de `g_rows × g_cols` celdas
  - **Celda vacía** (gp_occupied = false) → Color gris claro, muestra coordenadas (fila, columna)
  - **Celda ocupada** (gp_occupied = true) → Color verde, muestra `so_barcode` o `order_number_with_suffix`, tooltip con datos de la muestra
- **Acciones por celda:**
  - **Celda vacía:** Botón "Almacenar muestra aquí" → abre modal para escanear/ingresar barcode → `POST /api/seroteca/positions/{gp_id}/store`
  - **Celda ocupada:** Botón "Retirar muestra" → confirmación → `DELETE /api/seroteca/positions/{gp_id}/release`
- **Acción global:** Botón "Auto-almacenar" → modal con input de barcode → `POST /api/seroteca/samples/store` con `{barcode, g_id}`
- **Permisos requeridos:**
  - Ver: `Seroteca:ManageRacks`
  - Almacenar/Retirar: `Seroteca:StoreSample`

### 6.5 Tipos de Gradilla — Listado

- **Ruta:** `/seroteca/tipos-gradilla`
- **Filtros:** Búsqueda por nombre, Solo activos
- **Columnas:** Nombre, Filas, Columnas, Días almacenamiento, Activo, Acciones
- **Acciones:** Crear, Editar, Eliminar
- **Permiso requerido:** `Seroteca:ManageRackTypes`

### 6.6 Tipos de Gradilla — Formulario

- **Ruta:** `/seroteca/tipos-gradilla/create` o `/seroteca/tipos-gradilla/:id/edit`
- **Campos:**
  - **Nombre** (ej: "Gradilla 10x10", "Positivos VPH", "Gradilla 5x10")
  - **Nro Filas** (numérico, 1-100)
  - **Nro Columnas** (numérico, 1-100)
  - **Días de almacenamiento** (numérico, 1-3650, default 30)
- **Endpoints:**
  - `POST /api/seroteca/tipos-gradilla` → Crear
  - `PATCH /api/seroteca/tipos-gradilla/{tg_id}` → Actualizar
  - `DELETE /api/seroteca/tipos-gradilla/{tg_id}` → Eliminar
- **Permiso requerido:** `Seroteca:ManageRackTypes`

### 6.7 Tracking — Historial de Muestra

- **Ruta:** `/seroteca/samples/:barcode/history`
- **Vista:** Línea de tiempo (timeline) con eventos de la muestra
  - Cada evento muestra: Fecha/hora, Estado, Ubicación, Observación, Usuario
- **Badges de estado:**
  - 0 (Recibida) → Azul
  - 1 (En proceso) → Naranja
  - 2 (Almacenada) → Verde
  - 3 (Retirada) → Púrpura
  - 4 (Descartada) → Rojo
- **Paginación:** skip/limit estándar
- **Permiso requerido:** `Tracking:Read`

### 6.8 Tracking — Registrar Evento

- **Contexto:** Desde el detalle de una muestra o desde la vista de posiciones
- **Modal con campos:**
  - **Barcode** (pre-llenado si viene del contexto)
  - **Estado** (dropdown: Recibida, En proceso, Almacenada, Retirada, Descartada)
  - **Ubicación** (dropdown opcional de locations)
  - **Observación** (textarea opcional)
- **Endpoint:** `POST /api/seroteca/samples/track`
- **Permiso requerido:** `Tracking:Log`

---

## 7. Configuración de Rutas (app-routing.module.ts)

```typescript
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PermissionGuard } from '@core/guards/permission.guard';

const routes: Routes = [
  // ── Seroteca ────────────────────────────────────────────────
  {
    path: 'seroteca',
    canActivate: [PermissionGuard],
    data: { permission: 'Seroteca:List' },
    children: [
      { path: '', component: SerotecaListComponent },
      {
        path: 'create',
        component: SerotecaFormComponent,
        data: { permission: 'Seroteca:Create' },
      },
      {
        path: ':id',
        component: SerotecaDetailComponent,
        data: { permission: 'Seroteca:GetOne' },
      },
      {
        path: ':id/edit',
        component: SerotecaFormComponent,
        data: { permission: 'Seroteca:Update' },
      },
    ],
  },

  // ── Tipos de Gradilla ───────────────────────────────────────
  {
    path: 'seroteca/tipos-gradilla',
    canActivate: [PermissionGuard],
    data: { permission: 'Seroteca:ManageRackTypes' },
    children: [
      { path: '', component: TipoGradillaListComponent },
      {
        path: 'create',
        component: TipoGradillaFormComponent,
      },
      {
        path: ':id/edit',
        component: TipoGradillaFormComponent,
      },
    ],
  },

  // ── Gradillas (racks) ───────────────────────────────────────
  {
    path: 'seroteca/gradillas/:g_id',
    component: GradillaPositionsComponent,
    canActivate: [PermissionGuard],
    data: { permission: 'Seroteca:ManageRacks' },
  },

  // ── Tracking de Muestra ─────────────────────────────────────
  {
    path: 'seroteca/samples/:barcode/history',
    component: SampleTrackingComponent,
    canActivate: [PermissionGuard],
    data: { permission: 'Tracking:Read' },
  },
];
```

---

## 8. Consideraciones de UX

### 8.1 Grid de Posiciones (Gradilla)

- Renderizar un grid CSS de `g_cols` columnas × `g_rows` filas
- Cada celda debe mostrar:
  - **Vacía:** Número de posición (ej: "A1", "B3") en texto tenue
  - **Ocupada:** Barcode o número de orden, con tooltip al hacer hover mostrando: paciente, tipo de muestra, fecha de almacenamiento
- **Click en celda vacía:** Abre modal para ingresar barcode (o escanear con lector de códigos)
- **Click en celda ocupada:** Abre modal con datos de la muestra + botón "Retirar"
- **Colores sugeridos:**
  - Celda vacía: `#f5f5f5` (gris claro)
  - Celda ocupada: `#e8f5e9` (verde claro) con borde `#4caf50`
  - Celda hover: `#e3f2fd` (azul claro)

### 8.2 Auto-almacenamiento

- Campo de texto para ingresar/escanear barcode
- Dropdown para seleccionar gradilla (racks de la seroteca actual)
- El backend busca automáticamente la primera posición libre (por fila, luego columna)
- Si no hay posiciones libres, mostrar error "Gradilla llena"

### 8.3 Crear Gradilla desde Tipo

- Dropdown de "Tipo de Gradilla" (cargar tipos activos desde `GET /api/seroteca/tipos-gradilla?active_only=true`)
- Al seleccionar un tipo, los campos `g_rows` y `g_cols` se auto-completan y se deshabilitan
- Si no se selecciona tipo, los campos rows/cols son editables manualmente

### 8.4 Tracking de Muestras

- El historial se muestra como timeline vertical con íconos por estado
- Implementar scroll infinito o paginación
- Botón "Registrar evento" visible si el usuario tiene permiso `Tracking:Log`

### 8.5 General

- **Confirmaciones:** Antes de eliminar serotecas, gradillas, tipos de gradilla, o retirar muestras, mostrar diálogo de confirmación
- **Notificaciones:** Usar toast/snackbar para feedback
- **Loading states:** Spinners durante peticiones
- **Validaciones:** El backend retorna `422` con mensaje en `detail` — mostrar al usuario
- **Refresco automático:** Al almacenar/retirar una muestra, refrescar el grid de posiciones

---

## 9. Resumen de Endpoints API

### Serotecas

| Método | URL | Body | Respuesta | Permiso |
|--------|-----|------|-----------|---------|
| `POST` | `/seroteca/serotecas` | `SerotecaCreate` | `Seroteca` | `Seroteca:Create` |
| `GET` | `/seroteca/serotecas` | — (query: skip, limit, search, active_only, headquarter_id) | `PaginatedResponse<Seroteca>` | `Seroteca:List` |
| `GET` | `/seroteca/serotecas/{s_id}` | — | `Seroteca` | `Seroteca:GetOne` |
| `PATCH` | `/seroteca/serotecas/{s_id}` | `SerotecaUpdate` | `Seroteca` | `Seroteca:Update` |
| `DELETE` | `/seroteca/serotecas/{s_id}` | — | `{"detail":"..."}` | `Seroteca:Delete` |

### Gradillas (Racks)

| Método | URL | Body | Respuesta | Permiso |
|--------|-----|------|-----------|---------|
| `POST` | `/seroteca/serotecas/{s_id}/racks` | `GradillaCreate` | `Gradilla` | `Seroteca:ManageRacks` |
| `GET` | `/seroteca/serotecas/{s_id}/racks` | — (query: skip, limit, search) | `PaginatedResponse<Gradilla>` | `Seroteca:ManageRacks` |
| `GET` | `/seroteca/racks/{g_id}` | — | `GradillaWithPositions` | `Seroteca:ManageRacks` |
| `PATCH` | `/seroteca/racks/{g_id}` | `GradillaUpdate` | `Gradilla` | `Seroteca:ManageRacks` |
| `DELETE` | `/seroteca/racks/{g_id}` | — | `{"detail":"..."}` | `Seroteca:ManageRacks` |

### Tipos de Gradilla

| Método | URL | Body | Respuesta | Permiso |
|--------|-----|------|-----------|---------|
| `POST` | `/seroteca/tipos-gradilla` | `TipoGradillaCreate` | `TipoGradilla` | `Seroteca:ManageRackTypes` |
| `GET` | `/seroteca/tipos-gradilla` | — (query: skip, limit, search, active_only) | `PaginatedResponse<TipoGradilla>` | `Seroteca:ManageRackTypes` |
| `GET` | `/seroteca/tipos-gradilla/{tg_id}` | — | `TipoGradilla` | `Seroteca:ManageRackTypes` |
| `PATCH` | `/seroteca/tipos-gradilla/{tg_id}` | `TipoGradillaUpdate` | `TipoGradilla` | `Seroteca:ManageRackTypes` |
| `DELETE` | `/seroteca/tipos-gradilla/{tg_id}` | — | `{"detail":"Tipo de gradilla deleted"}` | `Seroteca:ManageRackTypes` |

### Storage (Almacenamiento)

| Método | URL | Body | Respuesta | Permiso |
|--------|-----|------|-----------|---------|
| `POST` | `/seroteca/samples/store` | `AutoStoreRequest` | `GradillaPosicion` | `Seroteca:StoreSample` |
| `POST` | `/seroteca/positions/{gp_id}/store` | `ManualStoreRequest` | `GradillaPosicion` | `Seroteca:StoreSample` |
| `DELETE` | `/seroteca/positions/{gp_id}/release` | — | `GradillaPosicion` | `Seroteca:StoreSample` |

### Tracking

| Método | URL | Body | Respuesta | Permiso |
|--------|-----|------|-----------|---------|
| `POST` | `/seroteca/samples/track` | `SampleLogCreate` | — | `Tracking:Log` |
| `GET` | `/seroteca/samples/{barcode}/history` | — (query: skip, limit) | `PaginatedResponse<SampleLogResponse>` | `Tracking:Read` |