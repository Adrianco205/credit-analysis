'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { EstudioHistorialItem } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader } from '@/components/ui/card';
import { 
    FileText, 
    Download, 
    Eye, 
    Building2, 
    Calendar, 
    ChevronLeft, 
    ChevronRight,
    ArrowLeft,
    AlertTriangle
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function HistorialPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    
    // History states
    const [estudios, setEstudios] = useState<EstudioHistorialItem[]>([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        loadHistorial();
    }, [page]);

    const loadHistorial = async () => {
        setLoading(true);
        try {
            const response = await apiClient.getEstudiosHistorial({ page, limit: 10 });
            setEstudios(response.estudios);
            setTotalPages(response.total_pages);
            setTotal(response.total);
        } catch (err: any) {
            console.error('Error loading historial:', err?.message || err?.error);
            setError(err?.message || 'Error al cargar el historial');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadDocument = async (documentId: string, filename?: string) => {
        try {
            const blob = await apiClient.downloadDocument(documentId);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || 'extracto.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err: any) {
            setError(err?.message || 'Error al descargar el documento');
        }
    };

    const formatDate = (dateString: string | null) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('es-CO', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const getStatusBadge = (status: string) => {
        const statusStyles: Record<string, string> = {
            'COMPLETED': 'bg-green-100 text-green-700',
            'PROCESSING': 'bg-yellow-100 text-yellow-700',
            'PENDING': 'bg-gray-100 text-gray-600',
            'PENDING_MANUAL': 'bg-blue-100 text-blue-700',
            'EXTRACTED': 'bg-green-100 text-green-700',
            'FAILED': 'bg-red-100 text-red-700',
            'ERROR': 'bg-red-100 text-red-700',
            'ID_MISMATCH': 'bg-orange-100 text-orange-700',
            'NAME_MISMATCH': 'bg-amber-100 text-amber-700',
        };
        return statusStyles[status] || 'bg-gray-100 text-gray-600';
    };

    const getStatusText = (status: string) => {
        const statusTexts: Record<string, string> = {
            'COMPLETED': 'Completado',
            'PROCESSING': 'Procesando',
            'PENDING': 'Pendiente',
            'PENDING_MANUAL': 'Datos pendientes',
            'EXTRACTED': 'Extraído',
            'FAILED': 'Fallido',
            'ERROR': 'Error',
            'ID_MISMATCH': 'Cédula no coincide',
            'NAME_MISMATCH': 'Nombre no coincide',
        };
        return statusTexts[status] || status;
    };
    
    // Estados que permiten ver el resumen (tienen datos extraídos)
    const canViewSummary = (status: string) => {
        return ['COMPLETED', 'EXTRACTED', 'NAME_MISMATCH', 'PENDING_MANUAL'].includes(status);
    };

    if (loading && estudios.length === 0) {
        return (
            <div className="flex items-center justify-center h-[50vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--verde-hoja)]"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard">
                        <Button variant="ghost" size="sm">
                            <ArrowLeft size={16} className="mr-1" />
                            Volver
                        </Button>
                    </Link>
                    <h1 className="text-2xl font-bold text-[var(--verde-bosque)] flex items-center gap-2">
                        <Calendar className="text-[var(--verde-hoja)]" />
                        Historial de Estudios
                    </h1>
                </div>
                <Link href="/dashboard/analysis/new">
                    <Button variant="primary">
                        <FileText size={16} className="mr-2" />
                        Nuevo Análisis
                    </Button>
                </Link>
            </div>

            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-lg border border-red-200 flex items-center gap-2">
                    <AlertTriangle size={20} />
                    <span>{error}</span>
                </div>
            )}

            {/* Historial Card */}
            <Card className="shadow-lg">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-gray-800">
                            Tus Análisis de Crédito
                        </h2>
                        {total > 0 && (
                            <span className="text-sm text-gray-500">
                                {total} análisis realizado{total !== 1 ? 's' : ''}
                            </span>
                        )}
                    </div>
                </CardHeader>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--verde-hoja)]"></div>
                    </div>
                ) : estudios.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                        <FileText size={48} className="mx-auto mb-4 text-gray-300" />
                        <p className="text-lg font-medium">No tienes análisis realizados</p>
                        <p className="text-sm mb-6">Sube tu primer extracto bancario para comenzar</p>
                        <Link href="/dashboard/analysis/new">
                            <Button variant="primary">
                                <FileText size={16} className="mr-2" />
                                Crear Primer Análisis
                            </Button>
                        </Link>
                    </div>
                ) : (
                    <>
                        {/* Table */}
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-gray-50 border-b border-gray-200">
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Documento</th>
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Banco / Crédito</th>
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Fecha de analisis</th>
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Estado</th>
                                        <th className="text-center py-3 px-4 text-sm font-semibold text-gray-600">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {estudios.map((estudio) => (
                                        <tr key={estudio.analisis_id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                            {/* Documento */}
                                            <td className="py-4 px-4">
                                                {estudio.documento_id ? (
                                                    <button
                                                        onClick={() => handleDownloadDocument(estudio.documento_id!)}
                                                        className="flex items-center gap-2 text-[var(--verde-hoja)] hover:text-[var(--verde-bosque)] transition-colors group"
                                                    >
                                                        <div className="w-10 h-10 bg-[var(--verde-suave)] rounded-lg flex items-center justify-center group-hover:bg-[var(--verde-hoja)] transition-colors">
                                                            <Download size={18} className="text-[var(--verde-hoja)] group-hover:text-white" />
                                                        </div>
                                                        <span className="text-sm font-medium underline">Descargar PDF</span>
                                                    </button>
                                                ) : (
                                                    <span className="text-gray-400 text-sm">Sin documento</span>
                                                )}
                                            </td>

                                            {/* Banco / Crédito */}
                                            <td className="py-4 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                                                        <Building2 size={16} className="text-gray-500" />
                                                    </div>
                                                    <div>
                                                        <p className="font-medium text-gray-800">{estudio.banco_nombre || 'Banco no identificado'}</p>
                                                        <p className="text-xs text-gray-500">{estudio.numero_credito || 'Sin número'}</p>
                                                    </div>
                                                </div>
                                            </td>

                                            {/* Fecha */}
                                            <td className="py-4 px-4">
                                                <span className="text-sm text-gray-600">{formatDate(estudio.fecha_subida)}</span>
                                            </td>

                                            {/* Estado */}
                                            <td className="py-4 px-4">
                                                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(estudio.status)}`}>
                                                    {getStatusText(estudio.status)}
                                                </span>
                                            </td>

                                            {/* Acciones */}
                                            <td className="py-4 px-4 text-center">
                                                {canViewSummary(estudio.status) ? (
                                                    <Link href={`/dashboard/analysis/${estudio.analisis_id}/summary`}>
                                                        <Button variant="secondary" size="sm" className="inline-flex items-center gap-1">
                                                            <Eye size={16} />
                                                            Ver Resumen
                                                        </Button>
                                                    </Link>
                                                ) : (
                                                    <Button variant="ghost" size="sm" disabled className="text-gray-400">
                                                        <Eye size={16} className="mr-1" />
                                                        No disponible
                                                    </Button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between px-4 py-4 border-t border-gray-100">
                                <span className="text-sm text-gray-500">
                                    Página {page} de {totalPages}
                                </span>
                                <div className="flex items-center gap-2">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setPage(p => Math.max(1, p - 1))}
                                        disabled={page === 1}
                                    >
                                        <ChevronLeft size={16} />
                                        Anterior
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                        disabled={page === totalPages}
                                    >
                                        Siguiente
                                        <ChevronRight size={16} />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </Card>
        </div>
    );
}
