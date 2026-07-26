import React from 'react';
import { render, screen } from '@testing-library/react';
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

describe('Tenants', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockResolvedValue({ data: mockTenants });
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
});
