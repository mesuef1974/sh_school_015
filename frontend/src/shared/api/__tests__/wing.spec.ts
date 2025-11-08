import { describe, it, expect, vi, afterEach } from 'vitest';
import { api, getWingMissing, getWingEntered } from '../client';

// Helper to mock api.get responses
function mockGetOnce(payload: any) {
  return vi.spyOn(api, 'get').mockResolvedValueOnce({ data: payload } as any);
}

describe('Wing endpoints normalization', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getWingMissing', () => {
    it('normalizes plain array to {items:[]}', async () => {
      mockGetOnce([{ class_id: 1, period_number: 1, subject_id: 2, teacher_id: 3 }]);
      const res = await getWingMissing({ date: '2024-01-01' });
      expect(Array.isArray(res.items)).toBe(true);
      expect(res.items.length).toBe(1);
      expect(res.date).toBeTypeOf('string');
    });

    it('reads items from {items:[]}', async () => {
      mockGetOnce({ date: '2024-01-02', items: [] });
      const res = await getWingMissing({});
      expect(Array.isArray(res.items)).toBe(true);
      expect(res.date).toBe('2024-01-02');
    });

    it('reads results from paginated shape', async () => {
      mockGetOnce({ count: 0, next: null, previous: null, results: [] });
      const res = await getWingMissing({});
      expect(Array.isArray(res.items)).toBe(true);
      expect(res.items.length).toBe(0);
    });
  });

  describe('getWingEntered', () => {
    it('normalizes plain array to {items:[]}', async () => {
      mockGetOnce([{ class_id: 1, period_number: 1, subject_id: 2, teacher_id: 3 }]);
      const res = await getWingEntered({ date: '2024-01-01' });
      expect(Array.isArray(res.items)).toBe(true);
      expect(res.items.length).toBe(1);
      expect(res.date).toBeTypeOf('string');
    });

    it('reads items from {items:[]}', async () => {
      mockGetOnce({ date: '2024-01-02', items: [] });
      const res = await getWingEntered({});
      expect(Array.isArray(res.items)).toBe(true);
      expect(res.date).toBe('2024-01-02');
    });

    it('reads results from paginated shape', async () => {
      mockGetOnce({ count: 0, next: null, previous: null, results: [] });
      const res = await getWingEntered({});
      expect(Array.isArray(res.items)).toBe(true);
      expect(res.items.length).toBe(0);
    });
  });
});
