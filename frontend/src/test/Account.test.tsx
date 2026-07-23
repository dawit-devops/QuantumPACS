import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import Account from '../account/Account';

describe('Account', () => {
  beforeEach(() => {
    localStorage.setItem('tempKey', 'test-key');
  });

  it('renders within MemoryRouter', () => {
    render(
      <MemoryRouter>
        <Account />
      </MemoryRouter>
    );
  });

  it('renders password field', () => {
    render(
      <MemoryRouter>
        <Account />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
  });

  it('renders password repeated field', () => {
    render(
      <MemoryRouter>
        <Account />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Password repeated')).toBeInTheDocument();
  });

  it('renders Change password button', () => {
    render(
      <MemoryRouter>
        <Account />
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: 'Change password' })).toBeInTheDocument();
  });
});