'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import {
  ArrowRight,
  CreditCard,
  Lock,
  Mail,
  MapPin,
  User,
} from 'lucide-react';

import { AuthLayout } from '@/components/auth-layout-glass';
import { Button } from '@/components/ui/button';
import { CitySearch } from '@/components/city-search';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';
import { registerSchema, type RegisterFormData } from '@/lib/validations';
import type { ApiError } from '@/types/api';

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      tipo_identificacion: 'CC',
      genero: 'M',
      ciudad_id: 0,
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
        telefono: data.telefono,
        genero: data.genero || undefined,
        password: data.password,
        ciudad_id: data.ciudad_id,
      };

      const response = await apiClient.register(requestData);

      toast.success('¡Cuenta creada!', {
        description: 'Revisa tu correo para el código de verificación.',
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
      <div className="space-y-6 sm:space-y-8">
        {/* Título */}
        <div className="text-center space-y-1 sm:space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold text-verde-bosque">Crear Cuenta</h2>
          <p className="text-gray-700 text-xs sm:text-sm">
            Únete a EcoFinanzas y transforma tu relación con el dinero
          </p>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 sm:space-y-8">
            {/* SECCIÓN 1: IDENTIDAD PERSONAL */}
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center gap-2">
                <User size={16} className="sm:w-[18px] sm:h-[18px] text-verde-bosque font-bold" />
                <h3 className="text-xs sm:text-xs font-bold text-verde-bosque uppercase tracking-wider">
                  Identidad Personal
                </h3>
              </div>

              <div className="space-y-3 sm:space-y-4">
                <Input
                  label="Nombre/s"
                  placeholder="Ej: Juan Carlos"
                  error={errors.nombres?.message}
                  {...register('nombres')}
                  disabled={isLoading}
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <Input
                    label="Primer Apellido"
                    placeholder="García"
                    error={errors.primer_apellido?.message}
                    {...register('primer_apellido')}
                    disabled={isLoading}
                  />
                  <Input
                    label="Segundo Apellido"
                    placeholder="Martínez"
                    error={errors.segundo_apellido?.message}
                    {...register('segundo_apellido')}
                    disabled={isLoading}
                  />
                </div>
              </div>
            </div>

            {/* SECCIÓN 2: DOCUMENTO */}
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center gap-2">
                <CreditCard size={16} className="sm:w-[18px] sm:h-[18px] text-verde-bosque font-bold" />
                <h3 className="text-xs sm:text-xs font-bold text-verde-bosque uppercase tracking-wider">
                  Documento de Identidad
                </h3>
              </div>

              <div className="space-y-3 sm:space-y-4">
                <div className="flex gap-3">
                  <div className="w-2/5">
                    <label className="block text-sm font-semibold text-verde-bosque mb-2 ml-1">
                      Tipo
                    </label>
                    <select
                      className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja outline-none transition-all text-sm md:text-base hover:border-gray-300 text-gray-900 font-medium"
                      {...register('tipo_identificacion')}
                      disabled={isLoading}
                    >
                      <option value="">Selecciona...</option>
                      <option value="CC">Cédula (CC)</option>
                      <option value="CE">Cédula Extranjería (CE)</option>
                      <option value="TI">Tarjeta Identidad (TI)</option>
                      <option value="PAS">Pasaporte (PAS)</option>
                    </select>
                  </div>
                  <div className="w-3/5">
                    <Input
                      label="Número"
                      placeholder="1234567890"
                      error={errors.identificacion?.message}
                      {...register('identificacion')}
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <Input
                  label="Confirmar Número de Identificación"
                  placeholder="Vuelve a escribir tu número"
                  error={errors.identificacion_confirm?.message}
                  {...register('identificacion_confirm')}
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* SECCIÓN 3: CONTACTO */}
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center gap-2">
                <Mail size={16} className="sm:w-[18px] sm:h-[18px] text-verde-bosque font-bold" />
                <h3 className="text-xs sm:text-xs font-bold text-verde-bosque uppercase tracking-wider">
                  Información de Contacto
                </h3>
              </div>

              <div className="space-y-3 sm:space-y-4">
                <Input
                  label="Correo Electrónico"
                  type="email"
                  placeholder="tu@correo.com"
                  error={errors.email?.message}
                  {...register('email')}
                  disabled={isLoading}
                />

                <Input
                  label="Confirmar Correo Electrónico"
                  type="email"
                  placeholder="Vuelve a escribir tu correo"
                  error={errors.email_confirm?.message}
                  {...register('email_confirm')}
                  disabled={isLoading}
                />

                <Input
                  label="Teléfono Celular"
                  placeholder="3001234567"
                  error={errors.telefono?.message}
                  helperText="10 dígitos comenzando con 3"
                  {...register('telefono')}
                  disabled={isLoading}
                />

                <Input
                  label="Confirmar Teléfono"
                  placeholder="Vuelve a escribir tu teléfono"
                  error={errors.telefono_confirm?.message}
                  {...register('telefono_confirm')}
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* SECCIÓN 4: UBICACIÓN */}
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center gap-2">
                <MapPin size={16} className="sm:w-[18px] sm:h-[18px] text-verde-bosque font-bold" />
                <h3 className="text-xs sm:text-xs font-bold text-verde-bosque uppercase tracking-wider">
                  Ubicación
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                <Controller
                  name="ciudad_id"
                  control={control}
                  render={({ field }) => (
                    <CitySearch
                      value={field.value}
                      onChange={(id, nombre) => {
                        setValue('ciudad_id', id);
                        setValue('ciudad_nombre', nombre);
                      }}
                      error={errors.ciudad_id?.message}
                      disabled={isLoading}
                    />
                  )}
                />

                <div>
                  <label className="block text-sm font-semibold text-verde-bosque mb-2 ml-1">
                    Género
                  </label>
                  <select
                    className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja outline-none transition-all text-sm md:text-base hover:border-gray-300 text-gray-900 font-medium"
                    {...register('genero')}
                    disabled={isLoading}
                  >
                    <option value="">Selecciona...</option>
                    <option value="M">Masculino</option>
                    <option value="F">Femenino</option>
                    <option value="O">Otro / Prefiero no decir</option>
                  </select>
                </div>
              </div>
            </div>

            {/* SECCIÓN 5: SEGURIDAD */}
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center gap-2">
                <Lock size={16} className="sm:w-[18px] sm:h-[18px] text-verde-bosque font-bold" />
                <h3 className="text-xs sm:text-xs font-bold text-verde-bosque uppercase tracking-wider">
                  Contraseña
                </h3>
              </div>

              <div className="space-y-3 sm:space-y-4">
                <Input
                  label="Contraseña"
                  type="password"
                  placeholder="Mínimo 8 caracteres"
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
                  error={errors.confirm_password?.message}
                  showPasswordToggle={true}
                  {...register('confirm_password')}
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Términos y Condiciones */}
            <div className="space-y-4 sm:space-y-5 pt-3 sm:pt-4 border-t border-gray-200">
              <div className="flex items-start gap-2 sm:gap-3">
                <input
                  type="checkbox"
                  id="terms"
                  required
                  className="mt-0.5 sm:mt-1 w-4 h-4 text-verde-hoja border-gray-300 rounded focus:ring-verde-hoja cursor-pointer flex-shrink-0"
                />
                <label htmlFor="terms" className="text-xs sm:text-sm text-gray-700 leading-relaxed cursor-pointer">
                  Acepto los{' '}
                  <Link
                    href="/terminos"
                    className="text-verde-bosque hover:text-verde-hoja font-medium underline"
                  >
                    términos y condiciones
                  </Link>{' '}
                  y la{' '}
                  <Link
                    href="/politica"
                    className="text-verde-bosque hover:text-verde-hoja font-medium underline"
                  >
                    política de privacidad
                  </Link>
                </label>
              </div>

              {/* Botón Submit */}
              <Button
                type="submit"
                disabled={isLoading}
                size="lg"
                className="w-full bg-gradient-to-r from-verde-bosque to-verde-hoja text-white text-sm sm:text-base font-semibold hover:shadow-lg hover:shadow-verde-hoja/30 transition-all"
              >
                Crear Cuenta
                <ArrowRight size={16} className="sm:w-[18px] sm:h-[18px]" />
              </Button>

              {/* Link al Login */}
              <p className="text-center text-xs sm:text-sm text-gray-700">
                ¿Ya tienes cuenta?{' '}
                <Link
                  href="/auth/login"
                  className="text-verde-bosque hover:text-verde-hoja font-bold transition-colors"
                >
                  Inicia sesión
                </Link>
              </p>
            </div>
          </form>
      </div>
    </AuthLayout>
  );
}