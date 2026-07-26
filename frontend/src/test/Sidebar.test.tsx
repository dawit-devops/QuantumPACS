import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import Sidebar from '../common/Sidebar';

vi.mock('../helpers', () => ({
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

describe('Sidebar', () => {
  function renderWithAuth(ui: React.ReactElement) {
    return render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          {ui}
        </MemoryRouter>
      </AuthProvider>
    );
  }

  it('renders Files nav item', () => {
    renderWithAuth(<Sidebar />);
    expect(screen.getByText('Files')).toBeInTheDocument();
  });

  it('renders Account nav item', () => {
    renderWithAuth(<Sidebar />);
    expect(screen.getByText('Account')).toBeInTheDocument();
  });

  it('renders Logout nav item', () => {
    renderWithAuth(<Sidebar />);
    expect(screen.getByText('Logout')).toBeInTheDocument();
  });

  it('renders Admin submenu for admin users', () => {
    renderWithAuth(<Sidebar />);
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('shows submenu items when Admin is clicked', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Sidebar />);
    await user.click(screen.getByText('Admin'));
    expect(screen.getByText('Replicas')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Logs')).toBeInTheDocument();
  });

  it('renders QuantumLogo', () => {
    renderWithAuth(<Sidebar />);
    const svg = document.querySelector('svg');
    expect(svg?.textContent).toContain('Quantum');
  });

  it('does not render Admin submenu for non-admin users', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('admin', 'false');
    localStorage.setItem('role', 'user');

    vi.resetModules();
    vi.doMock('../helpers', () => ({
      isAdmin: () => false,
      request: () => Promise.resolve({}),
    }));

    const NonAdminSidebar = React.lazy(() => import('../common/Sidebar'));
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <React.Suspense fallback={null}>
            <NonAdminSidebar />
          </React.Suspense>
        </MemoryRouter>
      </AuthProvider>
    );
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });
});
