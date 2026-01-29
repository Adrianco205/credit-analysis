'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, User, LogOut, FileText, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';
import type { UserProfile } from '@/types/api';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          router.push('/auth/login');
          return;
        }

        const profile = await apiClient.getProfile();
        setUser(profile);
      } catch (error: any) {
        console.error('Error loading profile:', error);
        toast.error('Sesión expirada. Por favor, inicia sesión nuevamente.');
        localStorage.removeItem('access_token');
        router.push('/auth/login');
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [router]);

  const handleLogout = async () => {
    try {
      await apiClient.logout();
      toast.success('Sesión cerrada correctamente');
      router.push('/auth/login');
    } catch (error) {
      console.error('Error during logout:', error);
      localStorage.removeItem('access_token');
      router.push('/auth/login');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-verde-suave to-white flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-verde-hoja animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Cargando tu perfil...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-verde-suave to-white">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-verde-bosque">EcoFinanzas</h1>
              <p className="text-sm text-gray-600">Panel de Control</p>
            </div>
            <Button
              onClick={handleLogout}
              variant="outline"
              leftIcon={<LogOut className="w-4 h-4" />}
            >
              Cerrar Sesión
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Bienvenido, {user.nombres} {user.apellidos}
          </h2>
          <p className="text-gray-600">
            Aquí podrás gestionar tus análisis de crédito hipotecario
          </p>
        </div>

        {/* Profile Card */}
        <Card className="mb-8">
          <div className="flex items-start space-x-4">
            <div className="bg-verde-hoja/10 p-3 rounded-lg">
              <User className="w-8 h-8 text-verde-hoja" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Información de Perfil
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Identificación</p>
                  <p className="text-gray-900 font-medium">{user.identificacion}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Email</p>
                  <p className="text-gray-900 font-medium">{user.email}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Teléfono</p>
                  <p className="text-gray-900 font-medium">{user.telefono}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Género</p>
                  <p className="text-gray-900 font-medium">
                    {user.genero === 'M' ? 'Masculino' : user.genero === 'F' ? 'Femenino' : 'Otro'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <div className="flex items-start space-x-4">
              <div className="bg-blue-100 p-3 rounded-lg">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  Subir Documento
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  Carga tu extracto bancario para análisis
                </p>
                <p className="text-xs text-gray-500 italic">
                  Próximamente disponible
                </p>
              </div>
            </div>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <div className="flex items-start space-x-4">
              <div className="bg-green-100 p-3 rounded-lg">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  Mis Análisis
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  Revisa tus análisis de crédito
                </p>
                <p className="text-xs text-gray-500 italic">
                  Próximamente disponible
                </p>
              </div>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
