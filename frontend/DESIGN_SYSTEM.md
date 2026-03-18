# 🌿 Sistema de Diseño PerFinanzas

## Introducción

Este documento define el sistema de diseño visual de **PerFinanzas**, una plataforma de análisis inteligente de crédito hipotecario. La identidad visual se basa en una paleta de colores sostenible derivada del logo de la marca.

---

## 📋 Tabla de Contenidos

1. [Paleta de Colores](#paleta-de-colores)
2. [Variables CSS](#variables-css)
3. [Componentes](#componentes)
4. [Reglas de Aplicación](#reglas-de-aplicación)
5. [Ejemplos de Uso](#ejemplos-de-uso)
6. [Guía Rápida](#guía-rápida)

---

## 🎨 Paleta de Colores

### Jerarquía de Colores - Sistema de Diseño

| Rol Visual | Nombre Variable | Código Hex | Uso Sugerido |
|---|---|---|---|
| **Primario Oscuro** | `verde-bosque` | `#1B5E20` | Títulos de alto contraste, fondos de botones principales, logotipos |
| **Color de Marca** | `verde-hoja` | `#4CAF50` | Bordes de campos activos, anillos de enfoque (focus), elementos de éxito |
| **Acento Vibrante** | `verde-claro` | `#66BB6A` | Estados de hover y énfasis visual sutil |
| **Fondo Suave** | `verde-suave` | `#E8F5E9` | Fondos de tarjetas, alertas positivas, secciones con contraste ligero |
| **Base Limpia** | `blanco` | `#FFFFFF` | Fondo principal de la aplicación, minimalismo |

### Colores Semánticos

| Propósito | Código Hex | Uso |
|---|---|---|
| **Success (Éxito)** | `#4CAF50` | Confirmaciones, mensajes positivos |
| **Warning (Advertencia)** | `#FBA500` | Alertas, precauciones |
| **Error** | `#DC2626` | Errores, validaciones fallidas |
| **Info** | `#0284C7` | Información general |

### Grises de Soporte

| Nivel | Código Hex | Uso |
|---|---|---|
| `--gray-50` | `#F9FAFB` | Fondos muy claros |
| `--gray-100` | `#F3F4F6` | Fondos claros |
| `--gray-200` | `#E5E7EB` | Bordes sutiles |
| `--gray-300` | `#D1D5DB` | Bordes normales |
| `--gray-400` | `#9CA3AF` | Placeholders |
| `--gray-500` | `#6B7280` | Texto secundario |
| `--gray-600` | `#4B5563` | Texto |
| `--gray-700` | `#374151` | Texto oscuro |
| `--gray-900` | `#111827` | Texto muy oscuro |

---

## 🔧 Variables CSS

### Ubicación

Todas las variables están definidas en:

```
frontend/app/globals.css
```

### Declaración

Las variables se declaran en el selector `:root`:

```css
:root {
  /* Base Colors */
  --background: #ffffff;
  --foreground: #171717;

  /* PerFinanzas Color Palette */
  --verde-bosque: #1B5E20;
  --verde-hoja: #4CAF50;
  --verde-claro: #66BB6A;
  --verde-suave: #E8F5E9;
  --blanco: #FFFFFF;

  /* Semantic Colors */
  --success: var(--verde-hoja);
  --warning: #FBA500;
  --error: #DC2626;
  --info: #0284C7;
}
```

### Uso en CSS

```css
.elemento {
  color: var(--verde-bosque);
  background-color: var(--verde-suave);
  border-color: var(--verde-hoja);
}
```

### Uso en Tailwind CSS

Las variables están disponibles como clases de Tailwind:

```html
<!-- Texto -->
<p class="text-verde-bosque">Texto primario oscuro</p>
<p class="text-verde-hoja">Texto marca</p>

<!-- Fondos -->
<div class="bg-verde-suave">Fondo suave</div>
<div class="bg-verde-bosque">Fondo oscuro</div>

<!-- Bordes -->
<div class="border border-verde-hoja">Borde marca</div>

<!-- Anillos (Focus) -->
<input class="focus:ring-verde-hoja">
```

---

## 🧩 Componentes

### Button

**Archivo**: `components/ui/button.tsx`

#### Variantes

```tsx
<Button variant="primary">Primario (verde-hoja)</Button>
<Button variant="secondary">Secundario (verde-bosque)</Button>
<Button variant="outline">Contorno (verde-hoja)</Button>
<Button variant="ghost">Fantasma (verde-bosque)</Button>
```

#### Características

- ✅ Transiciones suaves (200ms)
- ✅ Estados disabled con opacidad
- ✅ Focus rings con verde-hoja
- ✅ Sombras dinámicas al hover

### Input

**Archivo**: `components/ui/input.tsx`

#### Estados

| Estado | Color Borde | Color Focus Ring | Color Texto |
|---|---|---|---|
| Default | `gray-300` | `verde-hoja/15` | `gray-900` |
| Hover | `gray-300` (más oscuro) | `verde-hoja/15` | `gray-900` |
| Focus | `verde-hoja` | `verde-hoja/15` | `gray-900` |
| Error | `red-400` | `red-200` | `gray-900` |
| Disabled | `gray-200` | - | `gray-500` |

#### Características

- ✅ Labels dinámicos con color en focus
- ✅ Iconos con cambio de color en focus
- ✅ Toggle de contraseña integrado
- ✅ Mensajes de error y helper text

### Card

**Archivo**: `components/ui/card.tsx`

#### Variantes

```tsx
<Card variant="default">Fondo blanco limpio</Card>
<Card variant="bordered">Borde gris, hover verde</Card>
<Card variant="elevated">Sombra eco (verde suave)</Card>
<Card variant="soft">Fondo verde-suave, borde verde</Card>
```

### AuthLayout

**Archivo**: `components/auth-layout.tsx`

- Fondo gradiente: `gradient-eco-subtle`
- Logo: `gradient-eco-primary`
- Título: `text-verde-bosque`
- Minimalista y aireado

### AuthLayout Glass

**Archivo**: `components/auth-layout-glass.tsx`

- Fondo gradiente: `gradient-eco-primary`
- Efecto glassmorphism con bordes verdes
- Logo con logo.png
- Contenedor central con sombra eco

---

## 📐 Reglas de Aplicación

### 1. Contraste

> Los textos principales siempre deben ir sobre fondo blanco o verde muy suave para garantizar la legibilidad.

✅ **BIEN**:
```html
<p class="text-verde-bosque bg-white">Texto oscuro sobre blanco</p>
<p class="text-verde-bosque bg-verde-suave">Texto oscuro sobre verde suave</p>
```

❌ **MAL**:
```html
<p class="text-verde-hoja bg-verde-bosque">Contraste insuficiente</p>
<p class="text-white bg-gray-900">Gris puro fuera de la paleta</p>
```

### 2. Interactividad

> Los elementos interactivos (botones, enlaces) deben transicionar suavemente entre verde-hoja y verde-bosque al pasar el cursor.

✅ **BIEN**:
```html
<button class="bg-verde-hoja hover:bg-verde-bosque transition-colors">
  Acción
</button>
<a class="text-verde-bosque hover:text-verde-hoja">Enlace</a>
```

### 3. Minimalismo

> El uso del color verde debe ser estratégico; la interfaz debe sentirse predominantemente blanca y aireada, usando los verdes solo para guiar la atención del usuario.

✅ **Regla de Oro**: 
- **70% Blanco/Gris claro**
- **20% Verdes (énfasis)**
- **10% Otros (errores, warnings)**

### 4. Consistencia

> Todos los iconos, bordes de inputs y sombras deben seguir las tonalidades de gris suave o verde mencionadas, evitando negros puros o colores fuera de la gama ecológica.

---

## 🎯 Ejemplos de Uso

### Formulario Completo

```tsx
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export function LoginForm() {
  return (
    <Card variant="soft">
      <div className="space-y-4">
        <h2 className="text-verde-bosque text-2xl font-bold">
          Iniciar Sesión
        </h2>

        <Input
          label="Correo"
          type="email"
          placeholder="tu@correo.com"
          // El input aplicará automáticamente:
          // - Border: gray-300
          // - Focus ring: verde-hoja/15
          // - Focus border: verde-hoja
        />

        <Input
          label="Contraseña"
          type="password"
          showPasswordToggle={true}
        />

        <Button variant="primary" className="w-full">
          Iniciar Sesión
        </Button>

        <p className="text-gray-600">
          ¿No tienes cuenta?{' '}
          <a href="/register" className="text-verde-bosque hover:text-verde-hoja">
            Regístrate aquí
          </a>
        </p>
      </div>
    </Card>
  );
}
```

### Sección de Éxito

```tsx
<div className="p-4 bg-verde-suave border border-verde-hoja/30 rounded-lg">
  <div className="flex gap-2">
    <CheckCircle className="text-verde-hoja" />
    <div>
      <h3 className="font-semibold text-verde-bosque">
        Operación completada
      </h3>
      <p className="text-sm text-gray-600">
        Tu solicitud ha sido procesada correctamente.
      </p>
    </div>
  </div>
</div>
```

### Enlace Interactivo

```tsx
<Link
  href="/dashboard"
  className="text-verde-bosque hover:text-verde-hoja 
             hover:underline transition-colors duration-200"
>
  Ir al Dashboard
</Link>
```

---

## 📝 Guía Rápida

### Necesito...

**... un botón primario**
```tsx
<Button variant="primary">Acción principal</Button>
```

**... un botón secundario**
```tsx
<Button variant="secondary">Acción secundaria</Button>
```

**... un campo de entrada**
```tsx
<Input label="Nombre" placeholder="Tu nombre" />
```

**... una tarjeta**
```tsx
<Card variant="elevated">Contenido importante</Card>
```

**... un enlace**
```tsx
<a className="text-verde-bosque hover:text-verde-hoja">Enlace</a>
```

**... un texto importante**
```tsx
<p className="text-verde-bosque font-bold">Texto importante</p>
```

**... un fondo suave**
```tsx
<div className="bg-verde-suave p-4 rounded-lg">Contenido</div>
```

**... un focus ring personalizado**
```tsx
<input className="focus:ring-verde-hoja focus:border-verde-hoja" />
```

---

## 🔄 Gradientes Predefinidos

Están disponibles en `globals.css`:

```css
/* Gradiente suave para fondos */
.gradient-eco-subtle {
  @apply bg-gradient-to-br from-white via-white to-verde-suave;
}

/* Gradiente primario (verde) */
.gradient-eco-primary {
  @apply bg-gradient-to-br from-verde-bosque to-verde-hoja;
}

/* Gradiente de acento */
.gradient-eco-accent {
  @apply bg-gradient-to-r from-verde-hoja to-verde-claro;
}
```

---

## 🌟 Sombras Personalizadas

```css
.shadow-eco-sm {
  box-shadow: 0 1px 2px 0 rgba(27, 94, 32, 0.05);
}

.shadow-eco-md {
  box-shadow: 0 4px 6px -1px rgba(27, 94, 32, 0.1),
              0 2px 4px -1px rgba(27, 94, 32, 0.06);
}

.shadow-eco-lg {
  box-shadow: 0 10px 15px -3px rgba(27, 94, 32, 0.1),
              0 4px 6px -2px rgba(27, 94, 32, 0.05);
}
```

---

## ✅ Checklist para Nuevas Características

- [ ] ¿Usa variables CSS definidas en `globals.css`?
- [ ] ¿Respeta la jerarquía de colores (70% blanco, 20% verde, 10% otros)?
- [ ] ¿El contraste cumple con WCAG AA (4.5:1 para texto)?
- [ ] ¿Los elementos interactivos tienen transiciones suaves?
- [ ] ¿Se usan los componentes UI (Button, Input, Card)?
- [ ] ¿Los iconos son consistentes con la paleta verde?
- [ ] ¿El diseño se ve bien en móvil y desktop?
- [ ] ¿Se evitaron colores puros (negro #000, gris #808080)?

---

## 📞 Soporte

Para preguntas sobre el sistema de diseño:

1. Revisar este documento
2. Inspeccionar `frontend/app/globals.css`
3. Revisar los componentes en `frontend/components/ui/`

---

**Última actualización**: Enero 2026
**Versión**: 1.0
**Autor**: PerFinanzas Design System

