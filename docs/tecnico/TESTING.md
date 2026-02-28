# Guía de Prueba - Flujo de Registro y Verificación OTP

## Estado Actual
✅ Frontend ejecutándose en http://localhost:3000
✅ Backend ejecutándose en http://localhost:8001 (8000 interno)
✅ Base de datos funcionando
✅ Proxy de API configurado en Next.js

## Flujo Completo de Registro

### 1. Registro de Usuario
- Ir a http://localhost:3000/auth/register
- Completar el formulario con los siguientes datos de ejemplo:
  - **Nombres**: Juan Carlos
  - **Primer Apellido**: García
  - **Segundo Apellido**: Martínez
  - **Tipo de Identificación**: CC
  - **Número de Identificación**: 1234567890
  - **Correo**: test@example.com
  - **Teléfono**: 3001234567
  - **Género**: Masculino
  - **Contraseña**: Test123456
  - **Confirmar Contraseña**: Test123456
  - Aceptar términos y condiciones

### 2. Verificación de OTP
Después de registrarse, el usuario será redirigido automáticamente a:
- http://localhost:3000/auth/verify-otp?user_id={user_id}

En esta página el usuario debe:
- Ingresar el código de 6 dígitos que se envía al correo
- El código expira en 10 minutos
- Después de verificar, será redirigido a /auth/login

### 3. Login
- Ir a http://localhost:3000/auth/login
- Ingresar correo y contraseña
- Acceso al dashboard en http://localhost:3000/dashboard

## Cambios Realizados

### 1. Docker Compose (docker-compose.yml)
- ✅ Agregado volumen nombrado `frontend_node_modules` para preservar dependencias npm en Docker
- ✅ Configurado correctamente el mapeo de puertos

### 2. Frontend (.env.local)
- ✅ Actualizado NEXT_PUBLIC_API_URL a `http://backend:8000/api/v1` para conexión dentro de Docker

### 3. Frontend (next.config.ts)
- ✅ Agregado rewrites para crear un proxy de `/api/v1` hacia el backend
- ✅ Permite que las peticiones desde el navegador se redireccionen internamente

### 4. Frontend (lib/api-client.ts)
- ✅ Actualizado API_BASE_URL a `/api/v1` para usar el proxy local

### 5. Frontend (Dockerfile)
- ✅ Removido `npm cache clean --force` para preservar node_modules
- ✅ Simplificado comando de inicio a `npm run dev`

### 6. Backend (app/main.py)
- ✅ Actualizado CORS para permitir `allow_origins=["*"]` en desarrollo
- Esto permite que peticiones desde cualquier origen sean aceptadas

## Solución de Problemas

### Error: "No se pudo conectar con el servidor"
**Causa**: Frontend no puede comunicarse con backend
**Solución**: 
1. Verificar que todos los contenedores estén corriendo: `docker ps`
2. Revisar logs del backend: `docker logs credit_analysis_api`
3. Revisar logs del frontend: `docker logs credit_analysis_frontend`

### Error: "El código OTP ha expirado"
**Causa**: El código expira después de 10 minutos
**Solución**: Registrarse nuevamente para obtener un nuevo código

### Error: "Usuario ya registrado"
**Causa**: El email o identificación ya existe en la base de datos
**Solución**: Usar diferentes valores de correo e identificación

## Próximos Pasos
- [ ] Implementar envío de email de OTP real (actualmente solo imprime en logs)
- [ ] Agregar validaciones adicionales en el servidor
- [ ] Implementar refresh tokens
- [ ] Agregar recuperación de contraseña
