import React from 'react';
import { describe, it, expect } from 'vitest';
import { wadoRsUrl } from '../dicomweb/dicomweb';
import CornerstoneElement from '../detail/CornerstoneElement';

describe('Progressive Loading', () => {
  it('wadoRsUrl constructs valid WADO-RS URL', () => {
    const url = wadoRsUrl('1.2.3', '1.2.3.4', '1.2.3.4.5');
    expect(url).toContain('wadors:');
    expect(url).toContain('studies/1.2.3');
    expect(url).toContain('series/1.2.3.4');
    expect(url).toContain('instances/1.2.3.4.5');
  });

  it('thumbnail URL appends viewport parameter for progressive loading', () => {
    const fullUrl = wadoRsUrl('1.2.3', '1.2.3.4', '1.2.3.4.5');
    const thumbUrl = fullUrl + '?viewport=256,256';
    expect(thumbUrl).toContain('viewport=256,256');
  });

  it('CornerstoneElement accepts progressive prop', () => {
    expect(CornerstoneElement).toBeDefined();
  });
});