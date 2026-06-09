Tengo una API en FastAPI con las siguientes características:

- Base de datos: PostgreSQL (usando SQLAlchemy async)
- Autenticación: JWT token (Bearer)
- Ya existe una tabla `Permissions` con campos: `id`, `p_name`, `p_description`, `p_module`
- Ya existe una tabla `Roles` con campos: `id`, `r_name`, `r_description`
- Ya existe una tabla `role_permissions` (relación muchos a muchos entre Roles y Permissions)
- Ya existe una tabla `user_roles` (relación muchos a muchos entre Users y Roles)
- El usuario actual se obtiene del token JWT y se inyecta mediante `Depends(get_current_user)`

# Estructura actual de endpoints (por tags)

## Tag: Patients
- POST /api/patients/ → crear paciente
- GET /api/patients/ → listar todos
- GET /api/patients/document/{doc_number} → obtener por documento
- GET /api/patients/document/{search_query}/orders → obtener órdenes por documento o número de orden
- GET /api/patients/{id} → obtener un paciente
- PATCH /api/patients/{id} → actualizar paciente

## Tag: Users
- POST /api/users/ → crear usuario
- GET /api/users/ → listar usuarios
- GET /api/users/{usr_id} → obtener detalles
- PATCH /api/users/{usr_id} → actualizar usuario
- POST /api/users/login → login (NO requiere autenticación)
- GET /api/users/permissions/ → listar permisos
- GET /api/users/permissions/tree → listar permisos por módulo
- PATCH /api/users/permissions/{permission_id} → actualizar permiso
- DELETE /api/users/permissions/{permission_id} → eliminar permiso
- GET /api/users/roles/ → listar roles

## Otros tags (si existen)
- Enterprises
- Contracts

# Requerimiento

Implementar un sistema **RBAC completo** donde **cada endpoint** (excepto login) requiera un permiso específico basado en el tag y la acción.

## Tareas a realizar:

### 1. Definir y crear permisos faltantes
- Generar un script SQL INSERT con TODOS los permisos necesarios siguiendo el formato `Module:Action` (ej: `Patients:Create`, `Users:List`)
- Asegurar que no haya duplicados
- Cada permiso debe tener su `p_description` clara

### 2. Crear dependencia de autorización
Crear una función `require_permission(permission_name: str)` que:
- Reciba el nombre del permiso (ej: `"Patients:Create"`)
- Verifique que el usuario actual (desde JWT) tenga ese permiso (a través de sus roles)
- Si no lo tiene, lance `HTTPException(status_code=403, detail="Insufficient permissions")`
- Use caché en memoria (ej: `lru_cache` o `aiocache`) para no consultar la BD en cada request

### 3. Proteger cada endpoint
Modificar cada endpoint (excepto login) para que incluya `Depends(require_permission("Module:Action"))`

Ejemplo:
```python
@router.post("/", dependencies=[Depends(require_permission("Patients:Create"))])
async def create_patient(...):
    ...
4. Middleware o logger opcional
Agregar logging que registre: usuario, endpoint, permiso requerido, si fue autorizado o no

5. Script de seed inicial
Crear un script que:

Inserte los permisos (si no existen)

Cree roles por defecto: Admin (todos los permisos), Doctor (solo Patients:List, Patients:GetOne, Patients:Update), Viewer (solo Patients:List)

Asigne permisos a cada rol

6. Endpoint auxiliar (opcional)
Crear GET /api/users/me/permissions que devuelva todos los permisos del usuario autenticado

7. Actualizar modelos (si es necesario)
Asegurar que User, Role, Permission tengan relaciones correctas en SQLAlchemy.

Restricciones técnicas:
Usar async/await en toda la capa de BD

No usar librerías externas de RBAC (implementar manual)

Escribir pruebas unitarias para la dependencia require_permission

Entregables esperados:
Código completo de dependencies.py con require_permission

Script SQL/ Python para seed de permisos y roles

Endpoints modificados con la nueva dependencia

Ejemplo de cómo agregar un nuevo endpoint protegido en el futuro

Archivo tests/test_rbac.py con casos básicos

Formato de salida:
Explicación paso a paso

Código completo listo para copiar y pegar

Comentarios en español o inglés (consistente)

text

---

## 📌 Cómo usar este prompt

Copia todo el bloque de código markdown anterior y pégalo en:

- **Cursor Composer** (modo normal o Agent)
- **ChatGPT / Claude**
- **Copilot Chat**
- **Cualquier agente de IA que tenga contexto de tu proyecto**

---

## 🧰 Extra: Prompt más corto para cambios específicos

Si solo quieres que tu agente **proteja un endpoint nuevo** que acabas de crear:

```markdown
Protege el endpoint `PATCH /api/enterprises/{enterprise_id}` con el permiso `Enterprises:Update`. Usa la función `require_permission` existente en `dependencies.py`. Dame solo el código modificado del router.