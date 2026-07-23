# Guía de Integración Frontend: Portal de Resultados (App Results Page) — Angular

Este documento describe cómo integrar el **portal de consulta de resultados** (pacientes y empresas) del backend **LisCore** en una aplicación **Angular**. Cubre autenticación, endpoints REST, modelos TypeScript, servicios, guards, interceptor y flujos de pantalla.

> ⚠️ **Importante**: este portal usa su **propio sistema de autenticación**, completamente separado del login de personal interno (`/api/users/login`). Los tokens de un sistema **no sirven** en el otro — el backend los rechaza explícitamente (ver sección 1.2).

---

## 1. Base URL y Autenticación

**Prefijo base:** `{base_url}/api/app-results-page/...`

Ejemplo:
```
http://localhost:8000/api/app-results-page/login
```

### 1.1 Login

`POST /api/app-results-page/login` — **público**, no requiere token.

Body:
```json
{
  "login": "1234567890",
  "password": "miclave"
}
```

- `login`: número de documento del paciente **o** NIT de la empresa (el backend detecta cuál es automáticamente).
- La contraseña se valida contra `Patients.pt_password` o `Enterprises.en_password` según corresponda — es la misma contraseña que ya se gestiona en esas tablas, no hay una contraseña separada para el portal.

Respuesta `200 OK`:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "arp_user_access_type": 1,
  "patient": {
    "pt_id": 501,
    "document_number": "1234567890",
    "fullname": "JUAN PEREZ GOMEZ",
    "mail": "juan@mail.com",
    "phone_number": "3001234567",
    "date_of_birth": "1990-05-12",
    "sex": "Masculino"
  },
  "enterprise": null
}
```

Si el login es de una empresa, `arp_user_access_type` viene en `2`, `patient` es `null` y `enterprise` trae `{en_id, nit, name, mail}`.

**`arp_user_access_type` es el campo clave para el enrutamiento del front**: `1` → Paciente, `2` → Empresa.

Errores:
| Código | Causa |
|--------|-------|
| `401` | Login o contraseña incorrectos, o el usuario del portal está inactivo (`arp_user_active = false`) |

### 1.2 Uso del token

Todas las peticiones autenticadas del portal deben incluir:
```
Authorization: Bearer <access_token>
```

Notas sobre este token:
- Expira en **30 minutos** (mismo `ACCESS_TOKEN_EXPIRE_MINUTES` que el resto del sistema). **No hay refresh token** para el portal — cuando expire, el front debe redirigir a login nuevamente (no intentar renovar).
- El backend valida un claim interno `portal: true` — un token de este login **no funciona** contra endpoints de personal interno, y viceversa. No hace falta que el front haga nada especial por esto, solo asegúrate de no reutilizar el interceptor/token del login de staff para estas rutas si ambos coexisten en la misma app.
- No hay endpoint de logout (el JWT es *stateless*) — "cerrar sesión" es simplemente borrar el token guardado en el cliente.
- No existe (todavía) flujo de "recuperar contraseña" ni "registro" desde el portal, aunque la tabla tiene un campo `arp_user_recovery` reservado para eso a futuro. No lo expongas en el front por ahora.

---

## 2. Modelos TypeScript (`app-results-page.model.ts`)

Crear en `src/app/core/models/app-results-page.model.ts`:

```typescript
// ── Tipos de acceso ─────────────────────────────────────────────

export enum PortalAccessType {
  Paciente = 1,
  Empresa = 2,
}

// ── Login ───────────────────────────────────────────────────────

export interface PortalLoginRequest {
  login: string;
  password: string;
}

export interface PortalPatientData {
  pt_id: number;
  document_number: string;
  fullname: string;
  mail?: string;
  phone_number?: string;
  date_of_birth?: string;   // date ISO (YYYY-MM-DD)
  sex?: string;             // "Masculino" | "Femenino"
}

export interface PortalEnterpriseData {
  en_id: number;
  nit: string;
  name: string;
  mail?: string;
}

export interface PortalLoginResponse {
  access_token: string;
  token_type: string;
  arp_user_access_type: PortalAccessType;
  patient?: PortalPatientData | null;
  enterprise?: PortalEnterpriseData | null;
}

// ── Resultados ──────────────────────────────────────────────────

export interface StudyResultItem {
  test_name: string;
  result?: string;
  units?: string;
  l_state: string;           // nombre del estado, ya resuelto por el backend
  l_date_validatie?: string; // datetime ISO
}

export interface StudyWithResults {
  study_name: string;
  results: StudyResultItem[];
}

export interface PatientOrderItem {
  o_number?: string;
  o_autorizacion: string;    // "" si no tiene
  document_number?: string;
  fullname_patient: string;
  o_date?: string;           // date ISO
  o_order_state: string;     // nombre del estado, ya resuelto por el backend
  studies: StudyWithResults[];
}

export interface PatientOrdersPaginatedResponse {
  total: number;
  page: number;
  page_size: number;
  items: PatientOrderItem[];
}

export interface EnterpriseOrderItem {
  o_number?: string;
  io_number_request: string; // "" si no tiene (= o_autorizacion internamente)
  document_number?: string;
  fullname_patient: string;
  o_date?: string;
  age?: string;               // "5 días" | "3 meses" | "34 años"
  sex?: string;
  o_order_state: string;
  studies: StudyWithResults[];
}

export interface EnterpriseOrdersPaginatedResponse {
  total: number;
  page: number;
  page_size: number;
  items: EnterpriseOrderItem[];
}
```

---

## 3. Servicios Angular

### 3.1 Auth Service (`portal-auth.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '@env/environment';
import {
  PortalLoginRequest, PortalLoginResponse, PortalAccessType,
} from '@core/models/app-results-page.model';

const TOKEN_KEY = 'portal_access_token';
const ACCESS_TYPE_KEY = 'portal_access_type';
const USER_DATA_KEY = 'portal_user_data';

@Injectable({ providedIn: 'root' })
export class PortalAuthService {
  private base = `${environment.apiUrl}/api/app-results-page`;

  constructor(private http: HttpClient) {}

  login(data: PortalLoginRequest): Observable<PortalLoginResponse> {
    return this.http.post<PortalLoginResponse>(`${this.base}/login`, data).pipe(
      tap((res) => {
        localStorage.setItem(TOKEN_KEY, res.access_token);
        localStorage.setItem(ACCESS_TYPE_KEY, String(res.arp_user_access_type));
        localStorage.setItem(
          USER_DATA_KEY,
          JSON.stringify(res.arp_user_access_type === PortalAccessType.Paciente ? res.patient : res.enterprise)
        );
      })
    );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ACCESS_TYPE_KEY);
    localStorage.removeItem(USER_DATA_KEY);
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  getAccessType(): PortalAccessType | null {
    const raw = localStorage.getItem(ACCESS_TYPE_KEY);
    return raw ? (Number(raw) as PortalAccessType) : null;
  }

  getUserData<T = any>(): T | null {
    const raw = localStorage.getItem(USER_DATA_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  isPatient(): boolean {
    return this.getAccessType() === PortalAccessType.Paciente;
  }

  isEnterprise(): boolean {
    return this.getAccessType() === PortalAccessType.Empresa;
  }
}
```

### 3.2 Results Service (`portal-results.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import {
  PatientOrdersPaginatedResponse, EnterpriseOrdersPaginatedResponse,
} from '@core/models/app-results-page.model';

@Injectable({ providedIn: 'root' })
export class PortalResultsService {
  private base = `${environment.apiUrl}/api/app-results-page`;

  constructor(private http: HttpClient) {}

  private buildParams(page: number, pageSize: number, search?: string): HttpParams {
    let params = new HttpParams()
      .set('page', String(page))
      .set('page_size', String(pageSize));
    if (search) {
      params = params.set('search', search);
    }
    return params;
  }

  /** Listado de órdenes del paciente autenticado */
  getPatientOrders(page = 1, pageSize = 20, search?: string): Observable<PatientOrdersPaginatedResponse> {
    return this.http.get<PatientOrdersPaginatedResponse>(`${this.base}/patient/orders`, {
      params: this.buildParams(page, pageSize, search),
    });
  }

  /** Listado de órdenes de la empresa autenticada */
  getEnterpriseOrders(page = 1, pageSize = 20, search?: string): Observable<EnterpriseOrdersPaginatedResponse> {
    return this.http.get<EnterpriseOrdersPaginatedResponse>(`${this.base}/enterprise/orders`, {
      params: this.buildParams(page, pageSize, search),
    });
  }
}
```

El parámetro `search` es único y busca simultáneamente:
- **Paciente**: `o_number`, `o_date` (formato `YYYY-MM-DD` o `DD/MM/YYYY`), o nombre del estado (`o_order_state`, ej. `"validada"`).
- **Empresa**: lo mismo, más número de documento del paciente y `o_autorizacion`.

No hace falta que el front decida cuál campo está buscando el usuario — el backend prueba todas las coincidencias posibles con un único texto.

---

## 4. Interceptor HTTP (`portal-auth.interceptor.ts`)

Como este token es independiente del de personal interno, usa un interceptor que solo actúe sobre rutas `/api/app-results-page/`:

```typescript
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { PortalAuthService } from '@core/services/portal-auth.service';

@Injectable()
export class PortalAuthInterceptor implements HttpInterceptor {
  constructor(private auth: PortalAuthService, private router: Router) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!req.url.includes('/api/app-results-page/')) {
      return next.handle(req);
    }

    const token = this.auth.getToken();
    const authReq = token && !req.url.endsWith('/login')
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req;

    return next.handle(authReq).pipe(
      catchError((err: HttpErrorResponse) => {
        if (err.status === 401) {
          // token inválido o expirado — no hay refresh, se cierra sesión
          this.auth.logout();
          this.router.navigate(['/portal/login']);
        }
        return throwError(() => err);
      })
    );
  }
}
```

Regístralo en `app.module.ts`:
```typescript
providers: [
  { provide: HTTP_INTERCEPTORS, useClass: PortalAuthInterceptor, multi: true },
]
```

---

## 5. Guard de rutas (`portal-auth.guard.ts`)

```typescript
import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot } from '@angular/router';
import { PortalAuthService } from '@core/services/portal-auth.service';
import { PortalAccessType } from '@core/models/app-results-page.model';

@Injectable({ providedIn: 'root' })
export class PortalAuthGuard implements CanActivate {
  constructor(private auth: PortalAuthService, private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot): boolean {
    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/portal/login']);
      return false;
    }

    // Protección opcional por tipo de acceso (data: { accessType: PortalAccessType.Paciente })
    const requiredType: PortalAccessType | undefined = route.data?.['accessType'];
    if (requiredType !== undefined && this.auth.getAccessType() !== requiredType) {
      this.router.navigate(['/portal/login']);
      return false;
    }

    return true;
  }
}
```

---

## 6. Configuración de Rutas (`portal-routing.module.ts`)

```typescript
import { PortalAccessType } from '@core/models/app-results-page.model';

const routes: Routes = [
  { path: 'portal/login', component: PortalLoginComponent },
  {
    path: 'portal/paciente/resultados',
    component: PatientResultsComponent,
    canActivate: [PortalAuthGuard],
    data: { accessType: PortalAccessType.Paciente },
  },
  {
    path: 'portal/empresa/resultados',
    component: EnterpriseResultsComponent,
    canActivate: [PortalAuthGuard],
    data: { accessType: PortalAccessType.Empresa },
  },
];
```

Enrutamiento post-login (en `PortalLoginComponent`):
```typescript
this.portalAuth.login({ login, password }).subscribe({
  next: (res) => {
    if (res.arp_user_access_type === PortalAccessType.Paciente) {
      this.router.navigate(['/portal/paciente/resultados']);
    } else {
      this.router.navigate(['/portal/empresa/resultados']);
    }
  },
  error: (err) => {
    this.errorMessage = err.status === 401
      ? 'Usuario o contraseña incorrectos.'
      : 'Ocurrió un error al iniciar sesión.';
  },
});
```

---

## 7. Consideraciones de UX

- **Paginación**: `page` inicia en `1` (no `0`), `page_size` por defecto `20`, máximo `100`. Usa `total` para calcular el número de páginas (`Math.ceil(total / page_size)`).
- **Búsqueda**: aplica `debounceTime(400)` + `distinctUntilChanged()` sobre el input de búsqueda antes de llamar al servicio, para no disparar una petición por cada tecla.
- **Estados vacíos**: si `studies` viene como arreglo vacío `[]` en una orden, significa que la orden aún no tiene exámenes con resultados de laboratorio cargados — muéstralo como "Resultados pendientes", no como error.
- **`l_state` / `o_order_state`**: el backend ya devuelve el **nombre** del estado (ej. `"Validada"`, `"Con Resultados"`), no el id — úsalo directo para mostrar, no hace falta mapearlo en el front.
- **Campos "si lo tiene, sino vacío"** (`o_autorizacion`, `io_number_request`): el backend siempre devuelve `string` (nunca `null`) — si viene `""`, muestra un placeholder tipo `"—"` en la tabla.
- **Sesión expirada**: como no hay refresh token, ante un `401` durante el uso normal del portal (no en el login), el interceptor ya redirige a `/portal/login` — solo asegúrate de mostrar un mensaje tipo "Tu sesión expiró, inicia sesión de nuevo" antes de redirigir si quieres mejor UX.

---

## 8. Resumen de Endpoints API

| Método | URL | Auth | Query / Body | Respuesta |
|--------|-----|------|---------------|-----------|
| `POST` | `/app-results-page/login` | Pública | Body: `PortalLoginRequest` | `PortalLoginResponse` |
| `GET` | `/app-results-page/patient/orders` | Token paciente (`arp_user_access_type=1`) | Query: `page, page_size, search` | `PatientOrdersPaginatedResponse` |
| `GET` | `/app-results-page/enterprise/orders` | Token empresa (`arp_user_access_type=2`) | Query: `page, page_size, search` | `EnterpriseOrdersPaginatedResponse` |

Errores comunes en los endpoints protegidos:
| Código | Causa |
|--------|-------|
| `401` | Token ausente, inválido, expirado, o no pertenece al portal (`portal: true`) |
| `403` | Token válido pero de tipo incorrecto (ej. token de empresa llamando a `/patient/orders`), o cuenta inactiva |
