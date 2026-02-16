'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { ArrowLeft, Mail } from 'lucide-react';

import { AuthLayout } from '@/components/auth-layout-glass';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';
import { forgotPasswordSchema, type ForgotPasswordFormData } from '@/lib/validations';
import type { ApiError } from '@/types/api';

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setIsLoading(true);

    try {
      const response = await apiClient.forgotPassword({ email: data.email });
      toast.success('Solicitud enviada', {
        description: response.message,
      });
    } catch (error) {
      const apiError = error as ApiError;
      toast.error('No se pudo procesar la solicitud', {
        description: apiError.message || 'Inténtalo nuevamente en unos minutos.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-verde-bosque">Recuperar contraseña</h2>
          <p className="text-gray-700 text-sm">
            Ingresa tu correo y te enviaremos un enlace para crear una nueva contraseña.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <Input
            label="Correo electrónico"
            type="email"
            placeholder="tu@correo.com"
            error={errors.email?.message}
            leftIcon={<Mail size={18} />}
            {...register('email')}
            disabled={isLoading}
            autoComplete="email"
            autoFocus
          />

          <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
            Enviar enlace de recuperación
          </Button>
        </form>

        <Link href="/auth/login" className="block">
          <Button type="button" variant="ghost" className="w-full" leftIcon={<ArrowLeft size={18} />}>
            Volver a iniciar sesión
          </Button>
        </Link>
      </div>
    </AuthLayout>
  );
}
