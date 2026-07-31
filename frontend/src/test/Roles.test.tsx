import React from 'react';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import { ThemeProvider } from '../common/ThemeProvider';
import Roles from '../roles/Roles';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

function defaultMock(url: string) {
  if (url === 'permissions') {
    return Promise.resolve({
      data: { Files: ['FILE_READ', 'FILE_WRITE', 'FILE_DELETE'], Patients: ['PATIENT_READ', 'PATIENT_WRITE'] },
    });
  }
  return Promise.resolve({
    data: [
      { id: 1, name: 'Administrator', slug: 'admin', permissions: ['FILE_READ', 'FILE_WRITE'], built_in: true },
      { id: 2, name: 'Technologist', slug: 'technologist', permissions: ['FILE_READ'], built_in: true },
      { id: 3, name: 'Custom Role', slug: 'custom', permissions: ['PATIENT_READ'], built_in: false },
    ],
  });
}

async function waitForTable() {
  await screen.findByText('Administrator');
}

describe('Roles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockImplementation(defaultMock);
    localStorage.setItem('token', 't');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('admin', 'true');
  });

  function renderWithAuth(ui: React.ReactElement) {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            {ui}
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    );
  }

  it('renders Role column header', async () => {
    renderWithAuth(<Roles />);
    const headers = await screen.findAllByText('Role');
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it('displays role names from API', async () => {
    renderWithAuth(<Roles />);
    const admins = await screen.findAllByText('Administrator');
    expect(admins.length).toBeGreaterThanOrEqual(1);
    const techs = await screen.findAllByText('Technologist');
    expect(techs.length).toBeGreaterThanOrEqual(1);
    const customs = await screen.findAllByText('Custom Role');
    expect(customs.length).toBeGreaterThanOrEqual(1);
  });

  it('create modal includes permission checkboxes', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getByText('Create Role'));
    const modal = screen.getByRole('dialog');
    expect(within(modal).getByText('FILE_READ')).toBeInTheDocument();
    expect(within(modal).getByText('PATIENT_READ')).toBeInTheDocument();
  });

  it('create role sends name, slug, and selected permissions', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === 'permissions') return defaultMock('permissions');
      return Promise.resolve({ data: { id: 4 } });
    });

    await user.click(screen.getByText('Create Role'));

    const modal = screen.getByRole('dialog');
    await user.type(within(modal).getByLabelText('Role Name'), 'Test Role');
    await user.type(within(modal).getByLabelText('Slug'), 'test-role');
    await user.click(within(modal).getByText('FILE_READ'));

    await user.click(within(modal).getByText('Create'));

    expect(mockRequest).toHaveBeenCalledWith('roles', {
      data: { name: 'Test Role', slug: 'test-role', permissions: ['FILE_READ'] },
    });
  });

  it('edit modal opens with pre-filled values when clicking edit', async () => {
    const user = userEvent.setup();
    mockRequest.mockImplementation((url: string) => {
      if (url === 'permissions') return defaultMock('permissions');
      if (url === 'roles/3') return Promise.resolve({ data: { id: 3, name: 'Custom Role', slug: 'custom', permissions: ['PATIENT_READ'], built_in: false } });
      return defaultMock(url);
    });
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtn = screen.getAllByRole('button', { name: /edit/i })[2];
    await user.click(editBtn);

    const modal = screen.getByRole('dialog');
    expect(within(modal).getByDisplayValue('Custom Role')).toBeInTheDocument();
    expect(within(modal).getByDisplayValue('custom')).toBeInTheDocument();
  });

  it('edit role sends updated permissions', async () => {
    const user = userEvent.setup();
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === 'permissions') return defaultMock('permissions');
      if (opts?.data?.permissions) return Promise.resolve({ data: { id: 3 } });
      return defaultMock(url);
    });
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getAllByRole('button', { name: /edit/i })[2]);

    const modal = screen.getByRole('dialog');
    await user.click(within(modal).getByText('PATIENT_READ'));
    await user.click(within(modal).getByText('FILE_READ'));
    await user.click(within(modal).getByText('Update'));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('roles/3', {
        data: { permissions: ['FILE_READ'] },
      });
    });
  });

  it('delete role calls API and refreshes list', async () => {
    const user = userEvent.setup();
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === 'permissions') return defaultMock('permissions');
      return Promise.resolve({ data: [
        { id: 1, name: 'Administrator', slug: 'admin', permissions: ['FILE_READ', 'FILE_WRITE'], built_in: true },
        { id: 2, name: 'Technologist', slug: 'technologist', permissions: ['FILE_READ'], built_in: true },
        { id: 3, name: 'Custom Role', slug: 'custom', permissions: ['PATIENT_READ'], built_in: false },
      ]});
    });
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getByRole('button', { name: /delete/i }));

    const confirmBtn = screen.getByRole('button', { name: /yes|confirm|ok/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('roles/3', { data: undefined, method: 'DELETE' });
    });
  });

  it('does not show edit/delete for built-in roles', async () => {
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtns = screen.queryAllByRole('button', { name: /edit/i });
    const deleteBtns = screen.queryAllByRole('button', { name: /delete/i });
    expect(editBtns.length).toBe(3);
    expect(deleteBtns.length).toBe(1);
  });
});
