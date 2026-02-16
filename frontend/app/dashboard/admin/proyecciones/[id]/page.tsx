'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

import { apiClient } from '@/lib/api-client';
import type { UserProfile } from '@/types/api';
import { AnalysisProjectionDetail } from '@/components/dashboard/admin/AnalysisProjectionDetail';

export default function AdminProjectionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const analysisId = params.id as string;
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isRoleLoading, setIsRoleLoading] = useState(true);

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

  return <AnalysisProjectionDetail analysisId={analysisId} />;
}
