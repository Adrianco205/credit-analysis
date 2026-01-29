'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { LogIn, CreditCard, Lock, AlertCircle } from 'lucide-react';

import { AuthLayout } from '@/components/auth-layout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
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
      const response = await apiClient.login(data);
      
      toast.success('¡Bienvenido!', {
        description: 'Has iniciado sesión correctamente',
        duration: 2000,
      });

      // Redirigir al dashboard después de un breve delay
      setTimeout(() => {
        router.push('/dashboard');
      }, 1000);
      
    } catch (error) {
      const apiError = error as ApiError;
      
      if (apiError.status_code === 401) {
        toast.error('Credenciales incorrectas', {
          description: 'Verifica tu cédula y contraseña',
        });
      } else if (apiError.status_code === 403) {
        toast.error('Cuenta no activada', {
          description: apiError.message || 'Por favor verifica tu correo electrónico',
        });
      } else {
        toast.error('Error al iniciar sesión', {
          description: apiError.message || 'Intenta nuevamente',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle>Iniciar Sesión</CardTitle>
          <CardDescription>
            Ingresa con tu número de cédula y contraseña
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Identificación */}
            <Input
              label="Número de Cédula"
              type="text"
              placeholder="Ej: 1234567890"
              leftIcon={<CreditCard size={18} />}
              error={errors.identificacion?.message}
              {...register('identificacion')}
              disabled={isLoading}
              autoComplete="username"
            />

            {/* Password */}
            <Input
              label="Contraseña"
              type="password"
              placeholder="Ingresa tu contraseña"
              leftIcon={<Lock size={18} />}
              error={errors.password?.message}
              {...register('password')}
              disabled={isLoading}
              autoComplete="current-password"
            />

            {/* Forgot password link */}
            <div className="flex justify-end">
              <Link
                href="/auth/forgot-password"
                className="text-sm text-verde-bosque hover:text-verde-hoja font-medium transition-colors"
              >
                ¿Olvidaste tu contraseña?
              </Link>
            </div>

            {/* Submit button */}
            <Button
              type="submit"
              className="w-full"
              size="lg"
              isLoading={isLoading}
              leftIcon={<LogIn size={20} />}
            >
              Ingresar
            </Button>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">
                  ¿No tienes cuenta?
                </span>
              </div>
            </div>

            {/* Register link */}
            <Link href="/auth/register">
              <Button
                type="button"
                variant="outline"
                className="w-full"
                size="lg"
              >
                Crear cuenta nueva
              </Button>
            </Link>
          </form>
        </CardContent>
      </Card>

      {/* Info box */}
      <div className="mt-6 p-4 bg-verde-suave/50 border border-verde-hoja/20 rounded-lg">
        <div className="flex gap-3">
          <AlertCircle className="w-5 h-5 text-verde-bosque flex-shrink-0 mt-0.5" />
          <div className="text-sm text-gray-700">
            <p className="font-medium text-verde-bosque mb-1">Primera vez aquí?</p>
            <p className="text-gray-600">
              Crea tu cuenta y comienza a analizar tus créditos hipotecarios de forma inteligente.
            </p>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}
