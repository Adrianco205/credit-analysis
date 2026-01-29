'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { 
  UserPlus, 
  Mail, 
  Lock, 
  CreditCard, 
  User, 
  Phone, 
  ChevronRight,
  ShieldCheck 
} from 'lucide-react';

import { AuthLayout } from '@/components/auth-layout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { registerSchema, type RegisterFormData } from '@/lib/validations';
import { apiClient } from '@/lib/api-client';
import type { ApiError } from '@/types/api';

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      tipo_identificacion: 'CC',
      genero: 'O',
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);

    try {
      const requestData = {
        nombres: data.nombres,
        primer_apellido: data.primer_apellido,
        segundo_apellido: data.segundo_apellido || undefined,
        tipo_identificacion: data.tipo_identificacion,
        identificacion: data.identificacion,
        email: data.email,
        telefono: data.telefono || undefined,
        genero: data.genero || undefined,
        password: data.password,
        ciudad_id: data.ciudad_id,
      };

      const response = await apiClient.register(requestData);
      
      toast.success('¡Cuenta creada!', {
        description: 'Hemos enviado un código a tu correo.',
        duration: 5000,
      });

      setTimeout(() => {
        router.push(`/auth/verify-otp?user_id=${response.user_id}`);
      }, 1500);
      
    } catch (error) {
      const apiError = error as ApiError;
      toast.error('Error al registrarse', {
        description: apiError.message || 'Verifica los datos e intenta de nuevo',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Card className="border-none shadow-xl">
        <CardHeader className="space-y-1 pb-8">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 bg-verde-hoja/10 rounded-lg">
              <ShieldCheck className="w-6 h-6 text-verde-bosque" />
            </div>
            <span className="text-sm font-bold text-verde-bosque uppercase tracking-widest">Registro Seguro</span>
          </div>
          <CardTitle className="text-3xl font-bold">Crear Cuenta</CardTitle>
          <CardDescription>
            Únete a EcoFinanzas y transforma tu relación con el dinero.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            
            {/* SECCIÓN: IDENTIDAD PERSONAL */}
            <div className="space-y-4 p-5 bg-gray-50/50 rounded-2xl border border-gray-100">
              <h3 className="text-xs font-bold text-verde-bosque uppercase tracking-wider flex items-center gap-2">
                <User size={14} /> Identidad Personal
              </h3>
              
              <Input
                label="Nombres"
                placeholder="Ej: Juan Carlos"
                leftIcon={<User size={18} />}
                error={errors.nombres?.message}
                {...register('nombres')}
                disabled={isLoading}
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Primer Apellido"
                  placeholder="Pérez"
                  error={errors.primer_apellido?.message}
                  {...register('primer_apellido')}
                  disabled={isLoading}
                />
                <Input
                  label="Segundo Apellido"
                  placeholder="García"
                  error={errors.segundo_apellido?.message}
                  {...register('segundo_apellido')}
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* SECCIÓN: DOCUMENTO DE IDENTIDAD */}
            <div className="space-y-4 p-5 bg-gray-50/50 rounded-2xl border border-gray-100">
              <h3 className="text-xs font-bold text-verde-bosque uppercase tracking-wider flex items-center gap-2">
                <CreditCard size={14} /> Documento de Identidad
              </h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Tipo</label>
                  <select
                    className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-verde-hoja outline-none transition-all"
                    {...register('tipo_identificacion')}
                    disabled={isLoading}
                  >
                    <option value="CC">CC</option>
                    <option value="CE">CE</option>
                    <option value="TI">TI</option>
                    <option value="PAS">PAS</option>
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <Input
                    label="Número de Identificación"
                    placeholder="1234567890"
                    error={errors.identificacion?.message}
                    {...register('identificacion')}
                    disabled={isLoading}
                  />
                </div>
              </div>
            </div>

            {/* SECCIÓN: CONTACTO SEGURO */}
            <div className="space-y-4 p-5 bg-gray-50/50 rounded-2xl border border-gray-100">
              <h3 className="text-xs font-bold text-verde-bosque uppercase tracking-wider flex items-center gap-2">
                <Mail size={14} /> Contacto Seguro
              </h3>
              
              <Input
                label="Correo Electrónico"
                type="email"
                placeholder="tu@correo.com"
                leftIcon={<Mail size={18} />}
                error={errors.email?.message}
                {...register('email')}
                disabled={isLoading}
              />

              <Input
                label="Confirmar Correo Electrónico"
                type="email"
                placeholder="Vuelve a escribir tu correo"
                leftIcon={<Mail size={18} />}
                error={errors.email_confirm?.message}
                {...register('email_confirm')}
                disabled={isLoading}
              />

              <Input
                label="Teléfono Celular"
                placeholder="3001234567"
                leftIcon={<Phone size={18} />}
                error={errors.telefono?.message}
                helperText="Número de 10 dígitos comenzando con 3"
                {...register('telefono')}
                disabled={isLoading}
              />

              <Input
                label="Confirmar Teléfono Celular"
                placeholder="Vuelve a escribir tu teléfono"
                leftIcon={<Phone size={18} />}
                error={errors.telefono_confirm?.message}
                {...register('telefono_confirm')}
                disabled={isLoading}
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Género</label>
                <select
                  className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-verde-hoja outline-none"
                  {...register('genero')}
                  disabled={isLoading}
                >
                  <option value="O">Otro / Prefiero no decir</option>
                  <option value="M">Masculino</option>
                  <option value="F">Femenino</option>
                </select>
              </div>
            </div>

            {/* SECCIÓN: SEGURIDAD */}
            <div className="space-y-4 p-5 bg-verde-hoja/5 rounded-2xl border border-verde-hoja/10">
              <h3 className="text-xs font-bold text-verde-bosque uppercase tracking-wider flex items-center gap-2">
                <Lock size={14} /> Seguridad de la Cuenta
              </h3>
              
              <Input
                label="Contraseña"
                type="password"
                placeholder="Mínimo 8 caracteres"
                leftIcon={<Lock size={18} />}
                error={errors.password?.message}
                helperText="Debe contener mayúsculas, minúsculas y números"
                showPasswordToggle={true}
                {...register('password')}
                disabled={isLoading}
              />

              <Input
                label="Confirmar Contraseña"
                type="password"
                placeholder="Repite tu contraseña"
                leftIcon={<Lock size={18} />}
                error={errors.confirm_password?.message}
                showPasswordToggle={true}
                {...register('confirm_password')}
                disabled={isLoading}
              />
            </div>

            {/* TÉRMINOS Y ACCIÓN */}
            <div className="space-y-4 pt-2">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="terms"
                  required
                  className="mt-1 w-4 h-4 text-verde-hoja border-gray-300 rounded focus:ring-verde-hoja"
                />
                <label htmlFor="terms" className="text-sm text-gray-600 leading-snug">
                  Al registrarme, acepto los{' '}
                  <Link href="/terminos" className="text-verde-bosque font-semibold hover:underline">términos de servicio</Link>
                  {' '}y la{' '}
                  <Link href="/privacidad" className="text-verde-bosque font-semibold hover:underline">política de tratamiento de datos</Link>.
                </label>
              </div>

              <Button
                type="submit"
                className="w-full h-12 text-lg font-bold shadow-lg shadow-verde-hoja/20 hover:scale-[1.01] transition-transform"
                isLoading={isLoading}
                rightIcon={<ChevronRight size={20} />}
              >
                Crear mi cuenta
              </Button>

              <p className="text-center text-sm text-gray-500">
                ¿Ya tienes una cuenta?{' '}
                <Link href="/auth/login" className="text-verde-bosque font-bold hover:text-verde-hoja transition-colors">
                  Inicia Sesión aquí
                </Link>
              </p>
            </div>
          </form>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}