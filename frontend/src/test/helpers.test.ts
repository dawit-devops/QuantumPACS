import { describe, it, expect, beforeEach } from 'vitest';
import { isAdmin, parseParams, encodeQuery } from '../helpers';

describe('isAdmin', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns true when admin is "true" in localStorage', () => {
    localStorage.setItem('admin', 'true');
    expect(isAdmin()).toBe(true);
  });

  it('returns false when admin is not in localStorage', () => {
    expect(isAdmin()).toBe(false);
  });

  it('returns false when admin is "false" in localStorage', () => {
    localStorage.setItem('admin', 'false');
    expect(isAdmin()).toBe(false);
  });
});

describe('parseParams', () => {
  it('parses URL search string into object', () => {
    const params = parseParams('?key1=value1&key2=value2');
    expect(params).toEqual({ key1: 'value1', key2: 'value2' });
  });

  it('returns empty object for empty search string', () => {
    const params = parseParams('');
    expect(params).toEqual({});
  });

  it('handles single parameter', () => {
    const params = parseParams('?foo=bar');
    expect(params).toEqual({ foo: 'bar' });
  });
});

describe('encodeQuery', () => {
  it('encodes object to URL query string', () => {
    const query = encodeQuery({ key1: 'value1', key2: 'value2' });
    expect(query).toBe('key1=value1&key2=value2');
  });

  it('handles single key', () => {
    const query = encodeQuery({ foo: 'bar' });
    expect(query).toBe('foo=bar');
  });

  it('encodes special characters', () => {
    const query = encodeQuery({ q: 'hello world' });
    expect(query).toBe('q=hello%20world');
  });
});