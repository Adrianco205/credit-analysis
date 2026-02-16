'use client';

import React, { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { ArrowLeft, Lock } from 'lucide-react';

import { AuthLayout } from '@/components/auth-layout-glass';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';
import { resetPasswordSchema, type ResetPasswordFormData } from '@/lib/validations';
import type { ApiError } from '@/types/api';

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token) {
      toast.error('Enlace inválido', {
        description: 'El enlace de recuperación no contiene un token válido.',
      });
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.resetPassword({
        token,
        new_password: data.new_password,
        confirm_password: data.confirm_password,
      });

      toast.success('Contraseña actualizada', {
        description: 'Ya puedes iniciar sesión con tu nueva contraseña.',
      });

      setTimeout(() => {
        router.push('/auth/login');
      }, 1200);
    } catch (error) {
      const apiError = error as ApiError;
      toast.error('No se pudo restablecer la contraseña', {
        description: apiError.message || 'El enlace puede estar vencido o ser inválido.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-verde-bosque">Nueva contraseña</h2>
          <p className="text-gray-700 text-sm">
            Escribe y confirma tu nueva contraseña para completar la recuperación.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <Input
            label="Nueva contraseña"
            type="password"
            placeholder="Ingresa una contraseña segura"
            error={errors.new_password?.message}
            leftIcon={<Lock size={18} />}
            showPasswordToggle
            {...register('new_password')}
            disabled={isLoading}
            autoComplete="new-password"
            autoFocus
          />

          <Input
            label="Confirmar nueva contraseña"
            type="password"
            placeholder="Repite tu nueva contraseña"
            error={errors.confirm_password?.message}
            leftIcon={<Lock size={18} />}
            showPasswordToggle
            {...register('confirm_password')}
            disabled={isLoading}
            autoComplete="new-password"
          />

          <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
            Actualizar contraseña
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

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<AuthLayout><p className="text-center text-gray-600">Cargando...</p></AuthLayout>}>
      <ResetPasswordContent />
    </Suspense>
  );
}
