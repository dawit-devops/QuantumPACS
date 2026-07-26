import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Users from '../users/Users';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockUsers = [
  { id: 1, username: 'admin', admin: true, status: 'active', role_name: 'Administrator', role_slug: 'admin' },
  { id: 2, username: 'tech1', admin: false, status: 'active', role_name: 'Technologist', role_slug: 'technologist' },
  { id: 3, username: 'dr.jane', admin: false, status: 'active', role_name: 'Radiologist', role_slug: 'radiologist' },
];

describe('Users', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockResolvedValue({ data: mockUsers });
  });

  it('renders Role column header', async () => {
    render(
      <MemoryRouter>
        <Users />
      </MemoryRouter>
    );

    const headers = await screen.findAllByText('Role');
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it('displays role name for each user', async () => {
    render(
      <MemoryRouter>
        <Users />
      </MemoryRouter>
    );

    const admins = await screen.findAllByText('Administrator');
    expect(admins.length).toBeGreaterThanOrEqual(1);
    const techs = await screen.findAllByText('Technologist');
    expect(techs.length).toBeGreaterThanOrEqual(1);
    const rads = await screen.findAllByText('Radiologist');
    expect(rads.length).toBeGreaterThanOrEqual(1);
  });
});
