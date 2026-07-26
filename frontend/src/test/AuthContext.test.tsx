import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import { AuthProvider, useAuth } from '../auth/AuthContext';
import ProtectedRoute from '../auth/ProtectedRoute';
import RequirePermission from '../auth/RequirePermission';

function TestConsumer() {
  const { isAuthenticated, user } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      {user && <div data-testid="auth-user">{user.username}</div>}
    </div>
  );
}

function BrokenComponent() {
  useAuth();
  return <div />;
}

function SignInTestConsumer() {
  const { isAuthenticated, user, signIn } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      {user && <div data-testid="auth-user">{user.username}</div>}
      <button
        data-testid="signin-btn"
        onClick={() => signIn('test-token', { id: 'u1', username: 'alice', admin: false, role: 'user' })}
      >
        Sign In
      </button>
    </div>
  );
}

function SignOutTestConsumer() {
  const { isAuthenticated, user, signOut } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      {user && <div data-testid="auth-user">{user.username}</div>}
      <button data-testid="signout-btn" onClick={() => signOut()}>Sign Out</button>
    </div>
  );
}

describe('AuthProvider', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('provides isAuthenticated=false when no token exists', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
  });

  it('signIn sets localStorage and updates auth state', async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <SignInTestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');

    await user.click(screen.getByTestId('signin-btn'));

    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
    expect(screen.getByTestId('auth-user')).toHaveTextContent('alice');
    expect(localStorage.getItem('token')).toBe('test-token');
    expect(localStorage.getItem('userId')).toBe('u1');
    expect(localStorage.getItem('username')).toBe('alice');
  });

  it('signOut clears localStorage and sets isAuthenticated to false', async () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('username', 'alice');
    localStorage.setItem('admin', 'false');

    const user = userEvent.setup();
    render(
      <AuthProvider>
        <SignOutTestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');

    await user.click(screen.getByTestId('signout-btn'));

    expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('userId')).toBeNull();
    expect(screen.queryByTestId('auth-user')).toBeNull();
  });

  it('RequirePermission renders children when user has the required permission', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('username', 'admin-user');
    localStorage.setItem('admin', 'true');
    localStorage.setItem('role', 'admin');

    render(
      <AuthProvider>
        <RequirePermission permission="admin">
          <div data-testid="admin-content">Admin Panel</div>
        </RequirePermission>
      </AuthProvider>
    );
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });

  it('RequirePermission hides children when user lacks the required permission', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('username', 'regular-user');
    localStorage.setItem('admin', 'false');
    localStorage.setItem('role', 'user');

    render(
      <AuthProvider>
        <RequirePermission permission="admin">
          <div data-testid="admin-content">Admin Panel</div>
        </RequirePermission>
      </AuthProvider>
    );
    expect(screen.queryByTestId('admin-content')).toBeNull();
  });

  it('redirects unauthenticated users to /login', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login</div>} />
            <Route path="/dashboard" element={<ProtectedRoute><div data-testid="dashboard">Dashboard</div></ProtectedRoute>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('dashboard')).toBeNull();
  });

  it('renders children when authenticated', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('username', 'alice');
    localStorage.setItem('admin', 'false');
    localStorage.setItem('role', 'user');

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div data-testid="login-page">Login</div>} />
            <Route path="/dashboard" element={<ProtectedRoute><div data-testid="dashboard">Dashboard</div></ProtectedRoute>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    expect(screen.queryByTestId('login-page')).toBeNull();
  });

  it('throws when useAuth is used outside AuthProvider', () => {
    expect(() => render(<BrokenComponent />)).toThrow('useAuth must be used within an AuthProvider');
  });

  it('provides isAuthenticated=true when token and userId exist in localStorage', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('userId', 'user-1');
    localStorage.setItem('username', 'testuser');
    localStorage.setItem('admin', 'false');
    localStorage.setItem('role', 'user');

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
    expect(screen.getByTestId('auth-user')).toHaveTextContent('testuser');
  });
});
