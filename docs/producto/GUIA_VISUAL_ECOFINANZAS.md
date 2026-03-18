# 🌿 Guía Visual - PerFinanzas Paleta de Colores

## Vista Previa de Componentes

### Página de Login

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│             [LOGO - Fondo: gradient-eco-primary]   │
│                                                     │
│               PerFinanzas                          │
│          (color: text-verde-bosque)                │
│                                                     │
│           Accede a tu cuenta                       │
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │ Número de Identificación                 [×]│ │
│  │ ┌────────────────────────────────────────┐  │ │
│  │ │ [placeholder gris-400]    border-focus │  │ │
│  │ │                          verde-hoja    │  │ │
│  │ └────────────────────────────────────────┘  │ │
│  │                                              │ │
│  │ Contraseña                                 │ │
│  │ ┌────────────────────────────────────────┐  │ │
│  │ │ ••••••••••                  [👁]      │  │ │
│  │ └────────────────────────────────────────┘  │ │
│  │ ¿Olvidaste tu contraseña?                   │ │
│  │ (color: text-verde-bosque, hover: hoja)    │ │
│  │                                              │ │
│  │  ┌─────────────────────────────────────┐   │ │
│  │  │  INICIAR SESIÓN        →            │   │ │
│  │  │ bg: verde-hoja, hover: verde-bosque │   │ │
│  │  └─────────────────────────────────────┘   │ │
│  │                                              │ │
│  │ ¿No tienes cuenta? Regístrate aquí         │ │
│  │                 (verde-bosque/hoja)        │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│    © 2026 PerFinanzas. Todos los derechos        │
│                                                     │
└─────────────────────────────────────────────────────┘

FONDO: gradient-eco-subtle (white → verde-suave)
```

---

### Página de Registro

```
┌──────────────────────────────────────────────┐
│                                              │
│  IDENTIDAD PERSONAL  👤 (verde-bosque)      │
│  ──────────────────────────────────────────  │
│  ┌──────────────────────────────────────┐  │
│  │ Nombres Completos                    │  │
│  │ ┌────────────────────────────────┐   │  │
│  │ │ Ej: Juan Carlos                │   │  │
│  │ └────────────────────────────────┘   │  │
│  │                                       │  │
│  │ Primer Apellido    │ Segundo Apellido│  │
│  │ ┌──────────────┐   │ ┌──────────────┐│  │
│  │ │ García       │   │ │ Martínez     ││  │
│  │ └──────────────┘   │ └──────────────┘│  │
│  └──────────────────────────────────────┘  │
│                                              │
│  DOCUMENTO 🗂️ (verde-bosque)                │
│  ──────────────────────────────────────────  │
│  ┌────────────────────────────────────────┐ │
│  │ Tipo        │ Número                    │ │
│  │ ┌─────────┐ │ ┌────────────────────┐   │ │
│  │ │ ▼ CC    │ │ │ 1234567890         │   │ │
│  │ └─────────┘ │ └────────────────────┘   │ │
│  │             │                           │ │
│  │ Confirmar Número                        │ │
│  │ ┌──────────────────────────────────────┐│ │
│  │ │ 1234567890                           ││ │
│  │ └──────────────────────────────────────┘│ │
│  └────────────────────────────────────────┘ │
│                                              │
│  CONTACTO 📧 (verde-bosque)                 │
│  ──────────────────────────────────────────  │
│  [Correo electrónico - Confirmar correo]   │
│  [Teléfono - Confirmar teléfono]           │
│                                              │
│  UBICACIÓN 📍 (verde-bosque)                │
│  ──────────────────────────────────────────  │
│  [CitySearch con focus: verde-hoja]        │
│  [Género selector with verde-bosque icons] │
│                                              │
│  CONTRASEÑA 🔒 (verde-bosque)              │
│  ──────────────────────────────────────────  │
│  [Password con toggle - verde-hoja hover]  │
│  [Confirmar contraseña]                    │
│                                              │
│  ☑ Acepto los términos y condiciones      │
│    (checkbox: verde-hoja)                  │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  CREAR CUENTA         →                │ │
│  │ gradient: bosque → hoja, shadow hover  │ │
│  │  ¿Ya tienes cuenta? Inicia sesión      │ │
│  └────────────────────────────────────────┘ │
│                                              │
└──────────────────────────────────────────────┘
```

---

### Tarjetas (Cards)

```
VARIANTE: DEFAULT
┌──────────────────────────────────────┐
│ Contenido blanco limpio              │
└──────────────────────────────────────┘


VARIANTE: BORDERED
┌──────────────────────────────────────┐
│ Contenido blanco con borde gris      │
│ On hover: borde → verde-hoja/50      │
└──────────────────────────────────────┘


VARIANTE: ELEVATED
┌────────────────────────────────────────┐
│ Contenido blanco con sombra eco lg     │
│ shadow: verde-bosque/20 (no gris)      │
└────────────────────────────────────────┘


VARIANTE: SOFT (NUEVA)
┌──────────────────────────────────────┐
│ bg-verde-suave con borde verde-hoja   │
│ Ideal para llamados a la acción      │
└──────────────────────────────────────┘
```

---

### Botones

```
┌─────────────────────────────────────────┐
│ VARIANTE: PRIMARY                       │
│  ┌───────────────────────────────────┐  │
│  │ Acción Primaria        →          │  │
│  │ bg: verde-hoja                    │  │
│  │ hover: verde-bosque               │  │
│  │ focus: ring verde-hoja            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ VARIANTE: SECONDARY                     │
│  ┌───────────────────────────────────┐  │
│  │ Acción Secundaria                 │  │
│  │ bg: verde-bosque                  │  │
│  │ hover: verde-bosque (más oscuro)  │  │
│  │ focus: ring verde-bosque          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ VARIANTE: OUTLINE                       │
│  ┌───────────────────────────────────┐  │
│  │ Acción Contorno                   │  │
│  │ border: verde-hoja                │  │
│  │ text: verde-hoja                  │  │
│  │ hover: bg-verde-suave             │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ VARIANTE: GHOST                         │
│  ┌───────────────────────────────────┐  │
│  │ Acción Fantasma                   │  │
│  │ text: verde-bosque                │  │
│  │ hover: bg-verde-suave             │  │
│  │ no borde                          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

### Formularios - Inputs

```
ESTADO: NORMAL
┌──────────────────────────────┐
│ Label (text-gray-700)        │
│ ┌──────────────────────────┐ │
│ │ placeholder: gray-400    │ │
│ │ border: gray-300         │ │
│ └──────────────────────────┘ │
│ Helper text: text-gray-500   │
└──────────────────────────────┘


ESTADO: HOVER
┌──────────────────────────────┐
│ Label (text-gray-700)        │
│ ┌──────────────────────────┐ │
│ │ border: gray-300 (+)     │ │
│ │ bg: gray-50/50           │ │
│ └──────────────────────────┘ │
└──────────────────────────────┘


ESTADO: FOCUS
┌──────────────────────────────┐
│ Label (text-verde-hoja)      │
│ ┌──────────────────────────┐ │
│ │ border: verde-hoja       │ │
│ │ ring: verde-hoja/15      │ │
│ │ bg: white                │ │
│ └──────────────────────────┘ │
│ Helper text: text-gray-500   │
└──────────────────────────────┘


ESTADO: ERROR
┌──────────────────────────────┐
│ Label (text-red-600)         │
│ ┌──────────────────────────┐ │
│ │ border: red-400          │ │
│ │ ring: red-200            │ │
│ │ bg: red-50/30            │ │
│ │ Error message: red-600   │ │
│ └──────────────────────────┘ │
└──────────────────────────────┘


ESTADO: DISABLED
┌──────────────────────────────┐
│ Label (text-gray-400)        │
│ ┌──────────────────────────┐ │
│ │ border: gray-200         │ │
│ │ bg: gray-100             │ │
│ │ text: gray-500           │ │
│ │ cursor: not-allowed      │ │
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

---

### Alertas y Notificaciones

```
┌─────────────────────────────────────────────┐
│ ✓ ÉXITO (SUCCESS)                           │
│ bg: verde-suave, border: verde-hoja/30      │
│ ┌──────────────────────────────────────┐   │
│ │ [✓ verde-hoja] Operación exitosa   │   │
│ │ Los datos han sido guardados ok    │   │
│ └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ ⚠ ADVERTENCIA (WARNING)                     │
│ bg: #FBA500/10, border: #FBA500/30          │
│ ┌──────────────────────────────────────┐   │
│ │ [⚠ #FBA500] Ten cuidado             │   │
│ │ Esta acción no se puede deshacer    │   │
│ └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ ✕ ERROR                                     │
│ bg: #DC2626/10, border: #DC2626/30          │
│ ┌──────────────────────────────────────┐   │
│ │ [✕ #DC2626] Algo salió mal         │   │
│ │ Por favor, intenta nuevamente       │   │
│ └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ ℹ INFORMACIÓN (INFO)                        │
│ bg: #0284C7/10, border: #0284C7/30          │
│ ┌──────────────────────────────────────┐   │
│ │ [ℹ #0284C7] Información             │   │
│ │ Este campo es obligatorio            │   │
│ └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 🎭 Ejemplos de Layouts

### Formulario Limpio (Minimalista)

```
═══════════════════════════════════════════════
              PerFinanzas
  Accede a tu cuenta de forma segura
═══════════════════════════════════════════════

Identificación
┌─────────────────────────────────┐
│ [Input con border-gray-300]      │
└─────────────────────────────────┘

Contraseña
┌─────────────────────────────────┐
│ [Input con toggle - verde-hoja]  │
└─────────────────────────────────┘

[Enlace "¿Olvidaste?"  - verde-bosque]

┌──────────────────────────────────┐
│  INICIAR SESIÓN → (gradient-eco) │
└──────────────────────────────────┘

¿No tienes cuenta? [Regístrate] (verde-bosque)

───────────────────────────────────────────
  © 2026 PerFinanzas - Privacidad
═══════════════════════════════════════════════
```

---

## 🎨 Proporciones de Color en Diferentes Secciones

### Sección Hero / Header
```
70% Blanco/transparente
20% Verde (logo, títulos)
10% Grises (subtítulos)
```

### Formularios
```
75% Blanco (fondos, inputs)
15% Verde (labels focus, bordes)
10% Grises (placeholders, helpers)
```

### Llamadas a la Acción
```
Botón Primario: Verde-Hoja (100% del botón)
Botón Secundario: Verde-Bosque (100% del botón)
Estados Hover: Transición a verde-bosque
```

### Tarjetas de Contenido
```
80% Blanco (fondo)
10% Verde (bordes, acentos)
10% Grises (líneas divisoras)
```

---

## ✨ Efectos Visuales

### Transiciones
```
Duración estándar: 200ms (cubic-bezier)
Color hover: verde-hoja → verde-bosque
Escala hover: 1.0 → 1.02 (sutil)
Sombra hover: shadow-eco-md → shadow-eco-lg
```

### Focus States
```
Ring color: verde-hoja
Ring width: 2px
Ring offset: 2px
Duración: 200ms
```

### Hover States
```
Enlaces: green-bosque → green-hoja
Botones: color más oscuro + shadow aumento
Cards: border gris → verde-hoja
Inputs: border gris → verde-hoja (sin blur)
```

---

## 📐 Espaciado Recomendado

```
Padding componentes:
- Botones:   px-4 py-2.5 (md)
- Inputs:    px-4 py-2.5
- Cards:     p-8
- Sections:  space-y-6 (móvil) / space-y-8 (desktop)

Gap entre elementos:
- Dentro de grupos: gap-2
- Entre secciones: gap-4
- Entre bloques: gap-6 / gap-8
```

---

## 🎯 Checklist de Diseño

Antes de crear nuevos componentes:

- [ ] ¿Usa solo colores de la paleta (verde-* y grises)?
- [ ] ¿El contraste es WCAG AA (4.5:1)?
- [ ] ¿Las transiciones son smooth (200ms)?
- [ ] ¿El focus state es visible (ring verde-hoja)?
- [ ] ¿La proporción 70-20-10 es respetada?
- [ ] ¿Los espacios siguen la escala definida?
- [ ] ¿No hay negros puros (#000)?
- [ ] ¿Los iconos son coherentes con la marca?

---

**Última actualización**: Enero 2026
**Versión**: 1.0
**Status**: Implementado ✅

