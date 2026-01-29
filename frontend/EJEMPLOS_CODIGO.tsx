// 🌿 EJEMPLOS DE CÓDIGO - Sistema de Diseño EcoFinanzas
// Copypaste ready components y patterns

import React from 'react';

// ============================================================================
// 1. INPUTS CON VALIDACIÓN
// ============================================================================

import { Input } from '@/components/ui/input';
import { Mail, Lock } from 'lucide-react';

export function FormFieldExample() {
  return (
    <form className="space-y-4">
      {/* Input básico */}
      <Input
        label="Nombre Completo"
        placeholder="Ej: Juan García"
        helperText="Debe contener al menos 3 caracteres"
      />

      {/* Input con icono izquierdo */}
      <Input
        label="Correo Electrónico"
        type="email"
        placeholder="tu@correo.com"
        leftIcon={<Mail className="w-5 h-5" />}
      />

      {/* Input con contraseña toggle */}
      <Input
        label="Contraseña"
        type="password"
        placeholder="Mínimo 8 caracteres"
        showPasswordToggle={true}
        helperText="Debe contener mayúsculas y números"
        leftIcon={<Lock className="w-5 h-5" />}
      />

      {/* Input con error */}
      <Input
        label="Teléfono"
        placeholder="3001234567"
        error="El teléfono debe tener 10 dígitos"
      />

      {/* Input deshabilitado */}
      <Input
        label="Referencia"
        placeholder="Auto generado"
        disabled={true}
        value="REF-2026-001"
      />
    </form>
  );
}

// ============================================================================
// 2. BOTONES CON VARIANTES
// ============================================================================

import { Button } from '@/components/ui/button';
import { ArrowRight, Trash2, Plus } from 'lucide-react';

export function ButtonVariantsExample() {
  const [isLoading, setIsLoading] = React.useState(false);

  return (
    <div className="space-y-4">
      {/* Botón primario */}
      <Button variant="primary" size="md">
        Acción Primaria
        <ArrowRight size={18} />
      </Button>

      {/* Botón secundario */}
      <Button variant="secondary">
        Acción Secundaria
      </Button>

      {/* Botón outline */}
      <Button variant="outline">
        <Plus size={18} />
        Agregar Nuevo
      </Button>

      {/* Botón ghost */}
      <Button variant="ghost">
        <Trash2 size={18} />
        Eliminar
      </Button>

      {/* Botón con carga */}
      <Button
        isLoading={isLoading}
        onClick={async () => {
          setIsLoading(true);
          await new Promise(r => setTimeout(r, 2000));
          setIsLoading(false);
        }}
      >
        {isLoading ? 'Procesando...' : 'Procesar'}
      </Button>

      {/* Botón deshabilitado */}
      <Button disabled>
        No disponible
      </Button>

      {/* Botón full width */}
      <Button className="w-full">
        Aceptar Términos y Condiciones
      </Button>

      {/* Botón pequeño */}
      <Button size="sm">Guardar</Button>

      {/* Botón grande */}
      <Button size="lg">Comenzar Ahora</Button>
    </div>
  );
}

// ============================================================================
// 3. TARJETAS (CARDS)
// ============================================================================

import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { CheckCircle, TrendingUp } from 'lucide-react';

export function CardVariantsExample() {
  return (
    <div className="space-y-4">
      {/* Card default */}
      <Card variant="default">
        <div className="text-center">
          <h3 className="text-lg font-bold text-gray-900">Tarjeta Simple</h3>
          <p className="text-sm text-gray-600 mt-2">
            Fondo blanco limpio ideal para contenido neutral
          </p>
        </div>
      </Card>

      {/* Card con borde */}
      <Card variant="bordered">
        <CardHeader>
          <CardTitle className="text-verde-bosque">Con Borde</CardTitle>
          <CardDescription>
            Borde gris que se vuelve verde al hover
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Card elevada */}
      <Card variant="elevated">
        <div className="flex items-start gap-4">
          <TrendingUp className="w-6 h-6 text-verde-hoja mt-1 flex-shrink-0" />
          <div>
            <h3 className="font-bold text-verde-bosque">Card Elevada</h3>
            <p className="text-sm text-gray-600">
              Con sombra eco (no gris puro)
            </p>
          </div>
        </div>
      </Card>

      {/* Card soft (nueva) */}
      <Card variant="soft">
        <div className="flex items-start gap-3">
          <CheckCircle className="w-5 h-5 text-verde-hoja flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-verde-bosque">
              Éxito
            </h4>
            <p className="text-sm text-gray-700">
              Tu solicitud ha sido registrada correctamente
            </p>
          </div>
        </div>
      </Card>

      {/* Card con contenido completo */}
      <Card variant="bordered">
        <CardHeader>
          <CardTitle>Análisis de Crédito</CardTitle>
        </CardHeader>
        <div className="px-8 pb-8">
          <div className="space-y-2">
            <p className="text-sm">
              <span className="text-gray-600">Monto solicitado:</span>
              <span className="text-verde-bosque font-bold ml-2">$250,000</span>
            </p>
            <p className="text-sm">
              <span className="text-gray-600">Plazo:</span>
              <span className="text-verde-bosque font-bold ml-2">15 años</span>
            </p>
            <p className="text-sm">
              <span className="text-gray-600">Tasa estimada:</span>
              <span className="text-verde-bosque font-bold ml-2">4.5% anual</span>
            </p>
          </div>
          <div className="mt-6 pt-6 border-t border-gray-200">
            <Button className="w-full">Solicitar Ahora</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

// ============================================================================
// 4. SECCIONES CON ICONOS
// ============================================================================

import { Users, Shield, Zap, Leaf } from 'lucide-react';

export function SectionWithIconsExample() {
  const features = [
    {
      icon: Leaf,
      title: 'Sostenible',
      description: 'Análisis ambiental integrado',
    },
    {
      icon: Shield,
      title: 'Seguro',
      description: 'Tus datos están protegidos',
    },
    {
      icon: Zap,
      title: 'Rápido',
      description: 'Resultados en minutos',
    },
    {
      icon: Users,
      title: 'Fácil',
      description: 'Interfaz intuitiva',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {features.map((feature) => {
        const Icon = feature.icon;
        return (
          <Card key={feature.title} variant="soft">
            <div className="flex gap-4">
              <div className="w-12 h-12 rounded-lg bg-verde-hoja/10 flex items-center justify-center flex-shrink-0">
                <Icon className="w-6 h-6 text-verde-bosque" />
              </div>
              <div>
                <h3 className="font-bold text-verde-bosque">
                  {feature.title}
                </h3>
                <p className="text-sm text-gray-600">
                  {feature.description}
                </p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

// ============================================================================
// 5. ALERTAS SEMÁNTICAS
// ============================================================================

import { AlertCircle, Info, AlertTriangle } from 'lucide-react';

export function AlertsExample() {
  return (
    <div className="space-y-3">
      {/* Success Alert */}
      <div className="p-4 bg-verde-suave border border-verde-hoja/30 rounded-lg flex gap-3">
        <CheckCircle className="w-5 h-5 text-verde-hoja flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-verde-bosque">Éxito</h4>
          <p className="text-sm text-gray-700">
            Tu registro ha sido completado correctamente
          </p>
        </div>
      </div>

      {/* Warning Alert */}
      <div className="p-4 bg-[#FBA500]/10 border border-[#FBA500]/30 rounded-lg flex gap-3">
        <AlertTriangle className="w-5 h-5 text-[#FBA500] flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-[#FBA500]">Advertencia</h4>
          <p className="text-sm text-gray-700">
            Esta acción no se puede deshacer. Procede con cuidado.
          </p>
        </div>
      </div>

      {/* Error Alert */}
      <div className="p-4 bg-[#DC2626]/10 border border-[#DC2626]/30 rounded-lg flex gap-3">
        <AlertCircle className="w-5 h-5 text-[#DC2626] flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-[#DC2626]">Error</h4>
          <p className="text-sm text-gray-700">
            Ha ocurrido un error. Por favor intenta nuevamente.
          </p>
        </div>
      </div>

      {/* Info Alert */}
      <div className="p-4 bg-[#0284C7]/10 border border-[#0284C7]/30 rounded-lg flex gap-3">
        <Info className="w-5 h-5 text-[#0284C7] flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-[#0284C7]">Información</h4>
          <p className="text-sm text-gray-700">
            Este proceso puede tomar hasta 24 horas.
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 6. FORMULARIO COMPLETO
// ============================================================================

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const formSchema = z.object({
  nombres: z.string().min(3, 'Mínimo 3 caracteres'),
  email: z.string().email('Email inválido'),
  telefono: z.string().regex(/^\d{10}$/, 'Debe tener 10 dígitos'),
  mensaje: z.string().min(10, 'Mínimo 10 caracteres'),
  terminos: z.boolean().refine(val => val === true, {
    message: 'Debes aceptar los términos',
  }),
});

type FormData = z.infer<typeof formSchema>;

export function CompleteFormExample() {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  });

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    await new Promise(r => setTimeout(r, 2000));
    console.log(data);
    setIsSubmitting(false);
  };

  return (
    <Card variant="soft">
      <h2 className="text-2xl font-bold text-verde-bosque mb-6">
        Formulario de Contacto
      </h2>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Nombres"
          placeholder="Tu nombre completo"
          error={errors.nombres?.message}
          {...register('nombres')}
        />

        <Input
          label="Correo Electrónico"
          type="email"
          placeholder="tu@correo.com"
          error={errors.email?.message}
          {...register('email')}
        />

        <Input
          label="Teléfono"
          placeholder="3001234567"
          error={errors.telefono?.message}
          {...register('telefono')}
        />

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2 ml-1">
            Mensaje
          </label>
          <textarea
            className="w-full px-4 py-3 border border-gray-300 rounded-xl 
                       focus:border-verde-hoja focus:ring-4 focus:ring-verde-hoja/15
                       placeholder:text-gray-400 transition-all"
            placeholder="Tu mensaje aquí..."
            rows={4}
            {...register('mensaje')}
          />
          {errors.mensaje && (
            <p className="text-red-600 text-xs mt-1">{errors.mensaje.message}</p>
          )}
        </div>

        <div className="flex items-start gap-2">
          <input
            type="checkbox"
            id="terminos"
            className="mt-1 w-4 h-4 text-verde-hoja border-gray-300 rounded"
            {...register('terminos')}
          />
          <label htmlFor="terminos" className="text-sm text-gray-600">
            Acepto los términos y condiciones
          </label>
        </div>
        {errors.terminos && (
          <p className="text-red-600 text-xs">{errors.terminos.message}</p>
        )}

        <Button
          type="submit"
          className="w-full"
          isLoading={isSubmitting}
          size="lg"
        >
          Enviar Mensaje
          <ArrowRight size={18} />
        </Button>
      </form>
    </Card>
  );
}

// ============================================================================
// 7. GRADIENTES PERSONALIZADOS
// ============================================================================

export function GradientExamples() {
  return (
    <div className="space-y-4">
      {/* Gradiente suave */}
      <div className="gradient-eco-subtle h-32 rounded-lg flex items-center justify-center">
        <p className="text-verde-bosque font-bold">
          Gradiente Sutil (Fondos)
        </p>
      </div>

      {/* Gradiente primario */}
      <div className="gradient-eco-primary h-32 rounded-lg flex items-center justify-center">
        <p className="text-white font-bold">
          Gradiente Primario (Headers)
        </p>
      </div>

      {/* Gradiente acento */}
      <div className="gradient-eco-accent h-32 rounded-lg flex items-center justify-center">
        <p className="text-white font-bold">
          Gradiente Acento (Énfasis)
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// 8. SELECTORES Y DROPDOWNS ESTILIZADOS
// ============================================================================

export function SelectorsExample() {
  return (
    <div className="space-y-4">
      {/* Select básico */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2 ml-1">
          Tipo de Identificación
        </label>
        <select
          className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl
                     focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja
                     outline-none transition-all hover:border-gray-300"
        >
          <option value="CC">Cédula (CC)</option>
          <option value="CE">Cédula Extranjería (CE)</option>
          <option value="TI">Tarjeta de Identidad (TI)</option>
          <option value="PAS">Pasaporte (PAS)</option>
        </select>
      </div>

      {/* Select con estado enfocado */}
      <div>
        <label className="block text-sm font-semibold text-verde-hoja mb-2 ml-1">
          Ciudad (Enfocado)
        </label>
        <select
          className="w-full px-4 py-3 bg-white border-verde-hoja border-2 rounded-xl
                     ring-4 ring-verde-hoja/15
                     outline-none"
        >
          <option value="">Selecciona una ciudad</option>
          <option value="BOG">Bogotá</option>
          <option value="MED">Medellín</option>
          <option value="CAL">Cali</option>
        </select>
      </div>

      {/* Select deshabilitado */}
      <div>
        <label className="block text-sm font-semibold text-gray-400 mb-2 ml-1">
          País (Deshabilitado)
        </label>
        <select
          disabled
          className="w-full px-4 py-3 bg-gray-100 border border-gray-200 rounded-xl
                     text-gray-500 cursor-not-allowed"
        >
          <option>Colombia</option>
        </select>
      </div>
    </div>
  );
}

// ============================================================================
// 9. SOMBRAS PERSONALIZADAS
// ============================================================================

export function ShadowsExample() {
  return (
    <div className="space-y-4">
      <div className="shadow-eco-sm p-4 bg-white rounded-lg">
        <p>Sombra Eco Pequeña</p>
      </div>

      <div className="shadow-eco-md p-4 bg-white rounded-lg">
        <p>Sombra Eco Media</p>
      </div>

      <div className="shadow-eco-lg p-4 bg-white rounded-lg">
        <p>Sombra Eco Grande</p>
      </div>
    </div>
  );
}

// ============================================================================
// 10. TOKENS CSS (VARIABLES DISPONIBLES)
// ============================================================================

/*
COLORES PRINCIPALES:
  --verde-bosque: #1B5E20     (Primario oscuro, títulos)
  --verde-hoja: #4CAF50        (Color marca, focus)
  --verde-claro: #66BB6A       (Hover, énfasis)
  --verde-suave: #E8F5E9       (Fondos suaves)

SEMÁNTICOS:
  --success: #4CAF50            (Éxito)
  --warning: #FBA500            (Advertencia)
  --error: #DC2626              (Error)
  --info: #0284C7               (Información)

ESCALA DE GRISES:
  --gray-50 a --gray-900        (9 tonalidades)

USO EN CSS:
  color: var(--verde-bosque);
  background-color: var(--verde-suave);
  border-color: var(--verde-hoja);

USO EN TAILWIND:
  text-verde-bosque
  bg-verde-suave
  border-verde-hoja
  ring-verde-hoja
*/

export { Button, Input, Card, CardHeader, CardTitle, CardDescription };
