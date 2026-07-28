import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import Files from '../files/Files';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  open: vi.fn(),
  isAdmin: () => true,
  getAccessToken: () => 't',
  setTokens: vi.fn(),
  tryRefreshToken: () => Promise.resolve(false),
  clearTokens: vi.fn(),
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockQidoResponse = {
  data: [
    { '0020000D': { vr: 'UI', Value: ['1.2.3'] }, '00080050': { vr: 'SH', Value: ['ACC001'] } },
  ],
  total: 1,
};

const mockV2Results = {
  data: [
    { id: 'f1', 'Patient ID': 'P001', 'Patient\'s Name': 'Doe^John', 'Study ID': '1.2.3' },
  ],
  total: 1,
};

describe('Files QIDO-RS Search', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('token', 't');
    localStorage.setItem('userId', 'u1');
    localStorage.setItem('admin', 'true');
  });

  function renderWithAuth(url: string, ui: React.ReactElement) {
    return render(
      <AuthProvider>
        <MemoryRouter initialEntries={[url]}>
          {ui}
        </MemoryRouter>
      </AuthProvider>
    );
  }

  it('calls QIDO-RS endpoint when query param has Patient ID search', async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url.startsWith('v2/dicomweb/studies')) return Promise.resolve(mockQidoResponse);
      return Promise.resolve(mockV2Results);
    });

    const originalSearch = window.location.search;
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...window.location, search: '?{"query":"P001"}' },
    } as any);

    renderWithAuth('/?%7B%22query%22%3A%22P001%22%7D', <Files />);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalled();
    });

    const calls = mockRequest.mock.calls;
    const qidoCall = calls.find((c: any[]) => c[0]?.startsWith('v2/dicomweb/studies'));
    expect(qidoCall).toBeDefined();

    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...window.location, search: originalSearch },
    } as any);
  });

  it('falls back to v2 search when QIDO-RS returns empty results', async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url.startsWith('v2/dicomweb/studies')) return Promise.resolve({ data: [] });
      return Promise.resolve(mockV2Results);
    });

    const originalSearch = window.location.search;
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...window.location, search: '?{"query":"P001"}' },
    } as any);

    renderWithAuth('/?%7B%22query%22%3A%22P001%22%7D', <Files />);

    await waitFor(() => {
      const calls = mockRequest.mock.calls;
      const v2Call = calls.find((c: any[]) => c[0] === 'files');
      expect(v2Call).toBeDefined();
    });

    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...window.location, search: originalSearch },
    } as any);
  });

  it('falls back to v2 search when QIDO-RS request fails', async () => {
    mockRequest.mockImplementation((url: string) => {
      if (url.startsWith('v2/dicomweb/studies')) return Promise.reject(new Error('Network error'));
      return Promise.resolve(mockV2Results);
    });

    const originalSearch = window.location.search;
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...window.location, search: '?{"query":"P001"}' },
    } as any);

    renderWithAuth('/?%7B%22query%22%3A%22P001%22%7D', <Files />);

    await waitFor(() => {
      const calls = mockRequest.mock.calls;
      const v2Call = calls.find((c: any[]) => c[0] === 'files');
      expect(v2Call).toBeDefined();
    });

    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...window.location, search: originalSearch },
    } as any);
  });
});