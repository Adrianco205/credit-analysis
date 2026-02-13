import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AdminAnalysesPage from './page';
import { apiClient } from '@/lib/api-client';

const replaceMock = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock('@/lib/api-client', () => ({
  apiClient: {
    getProfile: vi.fn(),
    getAdminAnalyses: vi.fn(),
    downloadAdminDocument: vi.fn(),
  },
}));

const baseResponse = {
  data: [
    {
      analysis_id: 'an-1',
      uploaded_at: '2026-02-13T10:00:00Z',
      document_id: 'doc-1',
      credit_number: 'CR-001',
      status: 'COMPLETED',
      customer: { user_id: 'u-1', full_name: 'Juan Pérez', id_number: '123' },
      bank: { id: 1, name: 'Bancolombia' },
      actions: { can_view_summary: true, can_view_detail: true, can_view_pdf: true },
    },
  ],
  pagination: { page: 1, page_size: 25, total: 2, total_pages: 2 },
  filters: { bank_options: [{ id: 1, name: 'Bancolombia' }] },
};

describe('AdminAnalysesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getProfile as any).mockResolvedValue({ rol: 'ADMIN' });
  });

  it('aplica filtros server-side al hacer click en Aplicar filtros', async () => {
    (apiClient.getAdminAnalyses as any).mockResolvedValue(baseResponse);

    render(<AdminAnalysesPage />);

    await waitFor(() => {
      expect(apiClient.getAdminAnalyses).toHaveBeenCalledTimes(1);
    });

    const nameInput = screen.getByPlaceholderText('Nombre o apellidos');
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Carlos');

    const applyButton = screen.getByRole('button', { name: 'Aplicar filtros' });
    await userEvent.click(applyButton);

    await waitFor(() => {
      expect(apiClient.getAdminAnalyses).toHaveBeenCalledTimes(2);
    });

    const secondCall = (apiClient.getAdminAnalyses as any).mock.calls[1][0];
    expect(secondCall.customer_name).toBe('Carlos');
    expect(secondCall.page).toBe(1);
  });

  it('cambia de página y solicita page=2 al pulsar Siguiente', async () => {
    (apiClient.getAdminAnalyses as any)
      .mockResolvedValueOnce(baseResponse)
      .mockResolvedValueOnce({
        ...baseResponse,
        pagination: { ...baseResponse.pagination, page: 2 },
      });

    render(<AdminAnalysesPage />);

    await waitFor(() => {
      expect(apiClient.getAdminAnalyses).toHaveBeenCalledTimes(1);
    });

    const nextButton = screen.getByRole('button', { name: /Siguiente/i });
    await userEvent.click(nextButton);

    await waitFor(() => {
      expect(apiClient.getAdminAnalyses).toHaveBeenCalledTimes(2);
    });

    const secondCall = (apiClient.getAdminAnalyses as any).mock.calls[1][0];
    expect(secondCall.page).toBe(2);
  });
});
