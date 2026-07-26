import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import TenantSelector from '../auth/TenantSelector';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockTenants = [
  { id: '1', name: 'Main Hospital', slug: 'main' },
  { id: '2', name: 'North Clinic', slug: 'north' },
];

describe('TenantSelector', () => {
  it('renders tenant name when active tenant is set in localStorage', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('username', 'admin');
    localStorage.setItem('admin', 'true');
    localStorage.setItem('role', 'admin');
    localStorage.setItem('tenant_id', 'main');
    localStorage.setItem('tenant_name', 'Main Hospital');

    mockRequest.mockResolvedValue({ data: mockTenants });

    render(
      <MemoryRouter>
        <AuthProvider>
          <TenantSelector />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Main Hospital')).toBeInTheDocument();
  });
});
