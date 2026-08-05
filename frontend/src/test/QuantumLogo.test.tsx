import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import QuantumLogo from '../common/QuantumLogo';

describe('QuantumLogo', () => {
  it('renders without crashing', () => {
    render(<QuantumLogo />);
  });

  it('renders SVG element', () => {
    render(<QuantumLogo />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders text when showText is true (default)', () => {
    render(<QuantumLogo />);
    const svg = document.querySelector('svg');
    expect(svg?.textContent).toContain('Quantum');
    expect(screen.getByText('PACS')).toBeInTheDocument();
  });

  it('does not render text when showText is false', () => {
    render(<QuantumLogo showText={false} />);
    expect(screen.queryByText('PACS')).not.toBeInTheDocument();
    const svg = document.querySelector('svg');
    expect(svg?.textContent).not.toContain('Quantum');
  });

  it('accepts size prop', () => {
    render(<QuantumLogo size={60} />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});