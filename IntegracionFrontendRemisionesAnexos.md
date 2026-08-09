# Guía de Integración Frontend: Órdenes Remitidas y Resultados Anexos (Angular)

Este documento describe cómo integrar en Angular las nuevas funcionalidades del dominio **Remisiones** del backend **LisCore** para:

1. Listar, agrupadas por orden con sus estudios remitidos como JSON hijo, las órdenes que tienen al menos un estudio configurado como remitido a un **laboratorio de referencia externo real** (`StudiesLab.external_lab_id`, excluyendo el centinela `LOCAL` usado para estudios procesados en la propia sede), con filtros de fecha, de resultados anexos y de laboratorio externo.
2. Cargar el PDF de resultados anexos de una orden, **por laboratorio de referencia externo específico**, marcando automáticamente solo las pruebas remitidas a ESE laboratorio como `PDF ANEXO`.

> **Importante:** esta búsqueda es directamente sobre los estudios de la orden (`OrdersDetails` → `StudiesLab`), **no** sobre el módulo logístico de Remisiones (`Remissions`/`RemissionDetails`). Una orden aparece en este listado apenas tiene un estudio cuyo maestro está configurado con un laboratorio externo real, sin importar si ya se creó o no una remisión física para transportarla.
>
> **La carga de anexos es por laboratorio, no por orden completa.** Si una orden tiene estudios remitidos a dos laboratorios distintos (ejemplo real de la base de datos: la orden `0308260032` tiene 6 estudios remitidos a **CLINIZAD** y 1 estudio [`ALVIVORUSS`] remitido a **LAB. COLCAN**), cargar el PDF de CLINIZAD **no** marca el estudio de LAB. COLCAN — ese queda pendiente de su propio PDF.

> Complementa la guía general [`IntegracionFrontendRemisiones.md`](./IntegracionFrontendRemisiones.md) (creación de remisiones, envío, recepción de ítems, laboratorios externos). Aquí solo se documentan los 2 endpoints nuevos.

---

## 1. Base URL y Autenticación

Todas las peticiones deben incluir el token JWT:

```
Authorization: Bearer <token>
```

**Prefijo base:** `{base_url}/api/remissions/...`

---

## 2. Resumen de Endpoints

| # | Método | Endpoint | Permiso RBAC | Uso |
|---|--------|----------|---------------|-----|
| 1 | GET | `/api/remissions/orders?date_from=&date_to=&has_annexed_results=&external_lab_id=&search=&skip=&limit=` | `Remissions:View` | Listar órdenes con estudios remitidos (estudios anidados) |
| 2 | POST | `/api/remissions/orders/{order_id}/annexed-results` (multipart: `external_lab_id`, `file`) | `Remissions:UploadAnnexedResult` | Cargar PDF anexo **para un laboratorio específico** y marcar solo sus pruebas como `PDF ANEXO` |

Ambos filtros de fecha son opcionales y aplican sobre la fecha de la orden (`o_date`, formato `YYYY-MM-DD`). `skip`/`limit` paginan a **nivel de orden** (no de estudio).

---

## 3. Modelos TypeScript (`remission-annexed.model.ts`)

Crear en `src/app/core/models/remission-annexed.model.ts`:

```typescript
// ── Filtros de listado ───────────────────────────────────────────

export interface OrdersWithRemittedStudiesFilter {
  date_from?: string;              // 'YYYY-MM-DD'
  date_to?: string;                // 'YYYY-MM-DD'
  has_annexed_results?: boolean;   // true = solo con anexos, false = solo sin anexos
  external_lab_id?: number;
  search?: string;                 // busca en o_number, pt_Number_document y nombre de estudio (parcial, insensible a mayúsculas)
  skip?: number;
  limit?: number;
}

// ── Estudio remitido (JSON hijo) ────────────────────────────────────
// ar_file_status es específico del laboratorio externo DE ESE ESTUDIO:
// dos estudios de la misma orden remitidos a laboratorios distintos pueden
// tener estados de anexo distintos.

export type ArFileStatus = 'Cargado' | 'Sin resultado Anexo';

export interface RemittedStudyChild {
  order_detail_id: number;
  study_code?: string;
  study_name?: string;
  external_lab_id?: number;
  external_lab_name?: string;
  ar_file_status: ArFileStatus;
}

// ── Orden con estudios remitidos ────────────────────────────────────

export interface OrderWithRemittedStudiesItem {
  o_id: number;
  o_number?: string;
  fecha_ingreso?: string;          // ISO datetime (Orders.o_created_at)
  patient_full_name?: string;
  pt_number_document?: string;
  estudios_remitidos: RemittedStudyChild[];
}

export interface OrdersWithRemittedStudiesListResponse {
  items: OrderWithRemittedStudiesItem[];
  total: number;   // cantidad de ÓRDENES, no de estudios
  skip: number;
  limit: number;
}

// ── Carga de PDF anexo (por laboratorio) ────────────────────────────

export interface UploadRemittedAnnexedResponse {
  success: boolean;
  ar_id: number;
  ar_file: string;
  order_id: number;
  external_lab_id: number;
  external_lab_name?: string;
  labs_marked: number[];             // IDs de Laboratories marcados como 'PDF ANEXO' (solo de ese laboratorio)
  labs_skipped_validated: number[];  // IDs que no se tocaron por ya estar Validados
  message: string;
}
```

---

## 4. Servicio Angular (`remission-annexed.service.ts`)

Crear en `src/app/core/services/remission-annexed.service.ts`:

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  OrdersWithRemittedStudiesFilter,
  OrdersWithRemittedStudiesListResponse,
  UploadRemittedAnnexedResponse,
} from '@core/models/remission-annexed.model';

@Injectable({ providedIn: 'root' })
export class RemissionAnnexedService {
  private base = `${environment.apiUrl}/api/remissions`;

  constructor(private http: HttpClient) {}

  /** Lista órdenes con al menos un estudio remitido, con sus estudios anidados */
  listOrdersWithRemittedStudies(
    filter?: OrdersWithRemittedStudiesFilter,
  ): Observable<OrdersWithRemittedStudiesListResponse> {
    let params = new HttpParams();
    if (filter) {
      Object.entries(filter).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params = params.set(key, String(value));
        }
      });
    }
    return this.http.get<OrdersWithRemittedStudiesListResponse>(`${this.base}/orders`, { params });
  }

  /**
   * Sube el PDF anexo de una orden PARA UN LABORATORIO ESPECÍFICO y marca
   * solo las pruebas remitidas a ese laboratorio como 'PDF ANEXO'. Los
   * estudios de la misma orden remitidos a otro laboratorio no se ven afectados.
   */
  uploadAnnexedResult(
    orderId: number,
    externalLabId: number,
    file: File,
  ): Observable<UploadRemittedAnnexedResponse> {
    const formData = new FormData();
    formData.append('external_lab_id', String(externalLabId));
    formData.append('file', file, file.name);
    return this.http.post<UploadRemittedAnnexedResponse>(
      `${this.base}/orders/${orderId}/annexed-results`,
      formData,
    );
  }
}
```

> No es necesario fijar el header `Content-Type` al enviar `FormData`: `HttpClient` lo genera automáticamente con el `boundary` correcto.

---

## 5. Estructura de Componentes Sugerida

```
remissions/
└── remitted-orders/
    ├── remitted-orders-list/
    │   └── remitted-orders-list.component.ts     # Tabla de órdenes + estudios anidados + filtros
    └── upload-annexed-modal/
        └── upload-annexed-modal.component.ts      # Modal de carga de PDF (por laboratorio)
```

### 5.1 Listado con filtros (`remitted-orders-list.component.ts`)

```typescript
import { Component, OnInit } from '@angular/core';
import { RemissionAnnexedService } from '@core/services/remission-annexed.service';
import {
  OrderWithRemittedStudiesItem,
  OrdersWithRemittedStudiesFilter,
} from '@core/models/remission-annexed.model';

@Component({
  selector: 'app-remitted-orders-list',
  templateUrl: './remitted-orders-list.component.html',
})
export class RemittedOrdersListComponent implements OnInit {
  items: OrderWithRemittedStudiesItem[] = [];
  total = 0;
  loading = false;

  filter: OrdersWithRemittedStudiesFilter = { skip: 0, limit: 20 };

  // Opciones del filtro "resultados anexos": undefined = todas
  hasAnnexedOptions = [
    { label: 'Todas', value: undefined },
    { label: 'Con resultados anexos', value: true },
    { label: 'Sin resultados anexos', value: false },
  ];

  constructor(private remissionAnnexedService: RemissionAnnexedService) {}

  ngOnInit(): void {
    this.search();
  }

  search(): void {
    this.loading = true;
    this.remissionAnnexedService.listOrdersWithRemittedStudies(this.filter).subscribe({
      next: (res) => {
        this.items = res.items;
        this.total = res.total;
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  onFilterChange(): void {
    this.filter.skip = 0;
    this.search();
  }

  onPageChange(skip: number): void {
    this.filter.skip = skip;
    this.search();
  }
}
```

```html
<div class="filters-bar">
  <label>
    Buscar
    <input type="text" placeholder="N° de orden, documento del paciente o nombre de estudio"
           [(ngModel)]="filter.search" (ngModelChange)="onFilterChange()" />
  </label>
  <label>
    Fecha Inicial
    <input type="date" [(ngModel)]="filter.date_from" (change)="onFilterChange()" />
  </label>
  <label>
    Fecha Final
    <input type="date" [(ngModel)]="filter.date_to" (change)="onFilterChange()" />
  </label>
  <label>
    Resultados Anexos
    <select [(ngModel)]="filter.has_annexed_results" (change)="onFilterChange()">
      <option *ngFor="let opt of hasAnnexedOptions" [ngValue]="opt.value">{{ opt.label }}</option>
    </select>
  </label>
  <label>
    Laboratorio Externo
    <app-external-lab-select [(value)]="filter.external_lab_id" (valueChange)="onFilterChange()">
    </app-external-lab-select>
  </label>
</div>

<!-- Una fila por orden, con sus estudios remitidos como tabla hija -->
<table class="table">
  <thead>
    <tr>
      <th>Orden</th>
      <th>Fecha Ingreso</th>
      <th>Paciente</th>
      <th>Documento</th>
      <th>Estudios Remitidos</th>
    </tr>
  </thead>
  <tbody>
    <tr *ngFor="let order of items">
      <td>{{ order.o_number }}</td>
      <td>{{ order.fecha_ingreso | date: 'short' }}</td>
      <td>{{ order.patient_full_name }}</td>
      <td>{{ order.pt_number_document }}</td>
      <td>
        <!-- Tabla hija: un estudio remitido por fila, cada uno con su propio
             laboratorio externo y su propio estado de anexo -->
        <table class="table-sm">
          <tr *ngFor="let study of order.estudios_remitidos">
            <td>{{ study.study_code }} — {{ study.study_name }}</td>
            <td>{{ study.external_lab_name }}</td>
            <td>
              <span class="badge" [class.badge-success]="study.ar_file_status === 'Cargado'" [class.badge-secondary]="study.ar_file_status !== 'Cargado'">
                {{ study.ar_file_status }}
              </span>
            </td>
            <td>
              <button *ngIf="study.ar_file_status !== 'Cargado'"
                      (click)="openUploadModal(order, study)">
                Cargar PDF de {{ study.external_lab_name }}
              </button>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </tbody>
</table>
```

> El botón "Cargar PDF" se ofrece **por laboratorio**, no por orden: si `order.estudios_remitidos` trae estudios de 2 laboratorios distintos, se muestra un botón por cada estudio pendiente. Si prefieres un solo botón por laboratorio (en vez de uno por estudio), agrupa `estudios_remitidos` por `external_lab_id` en el componente antes de renderizar.

### 5.2 Modal de carga de PDF (`upload-annexed-modal.component.ts`)

El modal necesita **el `o_id` de la orden y el `external_lab_id`** del estudio sobre el que se hizo clic — el backend usa ambos para acotar qué pruebas marcar.

```typescript
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RemissionAnnexedService } from '@core/services/remission-annexed.service';
import { UploadRemittedAnnexedResponse } from '@core/models/remission-annexed.model';

@Component({
  selector: 'app-upload-annexed-modal',
  templateUrl: './upload-annexed-modal.component.html',
})
export class UploadAnnexedModalComponent {
  @Input() orderId!: number;
  @Input() orderNumber?: string;
  @Input() externalLabId!: number;
  @Input() externalLabName?: string;
  @Output() uploaded = new EventEmitter<UploadRemittedAnnexedResponse>();

  selectedFile: File | null = null;
  uploading = false;
  errorMessage: string | null = null;

  constructor(private remissionAnnexedService: RemissionAnnexedService) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    if (file && file.type !== 'application/pdf') {
      this.errorMessage = 'Solo se permiten archivos PDF.';
      this.selectedFile = null;
      return;
    }
    this.errorMessage = null;
    this.selectedFile = file;
  }

  upload(): void {
    if (!this.selectedFile) { return; }
    this.uploading = true;
    this.errorMessage = null;

    this.remissionAnnexedService
      .uploadAnnexedResult(this.orderId, this.externalLabId, this.selectedFile)
      .subscribe({
        next: (res) => {
          this.uploading = false;
          this.uploaded.emit(res);
        },
        error: (err) => {
          this.uploading = false;
          this.errorMessage = err?.error?.detail ?? 'Error al subir el archivo.';
        },
      });
  }
}
```

```html
<div class="modal-body">
  <p>Orden: <strong>{{ orderNumber }}</strong></p>
  <p>Laboratorio: <strong>{{ externalLabName }}</strong></p>
  <p class="text-muted">
    El PDF se marcará únicamente en los estudios de esta orden remitidos a
    <strong>{{ externalLabName }}</strong>. Los estudios remitidos a otro laboratorio no se ven afectados.
  </p>

  <input type="file" accept="application/pdf" (change)="onFileSelected($event)" />
  <p *ngIf="errorMessage" class="text-danger">{{ errorMessage }}</p>

  <button (click)="upload()" [disabled]="!selectedFile || uploading">
    {{ uploading ? 'Subiendo...' : 'Subir PDF anexo' }}
  </button>
</div>
```

Tras un `uploaded` exitoso, muestra un resumen al usuario, por ejemplo:

```typescript
onUploaded(res: UploadRemittedAnnexedResponse): void {
  // res.message ya trae un resumen legible, ej:
  // "PDF anexo subido correctamente para 'LAB. COLCAN'. 1 prueba(s) marcada(s) como 'PDF ANEXO'."
  this.toastr.success(res.message);

  if (res.labs_skipped_validated.length > 0) {
    this.toastr.warning(
      `${res.labs_skipped_validated.length} prueba(s) ya estaban validadas y no se modificaron.`
    );
  }

  this.closeModal();
  this.remittedOrdersList.search(); // refresca — solo el laboratorio cargado pasará a 'Cargado'
}
```

En el componente padre, `openUploadModal(order, study)` inicializa el modal con `orderId = order.o_id`, `externalLabId = study.external_lab_id`, `externalLabName = study.external_lab_name`.

---

## 6. Flujo de Pantalla

1. El usuario entra a la pantalla **"Órdenes Remitidas"** y opcionalmente filtra por fecha, laboratorio externo o si ya tienen/no tienen resultados anexos. El listado está **paginado a nivel de orden** (`skip`/`limit`), como cualquier otro listado de la aplicación.
2. La tabla muestra una fila por **orden**, con sus estudios remitidos anidados (código, nombre, laboratorio externo y estado de anexo — cada estudio con el estado de **su propio** laboratorio).
3. El usuario da clic en **"Cargar PDF de [laboratorio]"** sobre un estudio sin anexo.
4. Se abre el modal ya asociado a esa orden + ese laboratorio específico, selecciona el PDF y confirma.
5. El backend sube el archivo y marca automáticamente **solo las pruebas remitidas a ese laboratorio** (las que no estén ya Validadas) con el resultado `PDF ANEXO`. Si la orden tiene estudios remitidos a otro laboratorio, quedan **sin tocar**.
6. El listado se refresca — únicamente los estudios de ese laboratorio pasan a `ar_file_status = 'Cargado'`; los de otros laboratorios de la misma orden siguen en `'Sin resultado Anexo'` hasta que se cargue su propio PDF.
7. Desde el módulo de validación de resultados, esas pruebas aparecerán en estado "Con Resultados" con el texto `PDF ANEXO`, listas para el flujo normal de validación/impresión (el PDF anexo queda disponible para consulta vía los endpoints existentes de `AnnexedResults`, ver [`IntegracionFrontendAppResultsPage.md`](./IntegracionFrontendAppResultsPage.md) o el módulo de anexos).

---

## 7. Mapeo de Permisos RBAC

| Permiso | Uso |
|---------|-----|
| `Remissions:View` | Listar órdenes con estudios remitidos |
| `Remissions:UploadAnnexedResult` | Cargar PDF anexo (por laboratorio) y marcar pruebas como `PDF ANEXO` |

Verifica que el rol del usuario tenga asignados estos permisos; de lo contrario el backend responderá `403 Forbidden`. `Remissions:UploadAnnexedResult` es un permiso **nuevo** — confirma con el equipo de backend que ya fue sembrado en la base de datos de tu ambiente antes de probar la carga.

---

## 8. Consideraciones de UX

- **Solo PDF:** valida el tipo de archivo en el input (`accept="application/pdf"`) y también del lado del backend (que rechaza con `400` si no es PDF).
- **Paginación:** el listado (`GET /api/remissions/orders`) está paginado con `skip`/`limit` **a nivel de orden** — `total` es la cantidad de órdenes, no de estudios remitidos. Cada orden trae siempre TODOS sus estudios remitidos en `estudios_remitidos` (esa lista hija no se pagina).
- **`external_lab_id` es obligatorio en la carga:** el endpoint de subida ya no acepta "cargar para toda la orden" — siempre se sube para un laboratorio puntual. Si el frontend permite elegir el laboratorio manualmente (en vez de derivarlo del estudio clicado), valida que corresponda a uno de los `estudios_remitidos` de esa orden.
- **Pruebas ya validadas:** si algunas pruebas del laboratorio ya estaban en estado Validada, el backend las omite (no las sobrescribe) y las reporta en `labs_skipped_validated`. Muestra esto como una advertencia, no como un error — la carga del PDF sí fue exitosa.
- **Orden/laboratorio sin estudios remitidos:** si se intenta cargar un anexo para una combinación (orden, laboratorio) sin estudios remitidos a ese laboratorio, el backend responde `422` con un mensaje explicativo; solo debe llegar a esta pantalla el botón habilitado para combinaciones que sí aparecen en `estudios_remitidos`.
- **Refrescar tras cargar:** después de una carga exitosa, vuelve a pedir el listado (o actualiza localmente `ar_file_status = 'Cargado'` solo en los estudios de esa orden **cuyo `external_lab_id` coincide** con el laboratorio cargado) para que la tabla se actualice sin recargar la pantalla.
- **Multi-carga:** el endpoint permite subir más de un PDF por (orden, laboratorio); el listado solo distingue "Cargado" vs "Sin resultado Anexo" por laboratorio — para ver el detalle de cada archivo, usa `GET /api/annexes/order/{order_id}` (módulo de anexos, que ahora también incluye `ar_external_lab_id` en cada registro).
- **Filtro `has_annexed_results` sin seleccionar:** no envíes el parámetro (déjalo `undefined`), no lo envíes como cadena vacía, para que el backend no aplique el filtro y traiga todas las órdenes.
- **Búsqueda (`search`):** hace `ILIKE %texto%` sobre `o_number`, el documento del paciente y el nombre del estudio (no el código). Es una condición `OR` combinada con el resto de filtros por `AND` — por ejemplo `search=colcan` no encontrará nada porque "COLCAN" es el nombre del laboratorio, no del estudio ni del número de orden; usa `external_lab_id` para filtrar por laboratorio. Debounce el input (300ms) antes de llamar a `onFilterChange()` para no disparar una petición por cada tecla.
- **Anexos cargados antes de este cambio:** los PDFs subidos antes de que existiera el campo `external_lab_id` (columna `ar_external_lab_id` agregada en la migración 039) no tienen laboratorio asociado, así que ya no cuentan como "Cargado" para ningún estudio específico — quedan como referencia histórica en el módulo general de anexos.

---

## 9. Ejemplo de Consumo (curl)

```bash
# Listar todas las órdenes remitidas, en un rango de fechas, paginado (página 1 de 20)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/remissions/orders?date_from=2026-08-01&date_to=2026-08-09&skip=0&limit=20"

# Filtrar además por laboratorio de referencia externo
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/remissions/orders?date_from=2026-08-01&date_to=2026-08-09&external_lab_id=3"

# Buscar por número de orden, documento del paciente o nombre de estudio
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/remissions/orders?search=mielograma"

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/remissions/orders?search=1086050471"

# Cargar el PDF anexo de la orden 849 PARA EL LABORATORIO 3 (LAB. COLCAN)
# — no afecta los 6 estudios de la misma orden remitidos al laboratorio 2 (CLINIZAD)
curl -H "Authorization: Bearer $TOKEN" \
  -F "external_lab_id=3" \
  -F "file=@resultados_colcan.pdf;type=application/pdf" \
  "http://localhost:8000/api/remissions/orders/849/annexed-results"
```

Respuesta esperada del listado (caso real: orden con estudios remitidos a 2 laboratorios distintos; `total` cuenta órdenes, no estudios):
```json
{
  "items": [
    {
      "o_id": 849,
      "o_number": "0308260032",
      "fecha_ingreso": "2026-08-03T07:52:12.541185",
      "patient_full_name": "EILIN TALIANA VALENCIA CAICEDO",
      "pt_number_document": "1086050471",
      "estudios_remitidos": [
        { "order_detail_id": 5082, "study_code": "ANCA", "study_name": "CITOPLASMA DE NEUTRÓFILOS ANTICU TOT AUTOMATIZADO POR EIA", "external_lab_id": 2, "external_lab_name": "CLINIZAD", "ar_file_status": "Sin resultado Anexo" },
        { "order_detail_id": 5083, "study_code": "ACDNA", "study_name": "DNA N ANTICUERPOS POR EIA", "external_lab_id": 2, "external_lab_name": "CLINIZAD", "ar_file_status": "Sin resultado Anexo" },
        { "order_detail_id": 5084, "study_code": "ALVIVORUSS", "study_name": "ANTICOAGULANTE LUPICO PRUEBA CONFIRMATORIA CON VENENO DE VIVORA RUSSEL", "external_lab_id": 3, "external_lab_name": "LAB. COLCAN", "ar_file_status": "Sin resultado Anexo" }
      ]
    }
  ],
  "total": 7,
  "skip": 0,
  "limit": 20
}
```

Tras cargar el PDF de LAB. COLCAN para esta orden, solo el estudio `ALVIVORUSS` (od `5084`, `external_lab_id: 3`) pasa a `"ar_file_status": "Cargado"` — los estudios `ANCA`, `ACDNA`, etc. (laboratorio `2`, CLINIZAD) permanecen en `"Sin resultado Anexo"`.

Respuesta esperada de la carga:
```json
{
  "success": true,
  "ar_id": 12,
  "ar_file": "0308260032/12_resultados_colcan.pdf",
  "order_id": 849,
  "external_lab_id": 3,
  "external_lab_name": "LAB. COLCAN",
  "labs_marked": [20843],
  "labs_skipped_validated": [],
  "message": "PDF anexo subido correctamente para 'LAB. COLCAN'. 1 prueba(s) marcada(s) como 'PDF ANEXO'."
}
```
