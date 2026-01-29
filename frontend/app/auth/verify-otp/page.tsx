'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { ShieldCheck, Mail, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

import { AuthLayout } from '@/components/auth-layout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { otpSchema, type OtpFormData } from '@/lib/validations';
import { apiClient } from '@/lib/api-client';
import type { ApiError } from '@/types/api';

function VerifyOtpContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const userId = searchParams.get('user_id');

  const [isLoading, setIsLoading] = useState(false);
  const [timeLeft, setTimeLeft] = useState(600); // 10 minutos en segundos

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<OtpFormData>({
    resolver: zodResolver(otpSchema),
  });

  // Countdown timer
  useEffect(() => {
    if (timeLeft <= 0) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const onSubmit = async (data: OtpFormData) => {
    if (!userId) {
      toast.error('Error', {
        description: 'ID de usuario no encontrado',
      });
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.verifyOtp({
        user_id: userId,
        code: data.code,
      });

      toast.success('¡Cuenta activada!', {
        description: 'Tu cuenta ha sido verificada exitosamente',
        duration: 3000,
      });

      // Redirigir al login
      setTimeout(() => {
        router.push('/auth/login');
      }, 1500);
    } catch (error) {
      const apiError = error as ApiError;

      if (apiError.status_code === 400) {
        toast.error('Código inválido', {
          description: apiError.message || 'El código ingresado no es correcto o ha expirado',
        });
      } else {
        toast.error('Error al verificar', {
          description: apiError.message || 'Intenta nuevamente',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!userId) {
    return (
      <AuthLayout>
        <Card>
          <CardContent className="pt-8 text-center">
            <p className="text-gray-600 mb-4">
              No se encontró el ID de usuario. Por favor, regístrate nuevamente.
            </p>
            <Link href="/auth/register">
              <Button variant="primary">
                Ir a Registro
              </Button>
            </Link>
          </CardContent>
        </Card>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-verde-suave mb-4">
            <ShieldCheck className="w-6 h-6 text-verde-bosque" />
          </div>
          <CardTitle>Verifica tu Correo</CardTitle>
          <CardDescription>
            Hemos enviado un código de 6 dígitos a tu correo electrónico
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Info box */}
            <div className="p-4 bg-verde-suave/50 border border-verde-hoja/20 rounded-lg">
              <div className="flex gap-3">
                <Mail className="w-5 h-5 text-verde-bosque flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-verde-bosque mb-1">
                    Revisa tu bandeja de entrada
                  </p>
                  <p className="text-gray-700">
                    El código expira en{' '}
                    <span className="font-semibold text-verde-bosque">
                      {formatTime(timeLeft)}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            {/* OTP Input */}
            <Input
              label="Código de Verificación"
              type="text"
              placeholder="000000"
              maxLength={6}
              error={errors.code?.message}
              {...register('code')}
              disabled={isLoading}
              autoComplete="one-time-code"
              className="text-center text-2xl tracking-widest font-mono"
            />

            {/* Submit button */}
            <Button
              type="submit"
              className="w-full"
              size="lg"
              isLoading={isLoading}
              disabled={timeLeft <= 0}
            >
              {timeLeft <= 0 ? 'Código Expirado' : 'Verificar Cuenta'}
            </Button>

            {/* Resend button */}
            {timeLeft <= 0 && (
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => {
                  toast.info('Por favor, regístrate nuevamente para recibir un nuevo código');
                  router.push('/auth/register');
                }}
              >
                Solicitar Nuevo Código
              </Button>
            )}

            {/* Back to register */}
            <Link href="/auth/register" className="block">
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                leftIcon={<ArrowLeft size={18} />}
              >
                Volver al registro
              </Button>
            </Link>
          </form>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}

export default function VerifyOtpPage() {
  return (
    <Suspense fallback={
      <AuthLayout>
        <Card>
          <CardContent className="pt-8 text-center">
            <p className="text-gray-600">Cargando...</p>
          </CardContent>
        </Card>
      </AuthLayout>
    }>
      <VerifyOtpContent />
    </Suspense>
  );
}
