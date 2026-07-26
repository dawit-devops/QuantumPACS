import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
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

describe('Roles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockResolvedValue({ data: mockRoles });
  });

  it('renders Role Name column header', async () => {
    render(
      <MemoryRouter>
        <Roles />
      </MemoryRouter>
    );

    const headers = await screen.findAllByText('Role Name');
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it('displays role names from API', async () => {
    render(
      <MemoryRouter>
        <Roles />
      </MemoryRouter>
    );

    const admins = await screen.findAllByText('Administrator');
    expect(admins.length).toBeGreaterThanOrEqual(1);
    const techs = await screen.findAllByText('Technologist');
    expect(techs.length).toBeGreaterThanOrEqual(1);
    const customs = await screen.findAllByText('Custom Role');
    expect(customs.length).toBeGreaterThanOrEqual(1);
  });
});
