import React from 'react';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import Roles from '../roles/Roles';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockRoles = [
  { id: 1, name: 'Administrator', slug: 'admin', permissions: ['FILE_READ', 'FILE_WRITE'], built_in: true },
  { id: 2, name: 'Technologist', slug: 'technologist', permissions: ['FILE_READ'], built_in: true },
  { id: 3, name: 'Custom Role', slug: 'custom', permissions: ['PATIENT_READ'], built_in: false },
];

async function waitForTable() {
  await screen.findByText('Administrator');
}

describe('Roles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockImplementation(() => Promise.resolve({ data: mockRoles }));
    localStorage.setItem('token', 't');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('admin', 'true');
  });

  function renderWithAuth(ui: React.ReactElement) {
    return render(
      <AuthProvider>
        <MemoryRouter>
          {ui}
        </MemoryRouter>
      </AuthProvider>
    );
  }

  it('renders Role Name column header', async () => {
    renderWithAuth(<Roles />);
    const headers = await screen.findAllByText('Role Name');
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
    mockRequest.mockImplementation(() => Promise.resolve({ data: { id: 4 } }));

    await user.click(screen.getByText('Create Role'));

    const modal = screen.getByRole('dialog');
    await user.type(within(modal).getByLabelText('Role Name'), 'Test Role');
    await user.type(within(modal).getByLabelText('Slug'), 'test-role');
    await user.click(within(modal).getByText('FILE_READ'));

    await user.click(within(modal).getByText('OK'));

    expect(mockRequest).toHaveBeenCalledWith('roles', {
      data: { name: 'Test Role', slug: 'test-role', permissions: ['FILE_READ'] },
    });
  });

  it('edit modal opens with pre-filled values when clicking edit', async () => {
    const user = userEvent.setup();
    mockRequest.mockImplementation((url: string) => {
      if (url === 'roles/3') return Promise.resolve({ data: mockRoles[2] });
      return Promise.resolve({ data: mockRoles });
    });
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtn = screen.getAllByTitle('Edit')[0];
    await user.click(editBtn);

    const modal = screen.getByRole('dialog');
    expect(within(modal).getByDisplayValue('Custom Role')).toBeInTheDocument();
    expect(within(modal).getByDisplayValue('custom')).toBeInTheDocument();
  });

  it('edit role sends updated permissions', async () => {
    const user = userEvent.setup();
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (opts?.data?.permissions) return Promise.resolve({ data: { id: 3 } });
      return Promise.resolve({ data: mockRoles });
    });
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getAllByTitle('Edit')[0]);

    const modal = screen.getByRole('dialog');
    await user.click(within(modal).getByText('PATIENT_READ'));
    await user.click(within(modal).getByText('FILE_READ'));
    await user.click(within(modal).getByText('OK'));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('roles/3', {
        data: { permissions: ['FILE_READ'] },
      });
    });
  });

  it('delete role calls API and refreshes list', async () => {
    const user = userEvent.setup();
    mockRequest.mockImplementation(() => Promise.resolve({ data: mockRoles }));
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getAllByTitle('Delete')[0]);

    const confirmBtn = screen.getByRole('button', { name: /yes|confirm|ok/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('roles/3', { data: undefined, method: 'DELETE' });
    });
  });

  it('does not show edit/delete for built-in roles', async () => {
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtns = screen.queryAllByTitle('Edit');
    const deleteBtns = screen.queryAllByTitle('Delete');
    expect(editBtns.length).toBe(1);
    expect(deleteBtns.length).toBe(1);
  });
});