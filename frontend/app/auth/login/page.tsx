'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { ArrowRight } from 'lucide-react';

import { AuthLayout } from '@/components/auth-layout-glass';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { loginSchema, type LoginFormData } from '@/lib/validations';
import { apiClient } from '@/lib/api-client';
import type { ApiError } from '@/types/api';

export default function LoginPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);

    try {
      await apiClient.login(data);

      toast.success('¡Sesión iniciada!', {
        description: 'Bienvenido a EcoFinanzas',
        duration: 2000,
      });

      setTimeout(() => {
        router.push('/dashboard');
      }, 1000);
    } catch (error) {
      const apiError = error as ApiError;

      if (apiError.status_code === 401) {
        toast.error('Credenciales incorrectas');
      } else if (apiError.status_code === 403) {
        toast.error('Cuenta no activada', {
          description: 'Verifica tu correo electrónico',
        });
      } else {
        toast.error('Error al iniciar sesión');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-5 sm:space-y-6">
        {/* Título */}
        <div className="text-center space-y-1 sm:space-y-2">
          <h2 className="text-xl sm:text-2xl font-bold text-verde-bosque">Iniciar Sesión</h2>
          <p className="text-gray-700 text-xs sm:text-sm">Accede a tu cuenta</p>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 sm:space-y-5">
          {/* Identificación */}
          <Input
            label="Número de Identificación"
            placeholder="Ej: 1234567890"
            error={errors.identificacion?.message}
            {...register('identificacion')}
            disabled={isLoading}
            autoFocus
          />

          {/* Contraseña */}
          <div className="space-y-2">
            <Input
              label="Contraseña"
              type="password"
              placeholder="Tu contraseña"
              error={errors.password?.message}
              showPasswordToggle={true}
              {...register('password')}
              disabled={isLoading}
              autoComplete="current-password"
            />
            <Link
              href="/auth/forgot-password"
              className="inline-block text-xs sm:text-sm text-verde-bosque hover:text-verde-hoja font-medium transition-colors"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </div>

          {/* Botón Enviar */}
          <Button
            type="submit"
            disabled={isLoading}
            size="lg"
            className="w-full bg-gradient-to-r from-verde-bosque to-verde-hoja text-white text-sm sm:text-base font-semibold hover:shadow-lg hover:shadow-verde-hoja/30 transition-all"
          >
            Acceder
            <ArrowRight size={16} className="sm:w-[18px] sm:h-[18px]" />
          </Button>
        </form>

        {/* Divisor */}
        <div className="relative py-2">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center">
            <span className="px-2 sm:px-3 bg-white/85 text-gray-500 text-xs font-medium">
              O
            </span>
          </div>
        </div>

        {/* Registro Link */}
        <Link
          href="/auth/register"
          className="block w-full px-4 sm:px-6 py-2.5 sm:py-3 border-2 border-verde-bosque text-verde-bosque text-sm sm:text-base font-semibold rounded-xl sm:rounded-2xl hover:bg-verde-bosque/5 transition-all text-center flex items-center justify-center gap-2"
        >
          Crear una cuenta
          <ArrowRight size={16} className="sm:w-[18px] sm:h-[18px]" />
        </Link>
      </div>
    </AuthLayout>
  );
}
