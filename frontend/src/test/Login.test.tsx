import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import Login from '../login/Login';

describe('Login', () => {
  it('renders within MemoryRouter', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
  });

  it('renders username input', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument();
  });

  it('renders password input', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
  });

  it('renders Sign In button', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('renders QuantumLogo', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    const svg = document.querySelector('svg');
    expect(svg?.textContent).toContain('Quantum');
    expect(screen.getByText('PACS')).toBeInTheDocument();
  });

  it('renders tagline', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    expect(screen.getByText('QuantumPACS v1.0 — Diagnostic Clarity, Quantum Fast')).toBeInTheDocument();
  });
});