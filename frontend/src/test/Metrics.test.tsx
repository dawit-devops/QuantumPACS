import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../auth/AuthContext';
import Metrics from '../metrics/Metrics';

const mockRequest = vi.fn();
vi.mock('../helpers', () => ({
  request: (...args: any[]) => mockRequest(...args),
  isAdmin: () => false,
}));

vi.mock('../common/QuantumLogo', () => ({
  default: () => <div>Logo</div>,
}));

function renderWithAuth(ui: React.ReactElement) {
  return render(
    <AuthProvider>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </AuthProvider>
  );
}

describe('Metrics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading spinner initially', () => {
    mockRequest.mockReturnValue(new Promise(() => {}));
    renderWithAuth(<Metrics />);
    expect(screen.getByTestId('metrics-loading')).toBeInTheDocument();
  });

  it('renders stat cards after data loads', async () => {
    mockRequest.mockResolvedValue({
      totals: { patients: 10, studies: 20, series: 30, files: 40, users: 5, storage_bytes: 1000000 },
      modalities: { CT: 15, MR: 10 },
      ingestion_30d: [{ date: '2026-07-20', count: 5 }],
      latest_files: [{ id: 1, name: 'test.dcm', created: '2026-07-26' }],
    });

    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText('Patients')).toBeInTheDocument();
    });

    const tens = screen.getAllByText('10');
    expect(tens.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('40')).toBeInTheDocument();
    expect(screen.getByText('976.6 KB')).toBeInTheDocument();
  });

  it('renders modality and ingestion tables', async () => {
    mockRequest.mockResolvedValue({
      totals: {},
      modalities: { CT: 15, MR: 10 },
      ingestion_30d: [{ date: '2026-07-20', count: 5 }],
      latest_files: [],
    });

    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText('Modality Distribution')).toBeInTheDocument();
    });

    expect(screen.getByText('CT')).toBeInTheDocument();
    expect(screen.getByText('MR')).toBeInTheDocument();
    expect(screen.getByText('2026-07-20')).toBeInTheDocument();
  });
});
