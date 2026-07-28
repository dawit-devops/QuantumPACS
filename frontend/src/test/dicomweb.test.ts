import { describe, it, expect, vi, beforeEach } from 'vitest';
import { searchStudies, getSeries, getInstances, wadoRsUrl, Study, Series, Instance } from '../dicomweb/dicomweb';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function mockDicomJsonResponse(data: any) {
  return { ok: true, json: () => Promise.resolve(data) };
}

describe('dicomweb', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('access_token', 'test-token');
  });

  describe('searchStudies', () => {
    it('fetches studies from QIDO-RS endpoint', async () => {
      const raw = {
        '0020000D': { vr: 'UI', Value: ['1.2.3'] },
        '00100010': { vr: 'PN', Value: [{ Alphabetic: 'Test^Patient' }] },
        '00081030': { vr: 'LO', Value: ['Test Study'] },
        '00080061': { vr: 'CS', Value: ['CT'] },
        '00080020': { vr: 'DA', Value: ['20260701'] },
      };
      mockFetch.mockResolvedValue(mockDicomJsonResponse([raw]));

      const results = await searchStudies();
      expect(results).toHaveLength(1);
      expect(results[0].studyInstanceUid).toBe('1.2.3');
      expect(results[0].patientName).toBe('Test^Patient');
      expect(results[0].studyDescription).toBe('Test Study');
      expect(results[0].modalities).toBe('CT');
      expect(results[0].studyDate).toBe('20260701');
    });

    it('sends PatientID query param', async () => {
      mockFetch.mockResolvedValue(mockDicomJsonResponse([]));
      await searchStudies({ PatientID: 'P001' });
      const url = mockFetch.mock.calls[0][0];
      expect(url).toContain('PatientID=P001');
    });

    it('includes auth token header', async () => {
      mockFetch.mockResolvedValue(mockDicomJsonResponse([]));
      await searchStudies();
      const headers = mockFetch.mock.calls[0][1]?.headers;
      expect(headers['X-Auth-Pacs']).toBe('test-token');
    });

    it('returns empty array on empty response', async () => {
      mockFetch.mockResolvedValue(mockDicomJsonResponse(null));
      const results = await searchStudies();
      expect(results).toEqual([]);
    });
  });

  describe('getSeries', () => {
    it('fetches series for a study', async () => {
      const raw = {
        '0020000E': { vr: 'UI', Value: ['1.2.3.4'] },
        '00080060': { vr: 'CS', Value: ['MR'] },
        '0008103E': { vr: 'LO', Value: ['Brain'] },
      };
      mockFetch.mockResolvedValue(mockDicomJsonResponse([raw]));

      const results = await getSeries('study-uid');
      expect(results).toHaveLength(1);
      expect(results[0].seriesInstanceUid).toBe('1.2.3.4');
      expect(results[0].modality).toBe('MR');
      expect(results[0].seriesDescription).toBe('Brain');
    });
  });

  describe('getInstances', () => {
    it('fetches instances for a series', async () => {
      const raw = {
        '00080018': { vr: 'UI', Value: ['1.2.3.4.5'] },
        '00200013': { vr: 'IS', Value: ['1'] },
      };
      mockFetch.mockResolvedValue(mockDicomJsonResponse([raw]));

      const results = await getInstances('study-uid', 'series-uid');
      expect(results).toHaveLength(1);
      expect(results[0].sopInstanceUid).toBe('1.2.3.4.5');
      expect(results[0].instanceNumber).toBe('1');
    });
  });

  describe('wadoRsUrl', () => {
    it('builds wadors URL', () => {
      const url = wadoRsUrl('study-uuid', 'series-uuid', 'instance-uuid');
      expect(url).toContain('wadors:');
      expect(url).toContain('/dicomweb/studies/study-uuid/series/series-uuid/instances/instance-uuid');
    });
  });
});
