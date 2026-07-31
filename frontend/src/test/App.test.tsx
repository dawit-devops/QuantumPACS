import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import { ThemeProvider } from '../common/ThemeProvider';
import Login from '../login/Login';

describe('Login', () => {
  it('renders login form', () => {
    render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    );
    expect(screen.getByText(/Sign in to your account/)).toBeInTheDocument();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });
});
