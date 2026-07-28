import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import MobileNav from '../common/MobileNav';

vi.mock('../helpers', () => ({
  isAdmin: () => false,
}));

function renderWithRouter(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <MobileNav />
    </MemoryRouter>
  );
}

describe('MobileNav', () => {
  it('renders Files, Metrics, and Account links', () => {
    renderWithRouter('/');
    expect(screen.getByText('Files')).toBeInTheDocument();
    expect(screen.getByText('Metrics')).toBeInTheDocument();
    expect(screen.getByText('Account')).toBeInTheDocument();
  });

  it('highlights Files as active on root path', () => {
    renderWithRouter('/');
    const filesLink = screen.getByText('Files').closest('a');
    expect(filesLink?.className).toContain('active');
  });

  it('highlights Metrics as active on /metrics', () => {
    renderWithRouter('/metrics');
    const metricsLink = screen.getByText('Metrics').closest('a');
    expect(metricsLink?.className).toContain('active');
  });

  it('highlights Account as active on /account', () => {
    renderWithRouter('/account');
    const accountLink = screen.getByText('Account').closest('a');
    expect(accountLink?.className).toContain('active');
  });

  it('has accessible labels on nav items', () => {
    renderWithRouter('/');
    const nav = document.querySelector('nav');
    expect(nav).toBeInTheDocument();
    const links = nav!.querySelectorAll('a');
    expect(links.length).toBe(3);
  });
});
