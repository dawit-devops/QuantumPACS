import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('PWA scaffold', () => {
  it('vite config includes VitePWA plugin', () => {
    const config = readFileSync(resolve(__dirname, '../../vite.config.js'), 'utf-8');
    expect(config).toContain("VitePWA");
    expect(config).toContain("'QuantumPACS'");
    expect(config).toContain("'standalone'");
    expect(config).toContain("'pwa-192x192.png'");
  });
});