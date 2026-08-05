import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import Sidebar from '../common/Sidebar';

vi.mock('../helpers', () => ({
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

describe('Sidebar', () => {
  it('renders Files nav item', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText('Files')).toBeInTheDocument();
  });

  it('renders Account nav item', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText('Account')).toBeInTheDocument();
  });

  it('renders Logout nav item', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText('Logout')).toBeInTheDocument();
  });

  it('renders Admin submenu for admin users', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('shows submenu items when Admin is clicked', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );
    await user.click(screen.getByText('Admin'));
    expect(screen.getByText('Replicas')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Logs')).toBeInTheDocument();
  });

  it('renders QuantumLogo', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );
    const svg = document.querySelector('svg');
    expect(svg?.textContent).toContain('Quantum');
  });

  it('does not render Admin submenu for non-admin users', () => {
    vi.resetModules();
    vi.doMock('../helpers', () => ({
      isAdmin: () => false,
    }));

    const NonAdminSidebar = React.lazy(() => import('../common/Sidebar'));
    render(
      <MemoryRouter initialEntries={['/']}>
        <React.Suspense fallback={null}>
          <NonAdminSidebar />
        </React.Suspense>
      </MemoryRouter>
    );
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });
});
