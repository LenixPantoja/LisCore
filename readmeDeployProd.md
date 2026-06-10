# Despliegue en Producción — LisCore API

Guía completa para construir la imagen Docker de la API LisCore desde Windows y desplegarla en un servidor Linux.

---

## Requisitos del Servidor Linux

- **Docker Engine** v24+ y **Docker Compose** v2+
- **Git** (para clonar el repositorio)
- **Red Docker** `clinizad_network` creada
- **PostgreSQL** accesible desde el servidor (puede estar en otro host)
- Puertos abiertos: `8000` (API), `9000:9001` (MinIO), `3000` (Gotenberg)

---

## 1. Preparar el entorno en Linux

```bash
# Conectarse al servidor
ssh usuario@IP_DEL_SERVIDOR

# Crear la red Docker si no existe
docker network create liscore_network

# Crear directorio para la aplicación
mkdir -p /opt/liscore
cd /opt/liscore
```

---

## 2. Opción A — Construir la imagen directo en Linux

```bash
# Clonar el repositorio
git clone https://github.com/LenixPantoja/LisCore.git .
# O si ya tienes los archivos, súbelos por SCP/RSYNC

# Crear archivo .env con variables de producción
nano .env
```

Ejemplo de `.env` para producción:

```env
# Base de datos
DB_HOST=IP_DEL_POSTGRES
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=contraseña_segura
DB_NAME=LiscoreDB
APP_NAME=LiscoreDB

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=contraseña_minio
MINIO_SECURE=False
MINIO_GRAPHICS_BUCKET=graphics
MINIO_SIGNATURES_BUCKET=signatures
MINIO_ANNEXE_RESULT_BUCKET=annexedresults
MINIO_PRESIGNED_EXPIRES_HOURS=24

# Gotenberg
GOTENBERG_URL=http://gotenberg:3000

# WhatsApp (Evolution API)
WHATSAPP_BASE_URL=http://localhost:11300
WHATSAPP_INSTANCE_ID=enviores
WHATSAPP_API_KEY=749E922F3301-4DAB-9B6A-B1CBEBE58500

# Email
GMAIL_SENDER=envioresultados@clinizad.com
GMAIL_APP_PASSWORD=pjsb szfp tctr xeci
```

> ⚠️ **NUNCA** subas el `.env` al repositorio. Está en `.dockerignore` y `.gitignore`.

### Construir y levantar

```bash
# Construir la imagen
docker compose build

# O usar caché de Docker Hub (ver Opción B)

# Levantar todos los servicios
docker compose up -d

# Verificar logs
docker compose logs -f api

# Ver estado de salud
docker inspect --format='{{.State.Health.Status}}' lis_core_api
```

---

## 3. Opción C — Construir imagen en Windows y copiarla directamente a Linux (RECOMENDADA)

Esta es la forma **más rápida y directa**. NO necesitas Docker Hub ni internet en el servidor.

### En Windows (tu máquina local)

```powershell
# 1. Ir a la carpeta del proyecto
cd d:\Mis Proyectos\CoreLab\Backend\Backend\LisCore

# 2. Construir la imagen (ya la tienes lista)
docker build -t lis_core_api:prod .

# 3. Exportar la imagen a un archivo .tar
docker save lis_core_api:prod -o lis_core_api_prod.tar

# 4. Verificar el tamaño del archivo
dir lis_core_api_prod.tar
```

### Copiar el archivo .tar al servidor Linux

```powershell
# Desde PowerShell en Windows (sustituye usuario e IP)
scp .\lis_core_api_prod.tar usuario@IP_DEL_SERVIDOR:/opt/liscore/
```

> Si no tienes `scp`, usa WinSCP, FileZilla o cualquier cliente SFTP.

### En el servidor Linux

```bash
# 1. Ir al directorio donde copiaste el .tar
cd /opt/liscore

# 2. Cargar la imagen en Docker
docker load -i lis_core_api_prod.tar

# 3. Verificar que se cargó correctamente
docker images | grep lis_core_api

# 4. Crear el archivo .env (ver ejemplo en sección 2)
nano .env

# 5. Crear o copiar docker-compose.yml (ver sección 4)
nano docker-compose.yml

# 6. Levantar todos los servicios
docker compose up -d

# 7. Verificar que todo funciona
docker ps
docker inspect --format='{{.State.Health.Status}}' lis_core_api
```

### Ventajas de este método
- ✅ **Sin necesidad de Docker Hub** ni cuenta externa
- ✅ **Sin depender de internet** en el servidor (solo necesitas SCP/SSH)
- ✅ **Transferencia única** — la imagen completa viaja en un solo archivo
- ✅ **Rápido** — `scp` transferirá ~378MB (el tamaño de la imagen comprimida)
- ✅ **Ideal para servidores sin acceso público a internet**

> 💡 **Tip**: Para reducir el tamaño del .tar antes de copiarlo, puedes comprimirlo:
> ```powershell
> # En Windows, comprimir
> Compress-Archive -Path lis_core_api_prod.tar -DestinationPath lis_core_api_prod.zip
> 
> # En Linux, descomprimir y cargar
> unzip lis_core_api_prod.zip
> docker load -i lis_core_api_prod.tar
> ```

---

## 4. Opción B — Construir imagen en Windows y subirla a Docker Hub

> Útil si quieres centralizar la imagen en un registro accesible desde múltiples servidores.

### En Windows (tu máquina local)

```powershell
# 1. Construir la imagen
cd d:\Mis Proyectos\CoreLab\Backend\Backend\LisCore
docker build -t lis_core_api:prod .

# 2. Etiquetar para Docker Hub
docker tag lis_core_api:prod tuusuario/lis_core_api:latest

# 3. Iniciar sesión en Docker Hub
docker login

# 4. Subir la imagen
docker push tuusuario/lis_core_api:latest
```

### En el servidor Linux

```bash
# 1. Iniciar sesión en Docker Hub
docker login

# 2. Descargar la imagen
docker pull tuusuario/lis_core_api:latest

# 3. Etiquetar para uso local
docker tag tuusuario/lis_core_api:latest lis_core_api:prod

# 4. Crear docker-compose.yml y .env (ver secciones 4 y 5)
# 5. Levantar los servicios
docker compose up -d
```

---

## 4. docker-compose.yml para producción

> ⚠️ **IMPORTANTE**: Si tu PostgreSQL no está en contenedor, **NO incluyas** un servicio `postgres` en el compose. La API se conecta al `DB_HOST` definido en `.env`.
>
> ⚠️ **CRÍTICO**: 
> 1. Usa `image:` NO `build:` para que Docker use la imagen pre-cargada con `docker load`.
> 2. Agrega `pull_policy: never` para que Docker Compose **no intente descargar** la imagen de internet.
> 3. **SIEMPRE carga la imagen con `docker load -i` ANTES de ejecutar `docker compose up`**.

```yaml
services:
  # Almacenamiento de Objetos (MinIO)
  minio:
    image: minio/minio
    container_name: lis_core_minio
    restart: always
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-admin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-password}
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"        # API de MinIO (accesible desde el host)
      - "9001:9001"        # Consola web de MinIO
    networks:
      - liscore_network

  # Motor de PDF (Gotenberg)
  gotenberg:
    image: gotenberg/gotenberg:8
    container_name: gotenberg_pdf_api
    restart: always
    environment:
      - CHROMIUM_DISABLE_WEB_SECURITY=true
    ports:
      - "3000:3000"        # API de Gotenberg (accesible desde el host)
    networks:
      - liscore_network

  # API Backend (FastAPI)
  api:
    image: lis_core_api:prod
    pull_policy: never             # 👈 Impide que busque la imagen en internet
    container_name: lis_core_api
    restart: always
    depends_on:
      - minio
      - gotenberg
    env_file:
      - .env
    environment:
      GOTENBERG_URL: http://gotenberg:3000
      MINIO_ENDPOINT: minio:9000
    ports:
      - "8000:8000"
    networks:
      - liscore_network

networks:
  liscore_network:
    external: true

volumes:
  minio_data:
```

---

## 5. Pasos finales en el servidor

```bash
# 1. Asegúrate de tener la red creada
docker network create clinizad_network 2>/dev/null

# 2. Levantar todo
docker compose up -d

# 3. Verificar que los contenedores estén corriendo
docker ps

# 4. Verificar el healthcheck de la API (espera ~40 segundos)
docker inspect --format='{{.State.Health.Status}}' lis_core_api
# Debería mostrar: healthy

# 5. Probar que responde
curl http://localhost:8000/api/health
# Debería devolver un { "status": "ok" } o similar

# 6. Ver logs en vivo
docker compose logs -f --tail=50

# 7. Detener todo
docker compose down
```

---

## 6. Comandos útiles para mantenimiento

```bash
# Ver uso de recursos
docker stats

# Reconstruir solo la API sin usar caché
docker compose build --no-cache api

# Ver logs de un contenedor específico
docker logs -f lis_core_api

# Acceder al shell del contenedor
docker exec -it lis_core_api /bin/bash

# Ejecutar migraciones de base de datos manualmente
docker exec lis_core_api alembic upgrade head

# Reiniciar un contenedor
docker compose restart api

# Ver imágenes disponibles
docker images

# Eliminar imágenes no utilizadas
docker image prune -a
```

---

## 7. Resolución de problemas

### La API no inicia (exit code 1)

```bash
# Ver logs completos
docker compose logs api

# Causas comunes:
# - El .env no está creado o tiene variables incorrectas
# - PostgreSQL no es accesible desde el contenedor (revisar DB_HOST)
# - La red clinizad_network no existe
```

### Healthcheck falla siempre

```bash
# Ver estado
docker inspect --format='{{.State.Health}}' lis_core_api

# Posible causa: el endpoint /api/health no existe en tu aplicación
# El healthcheck está configurado para ese path, pero si tu app
# no lo expone, DEBES crear un endpoint GET /api/health que
# devuelva 200 OK.
```

### Error de conexión a PostgreSQL

- Verifica que el `DB_HOST` en `.env` sea la IP real del servidor PostgreSQL
- Si PostgreSQL está en otro servidor, asegúrate que el firewall permita el puerto 5432
- Si PostgreSQL está en un contenedor, debe estar conectado a `clinizad_network`

### MinIO no responde

```bash
# Verificar que el contenedor esté corriendo
docker ps | grep minio

# Probar conexión desde la API
docker exec lis_core_api python -c "from minio import Minio; c = Minio('minio:9000', access_key='admin', secret_key='password', secure=False); print(c.list_buckets())"
```

---

## 8. Arquitectura de despliegue recomendada

```
Servidor Linux
├── Docker Engine
│   ├── Contenedor: lis_core_api        (FastAPI:8000)
│   ├── Contenedor: lis_core_minio      (MinIO:9000/9001)
│   └── Contenedor: gotenberg_pdf_api   (Gotenberg:3000)
│
├── PostgreSQL ──── Host externo o contenedor
├── Nginx ───────── Reverse proxy (opcional, para HTTPS)
└── Firewall ────── Puerto 8000 expuesto
```

---

## 9. Referencia de variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `DB_HOST` | ✅ | IP del servidor PostgreSQL |
| `DB_PORT` | ✅ | Puerto de PostgreSQL (default: 5432) |
| `DB_USER` | ✅ | Usuario de PostgreSQL |
| `DB_PASSWORD` | ✅ | Contraseña de PostgreSQL |
| `DB_NAME` | ✅ | Nombre de la base de datos |
| `MINIO_ENDPOINT` | ✅ | Endpoint de MinIO (ej: `minio:9000`) |
| `MINIO_ACCESS_KEY` | ✅ | Access key de MinIO |
| `MINIO_SECRET_KEY` | ✅ | Secret key de MinIO |
| `MINIO_SECURE` | ✅ | `True` o `False` |
| `MINIO_GRAPHICS_BUCKET` | ✅ | Bucket de gráficos |
| `MINIO_SIGNATURES_BUCKET` | ✅ | Bucket de firmas |
| `MINIO_PRESIGNED_EXPIRES_HOURS` | ✅ | Horas de expiración de URLs prefirmadas |
| `GOTENBERG_URL` | ❌ | URL de Gotenberg (default: `http://localhost:3000`) |
| `WHATSAPP_BASE_URL` | ❌ | URL de Evolution API |
| `WHATSAPP_INSTANCE_ID` | ❌ | ID de instancia de WhatsApp |
| `WHATSAPP_API_KEY` | ❌ | API Key de WhatsApp |
| `GMAIL_SENDER` | ❌ | Correo remitente para envío de resultados |
| `GMAIL_APP_PASSWORD` | ❌ | App password de Gmail |

---

> 📌 **Última actualización:** 10 de junio de 2026
> 
> 📌 **Proyecto:** LisCore — Sistema de Gestión de Laboratorio Clínico