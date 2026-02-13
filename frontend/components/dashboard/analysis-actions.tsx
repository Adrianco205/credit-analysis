'use client';

import Link from 'next/link';
import { Download, Eye } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface AnalysisActionsProps {
  summaryHref?: string;
  detailHref?: string;
  canViewSummary: boolean;
  canViewDetail?: boolean;
  canDownloadPdf?: boolean;
  onDownloadPdf?: () => void;
  compact?: boolean;
}

export function AnalysisActions({
  summaryHref,
  detailHref,
  canViewSummary,
  canViewDetail = false,
  canDownloadPdf = false,
  onDownloadPdf,
  compact = false,
}: AnalysisActionsProps) {
  return (
    <div className={`flex items-center ${compact ? 'justify-center' : 'justify-start'} gap-2`}>
      {canViewDetail && detailHref ? (
        <Link href={detailHref}>
          <Button variant="ghost" size="sm" title="Ver detalle" aria-label="Ver detalle">
            Detalle
          </Button>
        </Link>
      ) : canViewDetail ? (
        <Button variant="ghost" size="sm" disabled title="Detalle no disponible" aria-label="Detalle no disponible">
          Detalle
        </Button>
      ) : null}

      {canViewSummary && summaryHref ? (
        <Link href={summaryHref}>
          <Button variant="secondary" size="sm" title="Ver resumen" aria-label="Ver resumen">
            <Eye size={16} className={compact ? '' : 'mr-1'} />
            {!compact && 'Ver Resumen'}
          </Button>
        </Link>
      ) : (
        <Button variant="ghost" size="sm" disabled title="Resumen no disponible" aria-label="Resumen no disponible">
          <Eye size={16} className={compact ? '' : 'mr-1'} />
          {!compact && 'No disponible'}
        </Button>
      )}

      {canDownloadPdf ? (
        <Button
          variant="ghost"
          size="sm"
          onClick={onDownloadPdf}
          title="Descargar PDF"
          aria-label="Descargar PDF"
        >
          <Download size={16} className={compact ? '' : 'mr-1'} />
          {!compact && 'PDF'}
        </Button>
      ) : null}
    </div>
  );
}
