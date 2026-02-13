'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  AlertTriangle,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  Filter,
} from 'lucide-react';

import { apiClient } from '@/lib/api-client';
import { AdminAnalysisItem, AdminAnalysesParams, UserProfile } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { AnalysisActions } from '@/components/dashboard/analysis-actions';
import { useDebouncedValue } from '@/lib/use-debounced-value';

const PAGE_SIZES = [10, 25, 50];
const LIVE_SEARCH_ENABLED = false;

const STATUS_TEXT: Record<string, string> = {
  COMPLETED: 'Completado',
  PROCESSING: 'Procesando',
  PENDING: 'Pendiente',
  PENDING_MANUAL: 'Datos pendientes',
  EXTRACTED: 'Extraído',
  FAILED: 'Fallido',
  ERROR: 'Error',
  ID_MISMATCH: 'Cédula no coincide',
  NAME_MISMATCH: 'Nombre no coincide',
};

const STATUS_BADGE: Record<string, string> = {
  COMPLETED: 'bg-green-100 text-green-700',
  PROCESSING: 'bg-yellow-100 text-yellow-700',
  PENDING: 'bg-gray-100 text-gray-600',
  PENDING_MANUAL: 'bg-blue-100 text-blue-700',
  EXTRACTED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  ERROR: 'bg-red-100 text-red-700',
  ID_MISMATCH: 'bg-orange-100 text-orange-700',
  NAME_MISMATCH: 'bg-amber-100 text-amber-700',
};

export default function AdminAnalysesPage() {
  const router = useRouter();

  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isRoleLoading, setIsRoleLoading] = useState(true);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState<AdminAnalysisItem[]>([]);
  const [bankOptions, setBankOptions] = useState<Array<{ id: number; name: string }>>([]);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const [draftFilters, setDraftFilters] = useState<AdminAnalysesParams>({
    customer_id_number: '',
    customer_name: '',
    credit_number: '',
    bank_id: undefined,
    uploaded_from: '',
    uploaded_to: '',
    sort_by: 'uploaded_at',
    sort_dir: 'desc',
  });
  const [appliedFilters, setAppliedFilters] = useState<AdminAnalysesParams>({
    sort_by: 'uploaded_at',
    sort_dir: 'desc',
  });
  const debouncedDraftFilters = useDebouncedValue(draftFilters, 300);

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

  useEffect(() => {
    if (!isRoleLoading && currentUser?.rol === 'ADMIN') {
      loadAdminAnalyses();
    }
  }, [isRoleLoading, currentUser, page, pageSize, appliedFilters]);

  useEffect(() => {
    if (!LIVE_SEARCH_ENABLED) {
      return;
    }
    setPage(1);
    setAppliedFilters((prev) => ({
      ...prev,
      customer_id_number: debouncedDraftFilters.customer_id_number,
      customer_name: debouncedDraftFilters.customer_name,
      credit_number: debouncedDraftFilters.credit_number,
    }));
  }, [debouncedDraftFilters]);

  const loadAdminAnalyses = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.getAdminAnalyses({
        page,
        page_size: pageSize,
        customer_id_number: normalizeText(appliedFilters.customer_id_number),
        customer_name: normalizeText(appliedFilters.customer_name),
        credit_number: normalizeText(appliedFilters.credit_number),
        bank_id: appliedFilters.bank_id,
        uploaded_from: normalizeText(appliedFilters.uploaded_from),
        uploaded_to: normalizeText(appliedFilters.uploaded_to),
        sort_by: appliedFilters.sort_by || 'uploaded_at',
        sort_dir: appliedFilters.sort_dir || 'desc',
      });

      setItems(response.data);
      setTotal(response.pagination.total);
      setTotalPages(response.pagination.total_pages);
      setBankOptions(response.filters.bank_options || []);
    } catch (err: any) {
      setError(err?.message || 'No se pudo cargar el historial de análisis');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilters = () => {
    setPage(1);
    setAppliedFilters({ ...draftFilters });
  };

  const handleClearFilters = () => {
    const clean: AdminAnalysesParams = {
      customer_id_number: '',
      customer_name: '',
      credit_number: '',
      bank_id: undefined,
      uploaded_from: '',
      uploaded_to: '',
      sort_by: 'uploaded_at',
      sort_dir: 'desc',
    };
    setDraftFilters(clean);
    setPage(1);
    setAppliedFilters(clean);
  };

  const downloadDocument = async (documentId: string) => {
    try {
      const blob = await apiClient.downloadAdminDocument(documentId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'extracto.pdf';
      document.body.appendChild(anchor);
      anchor.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(anchor);
    } catch (err: any) {
      setError(err?.message || 'No se pudo descargar el documento');
    }
  };

  const totalLabel = useMemo(() => `${total} análisis`, [total]);

  if (isRoleLoading) {
    return <LoadingState />;
  }

  if (currentUser?.rol !== 'ADMIN') {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--verde-bosque)]">Ver historial de análisis</h1>
          <p className="text-sm text-gray-600">Consulta todos los análisis subidos por los clientes.</p>
        </div>
        <Button
          variant="outline"
          disabled
          title="Próximamente"
          leftIcon={<FileSearch size={16} />}
        >
          Generar nuevas oportunidades
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg border border-red-200 flex items-center gap-2">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={loadAdminAnalyses}>Reintentar</Button>
        </div>
      )}

      <Card variant="bordered">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Filter size={18} className="text-[var(--verde-hoja)]" />
            Filtros
          </h2>
        </CardHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <Input
            label="Cédula"
            value={draftFilters.customer_id_number || ''}
            onChange={(e) => setDraftFilters((prev) => ({ ...prev, customer_id_number: e.target.value }))}
            placeholder="Ej. 123456789"
          />

          <Input
            label="Nombre cliente"
            value={draftFilters.customer_name || ''}
            onChange={(e) => setDraftFilters((prev) => ({ ...prev, customer_name: e.target.value }))}
            placeholder="Nombre o apellidos"
          />

          <Input
            label="Número crédito"
            value={draftFilters.credit_number || ''}
            onChange={(e) => setDraftFilters((prev) => ({ ...prev, credit_number: e.target.value }))}
            placeholder="Ej. ABC123"
          />

          <div>
            <label className="block text-sm font-semibold text-verde-bosque mb-2 ml-1">Banco</label>
            <select
              className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja outline-none transition-all text-sm md:text-base hover:border-gray-300 text-gray-900 font-medium"
              value={draftFilters.bank_id ?? ''}
              onChange={(e) =>
                setDraftFilters((prev) => ({
                  ...prev,
                  bank_id: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            >
              <option value="">Todos</option>
              {bankOptions.map((bank) => (
                <option key={bank.id} value={bank.id}>
                  {bank.name}
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Fecha desde"
            type="date"
            value={draftFilters.uploaded_from || ''}
            onChange={(e) => setDraftFilters((prev) => ({ ...prev, uploaded_from: e.target.value }))}
          />

          <Input
            label="Fecha hasta"
            type="date"
            value={draftFilters.uploaded_to || ''}
            onChange={(e) => setDraftFilters((prev) => ({ ...prev, uploaded_to: e.target.value }))}
          />

          <div>
            <label className="block text-sm font-semibold text-verde-bosque mb-2 ml-1">Orden por fecha</label>
            <select
              className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-4 focus:ring-verde-hoja/15 focus:border-verde-hoja outline-none transition-all text-sm md:text-base hover:border-gray-300 text-gray-900 font-medium"
              value={draftFilters.sort_dir || 'desc'}
              onChange={(e) =>
                setDraftFilters((prev) => ({
                  ...prev,
                  sort_by: 'uploaded_at',
                  sort_dir: e.target.value as 'asc' | 'desc',
                }))
              }
            >
              <option value="desc">Más reciente primero</option>
              <option value="asc">Más antiguo primero</option>
            </select>
          </div>

          <div className="flex items-end gap-2">
            <Button variant="primary" onClick={handleApplyFilters}>Aplicar filtros</Button>
            <Button variant="ghost" onClick={handleClearFilters}>Limpiar filtros</Button>
          </div>
        </div>
      </Card>

      <Card className="shadow-lg">
        <CardHeader>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold text-gray-800">Historial global</h2>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">{totalLabel}</span>
              <select
                className="px-3 py-2 rounded-lg border border-gray-200 text-sm"
                value={pageSize}
                onChange={(e) => {
                  setPage(1);
                  setPageSize(Number(e.target.value));
                }}
                aria-label="Cantidad por página"
              >
                {PAGE_SIZES.map((size) => (
                  <option key={size} value={size}>{size} por página</option>
                ))}
              </select>
            </div>
          </div>
        </CardHeader>

        {loading ? (
          <LoadingState compact />
        ) : items.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Fecha</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Cliente</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Cédula</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Banco</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">N° crédito</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Estado</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-600">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.analysis_id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="py-4 px-4 text-sm text-gray-700">{formatDate(item.uploaded_at)}</td>
                      <td className="py-4 px-4 text-sm font-medium text-gray-800">{item.customer.full_name}</td>
                      <td className="py-4 px-4 text-sm text-gray-700">{item.customer.id_number || 'N/A'}</td>
                      <td className="py-4 px-4 text-sm text-gray-700">{item.bank.name || 'Sin banco'}</td>
                      <td className="py-4 px-4 text-sm text-gray-700">{item.credit_number || 'N/A'}</td>
                      <td className="py-4 px-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(item.status)}`}>
                          {getStatusText(item.status)}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center justify-center gap-2">
                          <AnalysisActions
                            compact
                            canViewDetail={item.actions.can_view_detail}
                            detailHref={`/dashboard/admin/analyses/${item.analysis_id}`}
                            canViewSummary={item.actions.can_view_summary}
                            summaryHref={`/dashboard/admin/analyses/${item.analysis_id}/summary`}
                            canDownloadPdf={item.actions.can_view_pdf && Boolean(item.document_id)}
                            onDownloadPdf={() => item.document_id && downloadDocument(item.document_id)}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="md:hidden space-y-3 px-4 pb-4">
              {items.map((item) => (
                <div key={item.analysis_id} className="border border-gray-100 rounded-xl p-4 space-y-3 bg-white">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-gray-800">{item.customer.full_name}</p>
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(item.status)}`}>
                      {getStatusText(item.status)}
                    </span>
                  </div>

                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>Cédula:</strong> {item.customer.id_number || 'N/A'}</p>
                    <p><strong>Banco:</strong> {item.bank.name || 'Sin banco'}</p>
                    <p><strong>N° crédito:</strong> {item.credit_number || 'N/A'}</p>
                    <p><strong>Fecha:</strong> {formatDate(item.uploaded_at)}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <AnalysisActions
                      canViewDetail={item.actions.can_view_detail}
                      detailHref={`/dashboard/admin/analyses/${item.analysis_id}`}
                      canViewSummary={item.actions.can_view_summary}
                      summaryHref={`/dashboard/admin/analyses/${item.analysis_id}/summary`}
                      canDownloadPdf={item.actions.can_view_pdf && Boolean(item.document_id)}
                      onDownloadPdf={() => item.document_id && downloadDocument(item.document_id)}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between px-4 py-4 border-t border-gray-100">
              <span className="text-sm text-gray-500">Página {page} de {totalPages}</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft size={16} />
                  Anterior
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Siguiente
                  <ChevronRight size={16} />
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

function LoadingState({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className="p-4 space-y-3">
        {Array.from({ length: 4 }).map((_, idx) => (
          <div key={idx} className="h-14 rounded-lg bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="h-20 rounded-xl bg-gray-100 animate-pulse" />
      <div className="h-56 rounded-xl bg-gray-100 animate-pulse" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-12 text-gray-500">
      <ArrowUpDown size={44} className="mx-auto mb-3 text-gray-300" />
      <p className="text-lg font-medium">No hay resultados</p>
      <p className="text-sm">Ajusta los filtros y vuelve a intentar.</p>
    </div>
  );
}

function formatDate(dateString: string | null) {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function normalizeText(value?: string) {
  if (!value) return undefined;
  const clean = value.trim();
  return clean.length > 0 ? clean : undefined;
}

function getStatusBadge(status: string) {
  return STATUS_BADGE[status] || 'bg-gray-100 text-gray-600';
}

function getStatusText(status: string) {
  return STATUS_TEXT[status] || status;
}
