import React from 'react';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../auth/AuthContext';
import Worklist from '../worklist/Worklist';

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock('../helpers', () => ({
  request: mockRequest,
  isAdmin: () => true,
}));

vi.mock('../hooks', () => ({
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockEntries = [
  {
    id: '1', patient_id: 'P001', patient_name: 'John Doe',
    patient_birth_date: '1980-05-15', patient_sex: 'M',
    accession_number: 'ACC-001', requested_procedure_desc: 'CT Chest',
    modality: 'CT', scheduled_date: '2026-07-28', scheduled_time: '09:00',
    status: 'scheduled', station_ae_title: 'CT-SCANNER-1',
  },
  {
    id: '2', patient_id: 'P002', patient_name: 'Jane Smith',
    patient_birth_date: '1990-11-20', patient_sex: 'F',
    accession_number: 'ACC-002', requested_procedure_desc: 'MRI Brain',
    modality: 'MR', scheduled_date: '2026-07-28', scheduled_time: '10:30',
    status: 'scheduled', station_ae_title: 'MR-SCANNER-2',
  },
  {
    id: '3', patient_id: 'P003', patient_name: 'Bob Wilson',
    patient_birth_date: '1975-03-08', patient_sex: 'M',
    accession_number: 'ACC-003', requested_procedure_desc: 'XR Chest',
    modality: 'XR', scheduled_date: '2026-07-27', scheduled_time: '14:00',
    status: 'performed', station_ae_title: 'XR-SCANNER-1',
  },
];

async function waitForTable() {
  await screen.findByText('John Doe');
}

describe('Worklist', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockImplementation(() => Promise.resolve({ data: mockEntries }));
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

  it('renders table with worklist entries from API', async () => {
    renderWithAuth(<Worklist />);
    expect(await screen.findByText('John Doe')).toBeInTheDocument();
    expect(await screen.findByText('Jane Smith')).toBeInTheDocument();
    expect(await screen.findByText('Bob Wilson')).toBeInTheDocument();
  });

  it('renders column headers', async () => {
    renderWithAuth(<Worklist />);
    await waitForTable();
    expect(screen.getByText('Patient Name')).toBeInTheDocument();
    expect(screen.getByText('Patient ID')).toBeInTheDocument();
    expect(screen.getByText('Accession #')).toBeInTheDocument();
    expect(screen.getByText('Modality')).toBeInTheDocument();
    expect(screen.getByText('Scheduled Date')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('renders Create Worklist Entry button', async () => {
    renderWithAuth(<Worklist />);
    await waitForTable();
    expect(screen.getByText('Create Entry')).toBeInTheDocument();
  });

  it('calls request with correct endpoint on mount', async () => {
    renderWithAuth(<Worklist />);
    await waitForTable();
    expect(mockRequest).toHaveBeenCalledWith('worklist', expect.any(Object));
  });

  it('create modal opens with form fields', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();

    await user.click(screen.getByText('Create Entry'));
    const modal = screen.getByRole('dialog');
    expect(within(modal).getByText('Create Worklist Entry')).toBeInTheDocument();
    expect(within(modal).getByLabelText('Patient ID')).toBeInTheDocument();
    expect(within(modal).getByLabelText('Patient Name')).toBeInTheDocument();
  });

  it('create entry sends correct API request', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();
    mockRequest.mockImplementation(() => Promise.resolve({ data: { id: '4' } }));

    await user.click(screen.getByText('Create Entry'));
    const modal = screen.getByRole('dialog');
    await user.type(within(modal).getByLabelText('Patient ID'), 'P004');
    await user.type(within(modal).getByLabelText('Patient Name'), 'Test Patient');
    await user.type(within(modal).getByLabelText('Accession #'), 'ACC-004');
    await user.type(within(modal).getByLabelText('Modality'), 'CT');
    await user.click(within(modal).getByText('OK'));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('worklist', {
        data: {
          patient_id: 'P004', patient_name: 'Test Patient',
          accession_number: 'ACC-004', modality: 'CT',
        },
      });
    });
  });

  it('edit modal opens with pre-filled values', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();

    await user.click(screen.getAllByTitle('Edit')[0]);
    const modal = screen.getByRole('dialog');
    expect(within(modal).getByDisplayValue('John Doe')).toBeInTheDocument();
    expect(within(modal).getByDisplayValue('P001')).toBeInTheDocument();
  });

  it('cancel entry calls delete API', async () => {
    const user = userEvent.setup();
    renderWithAuth(<Worklist />);
    await waitForTable();

    await user.click(screen.getAllByTitle('Cancel')[0]);
    const confirmBtn = screen.getByRole('button', { name: /yes|confirm|ok/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith('worklist/1', { data: undefined, method: 'DELETE' });
    });
  });
});
