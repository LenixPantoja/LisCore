# Módulo de Reportes Dinámicos — Guía para el Frontend (Angular)

## ¿Qué hace este módulo?

El backend expone una API que permite:
1. Listar reportes dinámicos configurados en la BD.
2. Obtener el detalle de un reporte (sus parámetros + opciones de selects).
3. Ejecutar el reporte enviando los valores de los filtros → recibir HTML renderizado.
4. Exportar el reporte a PDF en base64.

---

## Base URL

```
/api/reports/dynamic
```

---

## Flujo completo Angular

```
Usuario abre módulo
       ↓
GET /reports/dynamic         → lista de reportes
       ↓
Usuario elige un reporte
       ↓
GET /reports/dynamic/{id}    → parámetros + opciones de selects resueltas
       ↓
Angular construye formulario dinámico
       ↓
Usuario llena filtros y hace clic en "Ejecutar"
       ↓
POST /reports/dynamic/{id}/run   → HTML renderizado
       ↓
Angular muestra <div [innerHTML]="html">
       ↓
(Opcional) POST /reports/dynamic/{id}/export-pdf → PDF base64
```

---

## Endpoints que consumirá Angular

### 1. Listar reportes activos

```
GET /api/reports/dynamic
Authorization: Bearer {token}
```

**Respuesta:**
```json
[
  { "dr_id": 1, "dr_name": "Órdenes por fecha", "dr_description": "...", "dr_active": true },
  { "dr_id": 2, "dr_name": "Pendientes por estudio", "dr_description": "...", "dr_active": true }
]
```

**Uso en Angular:** poblar un `<mat-list>` o `<select>` con los reportes disponibles.

---

### 2. Obtener parámetros del reporte

```
GET /api/reports/dynamic/{id}
Authorization: Bearer {token}
```

**Respuesta:**
```json
{
  "dr_id": 1,
  "dr_name": "Órdenes por fecha",
  "dr_description": "Lista de órdenes con paciente",
  "dr_active": true,
  "parameters": [
    {
      "rp_id": 1,
      "rp_name": "fecha_inicio",
      "rp_label": "Fecha inicio",
      "rp_type": "date",
      "rp_required": true,
      "rp_default_value": null,
      "rp_order_index": 0,
      "options": null
    },
    {
      "rp_id": 2,
      "rp_name": "fecha_fin",
      "rp_label": "Fecha fin",
      "rp_type": "date",
      "rp_required": true,
      "rp_default_value": null,
      "rp_order_index": 1,
      "options": null
    },
    {
      "rp_id": 3,
      "rp_name": "id_estudio",
      "rp_label": "Estudio",
      "rp_type": "select",
      "rp_required": false,
      "rp_default_value": null,
      "rp_order_index": 2,
      "options": [
        { "value": 1, "label": "Hemograma" },
        { "value": 2, "label": "Glicemia" }
      ]
    }
  ]
}
```

---

### 3. Ejecutar el reporte

```
POST /api/reports/dynamic/{id}/run
Authorization: Bearer {token}
Content-Type: application/json

{
  "params": {
    "fecha_inicio": "2026-05-01",
    "fecha_fin": "2026-05-13",
    "id_estudio": 1
  }
}
```

**Respuesta:**
```json
{
  "report_id": 1,
  "report_name": "Órdenes por fecha",
  "total_rows": 42,
  "html": "<h2>Órdenes del 2026-05-01...</h2><table>...</table>"
}
```

**Uso en Angular:** renderizar con `[innerHTML]="html"`.

---

### 4. Exportar a PDF

```
POST /api/reports/dynamic/{id}/export-pdf
Authorization: Bearer {token}
Content-Type: application/json

{
  "params": {
    "fecha_inicio": "2026-05-01",
    "fecha_fin": "2026-05-13"
  }
}
```

**Respuesta:**
```json
{
  "filename": "reporte_1_Ordenes_por_fecha.pdf",
  "base64_pdf": "JVBERi0xLjQK...",
  "report_name": "Órdenes por fecha",
  "total_rows": 42
}
```

**Uso en Angular:** decodificar base64 y disparar descarga:
```ts
const blob = this.base64ToBlob(response.base64_pdf, 'application/pdf');
const url  = URL.createObjectURL(blob);
const a    = document.createElement('a');
a.href     = url;
a.download = response.filename;
a.click();
URL.revokeObjectURL(url);
```

---

## Formulario Dinámico — Lógica Angular

Iterá sobre `parameters` ordenados por `rp_order_index` y generá controles según `rp_type`:

| `rp_type`     | Control Angular                          |
|---------------|------------------------------------------|
| `date`        | `<input type="date">`                    |
| `datetime`    | `<input type="datetime-local">`          |
| `text`        | `<input type="text">`                    |
| `number`      | `<input type="number">`                  |
| `select`      | `<mat-select>` con `options`             |
| `multiselect` | `<mat-select multiple>` con `options`    |
| `checkbox`    | `<mat-checkbox>`                         |
| `textarea`    | `<textarea>`                             |

### Ejemplo de componente (simplificado):

```ts
// dynamic-report.component.ts
export class DynamicReportComponent {
  reports: DynamicReportSummary[] = [];
  selectedReport: DynamicReportDetail | null = null;
  form = this.fb.group({});
  html = '';

  constructor(private fb: FormBuilder, private svc: DynamicReportService) {}

  loadReports() {
    this.svc.list().subscribe(r => this.reports = r);
  }

  selectReport(id: number) {
    this.svc.getDetail(id).subscribe(report => {
      this.selectedReport = report;
      this.buildForm(report.parameters);
    });
  }

  buildForm(params: ReportParameter[]) {
    this.form = this.fb.group({});
    params.forEach(p => {
      this.form.addControl(
        p.rp_name,
        this.fb.control(p.rp_default_value ?? '', p.rp_required ? Validators.required : [])
      );
    });
  }

  runReport() {
    if (!this.selectedReport || this.form.invalid) return;
    this.svc.run(this.selectedReport.dr_id, this.form.value).subscribe(r => {
      this.html = r.html;
    });
  }

  exportPdf() {
    if (!this.selectedReport) return;
    this.svc.exportPdf(this.selectedReport.dr_id, this.form.value).subscribe(r => {
      const blob = this.base64ToBlob(r.base64_pdf, 'application/pdf');
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = r.filename; a.click();
      URL.revokeObjectURL(url);
    });
  }

  private base64ToBlob(b64: string, type: string): Blob {
    const bytes = atob(b64);
    const arr   = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    return new Blob([arr], { type });
  }
}
```

### Template mínimo:

```html
<!-- Lista de reportes -->
<mat-list>
  <mat-list-item *ngFor="let r of reports" (click)="selectReport(r.dr_id)">
    {{ r.dr_name }}
  </mat-list-item>
</mat-list>

<!-- Formulario dinámico -->
<form [formGroup]="form" *ngIf="selectedReport" (ngSubmit)="runReport()">
  <ng-container *ngFor="let p of selectedReport.parameters">

    <mat-form-field *ngIf="p.rp_type === 'text'">
      <mat-label>{{ p.rp_label }}</mat-label>
      <input matInput [formControlName]="p.rp_name">
    </mat-form-field>

    <mat-form-field *ngIf="p.rp_type === 'date'">
      <mat-label>{{ p.rp_label }}</mat-label>
      <input matInput type="date" [formControlName]="p.rp_name">
    </mat-form-field>

    <mat-form-field *ngIf="p.rp_type === 'number'">
      <mat-label>{{ p.rp_label }}</mat-label>
      <input matInput type="number" [formControlName]="p.rp_name">
    </mat-form-field>

    <mat-form-field *ngIf="p.rp_type === 'select'">
      <mat-label>{{ p.rp_label }}</mat-label>
      <mat-select [formControlName]="p.rp_name">
        <mat-option *ngFor="let opt of p.options" [value]="opt.value">
          {{ opt.label }}
        </mat-option>
      </mat-select>
    </mat-form-field>

    <mat-form-field *ngIf="p.rp_type === 'multiselect'">
      <mat-label>{{ p.rp_label }}</mat-label>
      <mat-select [formControlName]="p.rp_name" multiple>
        <mat-option *ngFor="let opt of p.options" [value]="opt.value">
          {{ opt.label }}
        </mat-option>
      </mat-select>
    </mat-form-field>

    <mat-checkbox *ngIf="p.rp_type === 'checkbox'" [formControlName]="p.rp_name">
      {{ p.rp_label }}
    </mat-checkbox>

    <mat-form-field *ngIf="p.rp_type === 'textarea'">
      <mat-label>{{ p.rp_label }}</mat-label>
      <textarea matInput [formControlName]="p.rp_name"></textarea>
    </mat-form-field>

  </ng-container>

  <button mat-raised-button color="primary" type="submit">Ejecutar</button>
  <button mat-stroked-button type="button" (click)="exportPdf()">Exportar PDF</button>
</form>

<!-- Resultado HTML renderizado -->
<div *ngIf="html" [innerHTML]="html" class="report-output"></div>
```

---

## Servicio Angular sugerido

```ts
// dynamic-report.service.ts
@Injectable({ providedIn: 'root' })
export class DynamicReportService {
  private base = '/api/reports/dynamic';

  constructor(private http: HttpClient) {}

  list()                         { return this.http.get<any[]>(this.base); }
  getDetail(id: number)          { return this.http.get<any>(`${this.base}/${id}`); }
  run(id: number, params: any)   { return this.http.post<any>(`${this.base}/${id}/run`, { params }); }
  exportPdf(id: number, params: any) {
    return this.http.post<any>(`${this.base}/${id}/export-pdf`, { params });
  }
}
```

---

## Permisos necesarios (RBAC)

El backend requiere estos permisos en el rol del usuario:

| Permiso                       | Acción                         |
|-------------------------------|--------------------------------|
| `Reports:DynamicList`         | Ver listado de reportes        |
| `Reports:DynamicRead`         | Ver detalle + parámetros       |
| `Reports:DynamicCreate`       | Crear reporte (admin)          |
| `Reports:DynamicUpdate`       | Editar reporte (admin)         |
| `Reports:DynamicDelete`       | Desactivar reporte (admin)     |
| `Reports:DynamicRun`          | Ejecutar reporte               |
| `Reports:DynamicExportPdf`    | Exportar PDF                   |

Registrálos en la tabla de permisos del sistema para asignarlos a los roles.

---

## Notas de seguridad para el front

- Siempre enviar el token JWT en el header `Authorization: Bearer {token}`.
- No mostrar el HTML del reporte en contextos donde el usuario pueda ser malicioso (el HTML es generado por admins, no por el usuario final).
- Usar `DomSanitizer.bypassSecurityTrustHtml` en Angular solo si el HTML es confiable (viene del backend controlado).
