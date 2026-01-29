# 🌿 EcoFinanzas Frontend

Frontend de la plataforma EcoFinanzas construido con Next.js 16, React 19, Tailwind CSS y TypeScript.

## 🚀 Stack Tecnológico

- **Framework**: Next.js 16.1.4 (App Router)
- **UI Library**: React 19.2.3
- **Styling**: Tailwind CSS 4
- **Forms**: React Hook Form + Zod
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Notifications**: Sonner
- **Language**: TypeScript 5

## 📦 Instalación

### 1. Instalar dependencias

```bash
cd frontend/
npm install
```

### 2. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar con la URL del backend
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Ejecutar en desarrollo

```bash
npm run dev
```

La aplicación estará disponible en: `http://localhost:3000`

## 📁 Estructura del Proyecto

```
frontend/
├── app/
│   ├── layout.tsx              # Layout principal con Toaster
│   ├── page.tsx                # Landing page
│   ├── auth/
│   │   ├── login/
│   │   │   └── page.tsx        # Página de login
│   │   ├── register/
│   │   │   └── page.tsx        # Página de registro
│   │   └── verify-otp/
│   │       └── page.tsx        # Verificación OTP
│   └── dashboard/
│       └── page.tsx            # Dashboard (temporal)
├── components/
│   ├── auth-layout.tsx         # Layout de autenticación
│   └── ui/
│       ├── button.tsx          # Componente Button
│       ├── card.tsx            # Componente Card
│       └── input.tsx           # Componente Input
├── lib/
│   ├── api-client.ts           # Cliente Axios configurado
│   ├── utils.ts                # Utilidades generales
│   └── validations.ts          # Schemas de Zod
├── types/
│   └── api.ts                  # Tipos TypeScript de la API
└── package.json
```

## 🎨 Paleta de Colores

Basada en el logo de EcoFinanzas:

```css
--verde-bosque: #1B5E20;    /* Verde oscuro - Textos, iconos */
--verde-hoja: #4CAF50;      /* Verde medio - Botones primarios */
--verde-claro: #66BB6A;     /* Verde hover */
--verde-suave: #E8F5E9;     /* Verde backgrounds sutiles */
```

## 🔐 Flujo de Autenticación

### 1. Registro
- Formulario completo con validación Zod
- Campos: nombres, apellidos, identificación, email, teléfono, género, contraseña
- Envío de OTP al correo electrónico
- Redirección automática a verificación

### 2. Verificación OTP
- Input de 6 dígitos
- Countdown timer de 10 minutos
- Manejo de expiración

### 3. Login
- Autenticación por identificación (cédula) y contraseña
- JWT almacenado en localStorage
- Redirección al dashboard

## 🧩 Componentes UI

### Button
```tsx
<Button 
  variant="primary | secondary | outline | ghost"
  size="sm | md | lg"
  isLoading={false}
  leftIcon={<Icon />}
>
  Texto
</Button>
```

### Input
```tsx
<Input
  label="Etiqueta"
  type="text"
  placeholder="Placeholder"
  leftIcon={<Icon />}
  error="Mensaje de error"
  helperText="Texto de ayuda"
  {...register('fieldName')}
/>
```

## 📡 Cliente API

```typescript
import { apiClient } from '@/lib/api-client';

// Login
await apiClient.login({
  identificacion: '1234567890',
  password: 'Password123'
});

// Register
await apiClient.register({
  nombres: 'Juan',
  primer_apellido: 'Pérez',
  // ... otros campos
});
```

## 🌐 Rutas Disponibles

- `/` - Landing page
- `/auth/login` - Iniciar sesión
- `/auth/register` - Crear cuenta
- `/auth/verify-otp?user_id=XXX` - Verificar OTP
- `/dashboard` - Dashboard (requiere autenticación)

## 📄 Licencia

Propietario - EcoFinanzas © 2026
