import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ThumbnailStrip from '../detail/ThumbnailStrip';

vi.mock('../helpers', () => ({
  getAccessToken: () => 'test-token',
}));

const mockFiles = [
  { id: 1, name: 'image1.dcm' },
  { id: 2, name: 'image2.dcm' },
  { id: 3, name: 'image3.dcm' },
];

describe('ThumbnailStrip', () => {
  it('renders null when files is null', () => {
    const { container } = render(
      <ThumbnailStrip files={null as any} currentFileId="1" onSelect={vi.fn()} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders null when files has only one item', () => {
    const { container } = render(
      <ThumbnailStrip files={[{ id: 1, name: 'single.dcm' }]} currentFileId="1" onSelect={vi.fn()} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders a thumbnail button for each file', () => {
    render(
      <ThumbnailStrip files={mockFiles} currentFileId="1" onSelect={vi.fn()} />
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(3);
  });

  it('marks the current file as active', () => {
    render(
      <ThumbnailStrip files={mockFiles} currentFileId="2" onSelect={vi.fn()} />
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons[1].className).toContain('active');
    expect(buttons[0].className).not.toContain('active');
    expect(buttons[2].className).not.toContain('active');
  });

  it('calls onSelect with index when clicked', () => {
    const onSelect = vi.fn();
    render(
      <ThumbnailStrip files={mockFiles} currentFileId="1" onSelect={onSelect} />
    );
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[2]);
    expect(onSelect).toHaveBeenCalledWith(2);
  });
});
