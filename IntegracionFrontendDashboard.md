# Guía de Integración Frontend: Dashboard de Producción (Angular)

Este documento describe cómo integrar los endpoints del **Dashboard de Producción** del backend **LisCore** en Angular, para construir las 3 gráficas y las 5 tarjetas KPI del mockup:

- **Producción por Área** (barras: % y cantidad por grupo de trabajo)
- **Top 10 Total de Estudios** (barras + tabla)
- **Total de Estudios por Servicio** (barras: % y cantidad por servicio)
- **KPIs**: pacientes atendidos (con desglose por género), órdenes procesadas, pruebas recibidas, promedio de exámenes por orden, paciente con más atenciones

---

## 1. Base URL y Autenticación

Todas las peticiones deben incluir el token JWT:

```
Authorization: Bearer <token>
```

**Prefijo base:** `{base_url}/api/reports/dashboard/...`

Ejemplo:
```
http://localhost:8000/api/reports/dashboard/production-by-work-group
```

Todos los endpoints aceptan (opcionalmente) `date_from` y `date_to` en formato `YYYY-MM-DD`. Si se omiten, se calcula sobre el histórico completo.

Permiso requerido (RBAC): **`Reports:Dashboard`** (el mismo que ya usa `/api/reports/dashboard/stats`).

---

## 2. Resumen de Endpoints

| # | Método | Endpoint | Uso |
|---|--------|----------|-----|
| 1 | GET | `/api/reports/dashboard/production-by-work-group?date_from=&date_to=` | Gráfica "Producción por Área" |
| 2 | GET | `/api/reports/dashboard/top-studies?date_from=&date_to=&limit=10` | Gráfica + tabla "Top 10 Total de Estudios" |
| 3 | GET | `/api/reports/dashboard/studies-by-service?date_from=&date_to=` | Gráfica "Total de Estudios por Servicio" |
| 4 | GET | `/api/reports/dashboard/kpis-summary?date_from=&date_to=` | Las 5 tarjetas KPI |

> Cada gráfica del mockup tiene su propio filtro de fecha independiente, así que en el frontend cada sección debe llamar su endpoint con sus propias fechas (no comparten un único filtro global obligatoriamente, aunque puedes usar un filtro global como valor por defecto de los tres).

---

## 3. Modelos TypeScript (`dashboard.model.ts`)

Crear en `src/app/core/models/dashboard.model.ts`:

```typescript
// ── Filtros comunes ─────────────────────────────────────────────

export interface DashboardDateFilter {
  date_from?: string; // 'YYYY-MM-DD'
  date_to?: string;   // 'YYYY-MM-DD'
}

// ── 1. Producción por Área ──────────────────────────────────────

export interface ProductionByWorkGroupItem {
  work_group_id: number | null;
  work_group: string | null;
  total: number;
  percentage: number; // 0-100, redondeado a 2 decimales
}

export interface ProductionByWorkGroupResponse {
  total: number;
  items: ProductionByWorkGroupItem[];
}

// ── 2. Top 10 Estudios ──────────────────────────────────────────

export interface TopStudyItem {
  study_id: number;
  study_name: string | null;
  total: number;
}

export interface TopStudiesResponse {
  items: TopStudyItem[];
}

// ── 3. Estudios por Servicio ────────────────────────────────────

export interface StudiesByServiceItem {
  service_id: number | null;
  service_name: string | null;
  total: number;
  percentage: number;
}

export interface StudiesByServiceResponse {
  total: number;
  items: StudiesByServiceItem[];
}

// ── 4. KPIs ──────────────────────────────────────────────────────

export interface TopPatientItem {
  pt_id: number;
  document: string | null;
  name: string | null;
  total_visits: number;
}

export interface DashboardKpisSummaryResponse {
  total_patients: number;
  male_patients: number;
  female_patients: number;
  total_orders: number;
  total_tests: number;
  avg_tests_per_order: number;
  top_patient: TopPatientItem | null;
}
```

---

## 4. Servicio Angular (`dashboard.service.ts`)

Crear en `src/app/core/services/dashboard.service.ts`:

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  DashboardDateFilter,
  ProductionByWorkGroupResponse,
  TopStudiesResponse,
  StudiesByServiceResponse,
  DashboardKpisSummaryResponse,
} from '@core/models/dashboard.model';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private base = `${environment.apiUrl}/api/reports/dashboard`;

  constructor(private http: HttpClient) {}

  private buildParams(filter?: DashboardDateFilter, extra?: Record<string, any>): HttpParams {
    let params = new HttpParams();
    const all = { ...filter, ...extra };
    Object.entries(all).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return params;
  }

  /** Gráfica "Producción por Área" */
  getProductionByWorkGroup(filter?: DashboardDateFilter): Observable<ProductionByWorkGroupResponse> {
    return this.http.get<ProductionByWorkGroupResponse>(
      `${this.base}/production-by-work-group`,
      { params: this.buildParams(filter) },
    );
  }

  /** Gráfica + tabla "Top 10 Total de Estudios" */
  getTopStudies(filter?: DashboardDateFilter, limit: number = 10): Observable<TopStudiesResponse> {
    return this.http.get<TopStudiesResponse>(
      `${this.base}/top-studies`,
      { params: this.buildParams(filter, { limit }) },
    );
  }

  /** Gráfica "Total de Estudios por Servicio" */
  getStudiesByService(filter?: DashboardDateFilter): Observable<StudiesByServiceResponse> {
    return this.http.get<StudiesByServiceResponse>(
      `${this.base}/studies-by-service`,
      { params: this.buildParams(filter) },
    );
  }

  /** Tarjetas KPI */
  getKpisSummary(filter?: DashboardDateFilter): Observable<DashboardKpisSummaryResponse> {
    return this.http.get<DashboardKpisSummaryResponse>(
      `${this.base}/kpis-summary`,
      { params: this.buildParams(filter) },
    );
  }
}
```

---

## 5. Estructura de Componentes Sugerida

```
dashboard/
├── dashboard-page/
│   └── dashboard-page.component.ts        # Orquesta las 4 secciones + filtros
├── kpi-cards/
│   └── kpi-cards.component.ts              # Las 5 tarjetas
├── production-by-work-group-chart/
│   └── production-by-work-group-chart.component.ts   # Barras % / cantidad
├── top-studies-chart/
│   └── top-studies-chart.component.ts      # Barras + tabla
└── studies-by-service-chart/
    └── studies-by-service-chart.component.ts  # Barras % / cantidad
```

Se usa **`ng2-charts`** (wrapper de Chart.js) como en el resto del proyecto; si ya tienes otra librería de gráficas integrada (ApexCharts, ECharts, etc.), solo cambia la capa de renderizado — los datos que entrega el backend ya vienen listos para graficar (`total` + `percentage`).

### 5.1 Ejemplo: gráfica de barras "Producción por Área"

```typescript
import { Component, Input, OnChanges } from '@angular/core';
import { ChartConfiguration, ChartData } from 'chart.js';
import { DashboardService } from '@core/services/dashboard.service';
import { DashboardDateFilter } from '@core/models/dashboard.model';

@Component({
  selector: 'app-production-by-work-group-chart',
  templateUrl: './production-by-work-group-chart.component.html',
})
export class ProductionByWorkGroupChartComponent implements OnChanges {
  @Input() filter?: DashboardDateFilter;

  loading = false;
  total = 0;

  chartData: ChartData<'bar'> = { labels: [], datasets: [{ data: [], label: 'Cantidad' }] };
  chartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const pct = (ctx.dataset as any).percentages?.[ctx.dataIndex];
            return `${ctx.formattedValue} (${pct}%)`;
          },
        },
      },
    },
  };

  constructor(private dashboardService: DashboardService) {}

  ngOnChanges(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.dashboardService.getProductionByWorkGroup(this.filter).subscribe({
      next: (res) => {
        this.total = res.total;
        this.chartData = {
          labels: res.items.map((i) => i.work_group ?? 'Sin grupo'),
          datasets: [
            {
              data: res.items.map((i) => i.total),
              label: 'Cantidad',
              percentages: res.items.map((i) => i.percentage), // usado en el tooltip
            } as any,
          ],
        };
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }
}
```

```html
<!-- production-by-work-group-chart.component.html -->
<div class="chart-card">
  <h3>Producción por Área</h3>
  <canvas baseChart
    [data]="chartData"
    [options]="chartOptions"
    type="bar">
  </canvas>
  <div *ngIf="loading" class="loading-overlay">Cargando...</div>
</div>
```

Las gráficas de **"Total de Estudios por Servicio"** siguen el mismo patrón, solo cambiando el servicio invocado (`getStudiesByService`) y las etiquetas (`service_name`).

### 5.2 Ejemplo: "Top 10 Total de Estudios" (barras + tabla)

```typescript
import { Component, Input, OnChanges } from '@angular/core';
import { ChartData } from 'chart.js';
import { DashboardService } from '@core/services/dashboard.service';
import { DashboardDateFilter, TopStudyItem } from '@core/models/dashboard.model';

@Component({
  selector: 'app-top-studies-chart',
  templateUrl: './top-studies-chart.component.html',
})
export class TopStudiesChartComponent implements OnChanges {
  @Input() filter?: DashboardDateFilter;

  items: TopStudyItem[] = [];
  chartData: ChartData<'bar'> = { labels: [], datasets: [{ data: [], label: 'Solicitudes' }] };
  loading = false;

  constructor(private dashboardService: DashboardService) {}

  ngOnChanges(): void {
    this.loading = true;
    this.dashboardService.getTopStudies(this.filter, 10).subscribe({
      next: (res) => {
        this.items = res.items;
        this.chartData = {
          labels: res.items.map((i) => i.study_name ?? `Estudio ${i.study_id}`),
          datasets: [{ data: res.items.map((i) => i.total), label: 'Solicitudes' }],
        };
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }
}
```

```html
<div class="chart-card">
  <h3>Top 10 Total de Estudios</h3>
  <canvas baseChart [data]="chartData" type="bar"></canvas>

  <table class="table">
    <thead>
      <tr><th>Estudio</th><th>Total</th></tr>
    </thead>
    <tbody>
      <tr *ngFor="let it of items">
        <td>{{ it.study_name }}</td>
        <td>{{ it.total }}</td>
      </tr>
    </tbody>
  </table>
</div>
```

### 5.3 Ejemplo: Tarjetas KPI

```typescript
import { Component, Input, OnChanges } from '@angular/core';
import { DashboardService } from '@core/services/dashboard.service';
import { DashboardDateFilter, DashboardKpisSummaryResponse } from '@core/models/dashboard.model';

@Component({
  selector: 'app-kpi-cards',
  templateUrl: './kpi-cards.component.html',
})
export class KpiCardsComponent implements OnChanges {
  @Input() filter?: DashboardDateFilter;

  kpis?: DashboardKpisSummaryResponse;
  loading = false;

  constructor(private dashboardService: DashboardService) {}

  ngOnChanges(): void {
    this.loading = true;
    this.dashboardService.getKpisSummary(this.filter).subscribe({
      next: (res) => { this.kpis = res; this.loading = false; },
      error: () => { this.loading = false; },
    });
  }
}
```

```html
<div class="kpi-grid" *ngIf="kpis">
  <div class="kpi-card">
    <span class="kpi-label">Total pacientes atendidos</span>
    <span class="kpi-value">{{ kpis.total_patients }}</span>
    <span class="kpi-detail">
      <span class="text-primary">{{ kpis.male_patients }} H</span> /
      <span class="text-danger">{{ kpis.female_patients }} M</span>
    </span>
  </div>

  <div class="kpi-card">
    <span class="kpi-label">Total órdenes procesadas</span>
    <span class="kpi-value">{{ kpis.total_orders }}</span>
  </div>

  <div class="kpi-card">
    <span class="kpi-label">Total pruebas recibidas</span>
    <span class="kpi-value">{{ kpis.total_tests }}</span>
  </div>

  <div class="kpi-card">
    <span class="kpi-label">Promedio exámenes por orden</span>
    <span class="kpi-value">{{ kpis.avg_tests_per_order }}</span>
  </div>

  <div class="kpi-card" *ngIf="kpis.top_patient as tp">
    <span class="kpi-label">Paciente con más atenciones</span>
    <span class="kpi-value">{{ tp.total_visits }} visitas</span>
    <span class="kpi-detail">{{ tp.name }} ({{ tp.document }})</span>
  </div>
</div>
```

---

## 6. Componente Orquestador (`dashboard-page.component.ts`)

Cada sección tiene su propio filtro de fecha en el mockup (Fecha Inicial / Fecha Final), así que se recomienda un `DashboardDateFilter` independiente por sección, todos inicializados con el mismo rango por defecto (p. ej. mes actual):

```typescript
import { Component } from '@angular/core';
import { DashboardDateFilter } from '@core/models/dashboard.model';

@Component({
  selector: 'app-dashboard-page',
  templateUrl: './dashboard-page.component.html',
})
export class DashboardPageComponent {
  kpiFilter: DashboardDateFilter = {};
  productionFilter: DashboardDateFilter = {};
  topStudiesFilter: DashboardDateFilter = {};
  servicesFilter: DashboardDateFilter = {};

  applyKpiFilter(from?: string, to?: string): void {
    this.kpiFilter = { date_from: from, date_to: to };
  }
  applyProductionFilter(from?: string, to?: string): void {
    this.productionFilter = { date_from: from, date_to: to };
  }
  applyTopStudiesFilter(from?: string, to?: string): void {
    this.topStudiesFilter = { date_from: from, date_to: to };
  }
  applyServicesFilter(from?: string, to?: string): void {
    this.servicesFilter = { date_from: from, date_to: to };
  }
}
```

```html
<app-kpi-cards [filter]="kpiFilter"></app-kpi-cards>

<app-production-by-work-group-chart [filter]="productionFilter"></app-production-by-work-group-chart>
<app-top-studies-chart [filter]="topStudiesFilter"></app-top-studies-chart>
<app-studies-by-service-chart [filter]="servicesFilter"></app-studies-by-service-chart>
```

Como los `@Input()` disparan `ngOnChanges` al reasignarse un nuevo objeto, basta con crear un objeto nuevo (no mutar el existente) cada vez que el usuario aplique un filtro de fecha, para que el componente hijo vuelva a llamar al backend automáticamente.

---

## 7. Mapeo de Permisos RBAC

| Endpoint | Permiso |
|----------|---------|
| Los 4 endpoints de `/dashboard/*` | `Reports:Dashboard` |

Verifica que el rol del usuario tenga asignado `Reports:Dashboard` (el mismo permiso que ya usa `/api/reports/dashboard/stats`); si no, el backend responderá `403 Forbidden`.

---

## 8. Consideraciones de UX

- **Fechas opcionales:** si el usuario no selecciona rango, no envíes `date_from`/`date_to` (o envíalos como `undefined`) para que el backend calcule sobre el histórico completo — no envíes cadenas vacías.
- **Loading state:** cada sección tiene su propia carga independiente; usa un spinner/skeleton por card/gráfica, no uno global, ya que las 4 llamadas son independientes entre sí.
- **Sin datos:** si `items` viene vacío (o `total_orders`/`total_tests` es 0), muestra un estado vacío en vez de una gráfica en blanco.
- **Porcentajes:** ya vienen calculados y redondeados a 2 decimales desde el backend (`percentage`); no los recalcules en el frontend para evitar diferencias de redondeo entre gráficas y tooltips.
- **`work_group` / `service_name` nulos:** algunos estudios pueden no tener grupo de trabajo o servicio asociado; el backend los agrupa igualmente bajo `null` — en el frontend muéstralos como "Sin grupo" / "Sin servicio".

---

## 9. Ejemplo de Consumo (curl)

```bash
# Producción por área (todo el histórico)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/dashboard/production-by-work-group"

# Producción por área filtrado por fecha
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/dashboard/production-by-work-group?date_from=2026-01-01&date_to=2026-08-03"

# Top 10 estudios
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/dashboard/top-studies?date_from=2026-01-01&date_to=2026-08-03&limit=10"

# Estudios por servicio
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/dashboard/studies-by-service?date_from=2026-01-01&date_to=2026-08-03"

# KPIs
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/dashboard/kpis-summary?date_from=2026-01-01&date_to=2026-08-03"
```
