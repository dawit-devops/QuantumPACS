import React from 'react';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import ServiceKeys from '../servicekeys/ServiceKeys';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockKeys = [
  {
    id: '1', name: 'RIS Integration', prefix: 'qpk_abcde', service_name: 'RIS-App',
    permissions: ['FILE_READ'], expires_at: '2027-07-28T00:00:00Z',
    last_used_at: '2026-07-27T12:00:00Z', enabled: true, created_at: '2026-07-01T00:00:00Z',
  },
  {
    id: '2', name: 'HL7 Connector', prefix: 'qpk_fghij', service_name: 'HL7-Bridge',
    permissions: ['PATIENT_READ', 'WORKLIST_WRITE'], expires_at: null,
    last_used_at: null, enabled: true, created_at: '2026-07-15T00:00:00Z',
  },
  {
    id: '3', name: 'Old Backup Script', prefix: 'qpk_klmno', service_name: 'Backup',
    permissions: ['FILE_READ'], expires_at: '2026-06-01T00:00:00Z',
    last_used_at: '2026-05-30T00:00:00Z', enabled: false, created_at: '2026-01-01T00:00:00Z',
  },
];

async function waitForTable() {
  await screen.findByText('RIS Integration');
}

describe('ServiceKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockImplementation(() => Promise.resolve({ data: mockKeys }));
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

  it('renders table with API keys from API', async () => {
    renderWithAuth(<ServiceKeys />);
    expect(await screen.findByText('RIS Integration')).toBeInTheDocument();
    expect(await screen.findByText('HL7 Connector')).toBeInTheDocument();
  });

  it('renders column headers', async () => {
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Service')).toBeInTheDocument();
    expect(screen.getByText('Prefix')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('renders Generate New Key button', async () => {
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    expect(screen.getByText('Generate Key')).toBeInTheDocument();
  });

  it('calls request with correct endpoint on mount', async () => {
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    expect(mockRequest).toHaveBeenCalledWith('api-keys');
  });

  it('generate modal opens with form fields', async () => {
    const user = userEvent.setup();
    renderWithAuth(<ServiceKeys />);
    await waitForTable();

    await user.click(screen.getByText('Generate Key'));
    const modal = screen.getByRole('dialog');
    expect(within(modal).getByLabelText('Name')).toBeInTheDocument();
    expect(within(modal).getByLabelText('Service Name')).toBeInTheDocument();
  });

  it('generate key sends API request and shows raw key', async () => {
    const user = userEvent.setup();
    renderWithAuth(<ServiceKeys />);
    await waitForTable();
    mockRequest.mockImplementation(() =>
      Promise.resolve({ data: { id: '4', raw_key: 'qpk_newly_generated_key_token' } })
    );

    await user.click(screen.getByText('Generate Key'));
    const modal = screen.getByRole('dialog');
    await user.type(within(modal).getByLabelText('Name'), 'New Key');
    await user.type(within(modal).getByLabelText('Service Name'), 'MyService');
    await user.click(within(modal).getByText('Generate'));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('api-keys', {
        data: { name: 'New Key', service_name: 'MyService' },
      });
    });

    expect(await screen.findByText('qpk_newly_generated_key_token')).toBeInTheDocument();
  });

  it('revoke key calls delete API and refreshes list', async () => {
    const user = userEvent.setup();
    renderWithAuth(<ServiceKeys />);
    await waitForTable();

    await user.click(screen.getAllByTitle('Revoke')[0]);
    const confirmBtn = screen.getByRole('button', { name: /yes|confirm|ok/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('api-keys/1', { data: undefined, method: 'DELETE' });
    });
  });
});
