'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import type { UserProfile } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

export default function AdminProyeccionesPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isRoleLoading, setIsRoleLoading] = useState(true);
  const [analysisId, setAnalysisId] = useState('');

  useEffect(() => {
    const validateRole = async () => {
      try {
        const user = await apiClient.getProfile();
        setCurrentUser(user);
        if (user.rol !== 'ADMIN') {
          router.replace('/dashboard');
          return;
        }
      } catch {
        router.replace('/auth/login');
        return;
      } finally {
        setIsRoleLoading(false);
      }
    };

    validateRole();
  }, [router]);

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault();
    const value = analysisId.trim();
    if (!value) return;
    router.push(`/dashboard/admin/proyecciones/${value}`);
  };

  if (isRoleLoading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--verde-hoja)]" />
      </div>
    );
  }

  if (currentUser?.rol !== 'ADMIN') {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Generar proyecciones</h1>
        <p className="text-sm text-gray-600">Busca un crédito por ID de análisis para abrir el detalle y ejecutar el motor financiero.</p>
      </div>

      <Card variant="bordered" className="max-w-2xl">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-800">Buscar crédito</h2>
        </CardHeader>

        <form onSubmit={handleSearch} className="flex flex-col gap-4 md:flex-row md:items-end">
          <div className="flex-1">
            <Input
              label="ID del análisis"
              value={analysisId}
              onChange={(event) => setAnalysisId(event.target.value)}
              placeholder="Ej. 4c6df5a7-...."
            />
          </div>
          <Button type="submit" leftIcon={<Search size={16} />}>
            Abrir detalle
          </Button>
        </form>
      </Card>
    </div>
  );
}
