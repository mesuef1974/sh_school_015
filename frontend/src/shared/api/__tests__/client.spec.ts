import { describe, it, expect } from 'vitest';
import { normalizeApiError } from '../client';
import { getErrorMessage } from '../useApiToast';

function axiosErr(payload: any, status = 400) {
  return { response: { status, data: payload } };
}

describe('normalizeApiError', () => {
  it('extracts unified envelope {error:{code,message,details}}', () => {
    const err = axiosErr({ error: { code: 'SOME_CODE', message: 'Oops', details: { a: 1 } } }, 422);
    const norm = normalizeApiError(err)!;
    expect(norm).toBeTruthy();
    expect(norm.status).toBe(422);
    expect(norm.code).toBe('SOME_CODE');
    expect(norm.message).toBe('Oops');
    expect(norm.details).toEqual({ a: 1 });
  });

  it('handles network error without response', () => {
    const err = { message: 'Network Error' } as any;
    const norm = normalizeApiError(err)!;
    expect(norm.code).toBe('NETWORK_ERROR');
    expect(norm.message).toContain('Network');
  });

  it('falls back to HTTP status/message when payload missing', () => {
    const err = { response: { status: 500, data: 'boom' }, message: 'Server exploded' } as any;
    const norm = normalizeApiError(err)!;
    expect(norm.status).toBe(500);
    expect(norm.message).toContain('Server');
    expect(norm.details).toBeDefined();
  });
});

describe('getErrorMessage', () => {
  it('prefers normalized message', () => {
    const err = axiosErr({ error: { code: 'X', message: 'حدث خطأ', details: null } }, 400);
    expect(getErrorMessage(err)).toBe('حدث خطأ');
  });

  it('falls back to error.message then fallback', () => {
    expect(getErrorMessage(new Error('E1'))).toBe('E1');
    expect(getErrorMessage({} as any, 'افتراضي')).toBe('افتراضي');
  });
});