import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import NotFound from '../notfound/NotFound';

describe('NotFound', () => {
  it('renders without crashing', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );
  });

  it('renders heading', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );
    expect(screen.getByText('Oops! Page not found')).toBeInTheDocument();
  });

  it('renders link to home page', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );
    const link = screen.getByRole('link', { name: /Go to home page/ });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/');
  });
});