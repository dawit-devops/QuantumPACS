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

const mockData = {
  totals: { patients: 10, studies: 20, series: 30, files: 40, users: 5, storage_bytes: 1000000 },
  modalities: { CT: 15, MR: 10, XA: 8 },
  ingestion_30d: [
    { date: '2026-07-20', count: 5 },
    { date: '2026-07-21', count: 12 },
    { date: '2026-07-22', count: 8 },
  ],
  latest_files: [{ id: 1, name: 'test.dcm', created: '2026-07-26' }],
};

describe('Metrics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders skeleton while loading', () => {
    mockRequest.mockReturnValue(new Promise(() => {}));
    renderWithAuth(<Metrics />);

    expect(screen.getByTestId('metrics-skeleton')).toBeInTheDocument();
  });

  it('renders stat cards after data loads', async () => {
    mockRequest.mockResolvedValue(mockData);
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

  it('renders modality distribution as a chart with canvas', async () => {
    mockRequest.mockResolvedValue(mockData);
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText('Modality Distribution')).toBeInTheDocument();
    });

    const canvases = document.querySelectorAll('canvas');
    expect(canvases.length).toBeGreaterThanOrEqual(1);
  });

  it('renders ingestion chart with canvas', async () => {
    mockRequest.mockResolvedValue(mockData);
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText('Ingestion (30 days)')).toBeInTheDocument();
    });

    const canvases = document.querySelectorAll('canvas');
    expect(canvases.length).toBeGreaterThanOrEqual(2);
  });

  it('renders system health pills', async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === 'v2/health') return Promise.resolve({
        status: 'ok',
        components: {
          database: { status: 'ok', latency_ms: 2 },
          elasticsearch: { status: 'ok', latency_ms: 5 },
          redis: { status: 'ok', latency_ms: 1 },
          storage: { status: 'ok', latency_ms: 3 },
          dicom_listener: { status: 'degraded', latency_ms: 200 },
          ingestion_service: { status: 'ok', latency_ms: 10 },
        },
      });
      return Promise.resolve(mockData);
    });
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText('System Health')).toBeInTheDocument();
    });

    expect(screen.getByText('Database')).toBeInTheDocument();
    expect(screen.getByText('DICOM Listener')).toBeInTheDocument();
    expect(screen.getByText('DEGRADED')).toBeInTheDocument();
  });

  it('renders component latency chart', async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url === 'v2/health') return Promise.resolve({
        status: 'ok',
        components: {
          database: { status: 'ok', latency_ms: 2 },
          elasticsearch: { status: 'degraded', latency_ms: 500 },
        },
      });
      return Promise.resolve(mockData);
    });
    renderWithAuth(<Metrics />);

    await waitFor(() => {
      expect(screen.getByText('Component Latency')).toBeInTheDocument();
    });

    const canvases = document.querySelectorAll('canvas');
    expect(canvases.length).toBeGreaterThanOrEqual(2);
  });
});
