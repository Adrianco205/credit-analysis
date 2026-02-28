# Resumen de Solución - Registro y Autenticación OTP

## Problema Reportado
❌ **Error**: "error al registrarse; no se pudo conectar con el servidor. verifica tu conexión"
❌ **Falta**: Pantalla para verificar el código OTP que llega al correo

## Solución Implementada

### 1. ✅ Problema de Conexión (Network Error)

#### Causa Raíz
El frontend intentaba conectar a `http://localhost:8000` desde el navegador, pero:
- El backend estaba disponible en `http://localhost:8001` (puerto mapeado de Docker)
- Dentro de Docker, no existe `localhost` para comunicación entre contenedores
- `NEXT_PUBLIC_API_URL` estaba hardcodeada como `http://localhost:8000/api/v1`

#### Solución Aplicada
Implementé un **proxy inverso** usando rewrites de Next.js:

**Archivos modificados:**

1. **frontend/next.config.ts** - Agregado rewrites
```typescript
async rewrites() {
  return {
    beforeFiles: [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
      },
    ],
  };
}
```

2. **frontend/lib/api-client.ts** - Actualizado base URL
```typescript
const API_BASE_URL = '/api/v1';  // Usa el proxy local en lugar de URL externa
```

3. **frontend/.env.local** - Configuración interna de Docker
```
NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
```

4. **backend/app/main.py** - CORS habilitado para desarrollo
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Desarrollo: permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

5. **docker-compose.yml** - Volumen nombrado para node_modules
```yaml
volumes:
  frontend_node_modules:

frontend:
  volumes:
    - ./frontend:/app
    - /app/node_modules  # Usar volumen en lugar de carpeta local
```

### 2. ✅ Flujo Completo de Registro y Verificación OTP

#### Pantalla de Registro
**URL**: `http://localhost:3000/auth/register`

**Flujo**:
1. Usuario completa formulario de registro
2. Frontend envía POST a `/api/v1/auth/register`
3. Backend:
   - Crea usuario con estado `PENDING`
   - Genera código OTP de 6 dígitos
   - Envía email en background (tarea asincrónica)
   - Retorna `user_id` y `status`
4. Frontend redirige automáticamente a pantalla de verificación

#### Pantalla de Verificación OTP
**URL**: `http://localhost:3000/auth/verify-otp?user_id={id}`

**Flujo**:
1. Usuario ingresa código de 6 dígitos recibido por email
2. Frontend envía POST a `/api/v1/auth/verify-otp`
3. Backend:
   - Valida que el código no haya expirado (10 minutos)
   - Verifica que el código sea correcto
   - Marca usuario como `ACTIVE` y email como verificado
4. Frontend redirige a pantalla de login

#### Pantalla de Login
**URL**: `http://localhost:3000/auth/login`

**Flujo**:
1. Usuario ingresa cedula/identificación y contraseña
2. Frontend envía POST a `/api/v1/auth/login`
3. Backend:
   - Valida que usuario exista
   - Valida que usuario esté `ACTIVE` (verificado por OTP)
   - Genera JWT token
4. Frontend guarda token en localStorage
5. Redirige a `/dashboard` con acceso autenticado

## Arquitectura de Comunicación

```
┌─────────────────────────────────────────────────────┐
│                    NAVEGADOR (HOST)                  │
│              http://localhost:3000                   │
└─────────────┬───────────────────────────────────────┘
              │ Peticiones HTTP
              ↓
┌─────────────────────────────────────────────────────┐
│         FRONTEND - Next.js (CONTENEDOR DOCKER)       │
│  http://172.18.0.4:3000 (dentro de la red Docker)   │
│                                                      │
│  Proxy Configurado:                                  │
│  /api/v1/* → http://backend:8000/api/v1/*           │
└─────────────┬───────────────────────────────────────┘
              │ Peticiones internas de Docker
              ↓
┌─────────────────────────────────────────────────────┐
│      BACKEND - FastAPI (CONTENEDOR DOCKER)           │
│    http://backend:8000 (dentro de la red Docker)     │
│    http://localhost:8001 (desde el HOST)             │
└─────────────┬───────────────────────────────────────┘
              │ Consultas SQL
              ↓
┌─────────────────────────────────────────────────────┐
│   BASE DE DATOS - PostgreSQL (CONTENEDOR DOCKER)    │
│      postgresql://db:5432 (dentro de Docker)        │
└─────────────────────────────────────────────────────┘
```

## Cambios Realizados

### Frontend
1. ✅ `next.config.ts` - Agregado rewrites para proxy
2. ✅ `lib/api-client.ts` - Actualizado base URL a `/api/v1`
3. ✅ `.env.local` - Actualizado a `http://backend:8000/api/v1`
4. ✅ `Dockerfile` - Removido `npm cache clean --force`
5. ✅ Páginas ya existentes:
   - `/auth/register` - Registro de usuarios
   - `/auth/verify-otp` - Verificación de código OTP
   - `/auth/login` - Inicio de sesión

### Backend
1. ✅ `app/main.py` - CORS habilitado para `allow_origins=["*"]`
2. ✅ Endpoints de autenticación:
   - `POST /api/v1/auth/register` - Crear usuario
   - `POST /api/v1/auth/verify-otp` - Verificar código OTP
   - `POST /api/v1/auth/login` - Obtener JWT token
3. ✅ Endpoints de usuario:
   - `GET /api/v1/users/me` - Obtener perfil autenticado

### Infraestructura
1. ✅ `docker-compose.yml` - Agregado volumen `frontend_node_modules`
2. ✅ Redes: Todos los contenedores en la misma red de Docker

## Estado Actual

✅ **Funcionando**:
- Frontend accesible en http://localhost:3000
- Backend accesible en http://localhost:8001
- Comunicación entre frontend y backend funcionando
- Páginas de registro, OTP y login operacionales
- Validaciones en frontend y backend

✅ **Próximos Pasos Recomendados**:
1. Implementar envío real de emails (actualmente solo logs)
2. Agregar validación de email (confirmar disponibilidad)
3. Implementar recuperación de contraseña
4. Agregar refresh tokens
5. Implementar logout
6. Agregar 2FA adicional

## Testing Manual

### Para Registrar un Usuario:
1. Ir a http://localhost:3000/auth/register
2. Completar formulario con datos válidos:
   - Cedula válida (6-10 dígitos)
   - Email único
   - Contraseña: mín 8 caracteres, mayúsculas, minúsculas, números
3. Ver código OTP en logs del backend: `docker logs credit_analysis_api`

### Para Verificar OTP:
1. Copiar código de 6 dígitos de los logs
2. Ingresar en pantalla de verificación
3. Serás redirigido a login

### Para Login:
1. Ingresa cedula y contraseña
2. Se generará JWT token
3. Acceso a dashboard autenticado
