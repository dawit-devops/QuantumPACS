import React from 'react';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import Tenants from '../tenants/Tenants';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockTenants = [
  { id: '1', name: 'Main Hospital', slug: 'main', status: 'active', domain: 'main.example.com' },
  { id: '2', name: 'North Clinic', slug: 'north', status: 'active', domain: 'north.example.com' },
];

const mockStats = {
  user_count: 42, study_count: 1500, file_count: 12000,
  storage_used_bytes: 536870912000, last_activity: '2026-07-28T12:00:00Z',
};

async function waitForTable() {
  await screen.findByText('Main Hospital');
}

describe('Tenants', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url.includes('/stats')) return Promise.resolve({ data: mockStats });
      if (opts?.method === 'DELETE') return Promise.resolve({});
      return Promise.resolve({ data: mockTenants });
    });
    localStorage.setItem('token', 't');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('admin', 'true');
  });

  function renderWithAuth(ui: React.ReactElement) {
    return render(
      <AuthProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </AuthProvider>
    );
  }

  it('renders Tenant Name column header', async () => {
    renderWithAuth(<Tenants />);
    const headers = await screen.findAllByText('Tenant Name');
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it('displays tenant names from API', async () => {
    renderWithAuth(<Tenants />);
    const main = await screen.findAllByText('Main Hospital');
    expect(main.length).toBeGreaterThanOrEqual(1);
    const north = await screen.findAllByText('North Clinic');
    expect(north.length).toBeGreaterThanOrEqual(1);
  });

  it('shows health indicators for each tenant', async () => {
    renderWithAuth(<Tenants />);
    await waitForTable();
    const indicators = document.querySelectorAll('.tenant-health-dot');
    expect(indicators.length).toBe(2);
  });

  it('calls stats endpoint for each tenant', async () => {
    renderWithAuth(<Tenants />);
    await waitForTable();
    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('tenants/1/stats');
      expect(mockRequest).toHaveBeenCalledWith('tenants/2/stats');
    });
  });

  it('renders stats columns in table header', async () => {
    renderWithAuth(<Tenants />);
    await waitForTable();
    expect(screen.getByText('Users')).toBeInTheDocument();
  });

  it('decommission button opens confirmation', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForTable();

    await user.click(screen.getAllByTitle('Decommission')[0]);
    const confirmBtn = screen.getByRole('button', { name: /yes|confirm|ok/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('tenants/1', { data: undefined, method: 'DELETE' });
    });
  });
});
