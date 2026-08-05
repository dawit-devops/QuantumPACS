import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFormInput, usePrevious } from '../hooks';

describe('useFormInput', () => {
  it('returns initial value', () => {
    const { result } = renderHook(() => useFormInput('hello'));
    expect(result.current.value).toBe('hello');
  });

  it('updates value on change event', () => {
    const { result } = renderHook(() => useFormInput(''));
    act(() => {
      result.current.onChange({ target: { value: 'new value' } });
    });
    expect(result.current.value).toBe('new value');
  });

  it('updates value on direct value without target', () => {
    const { result } = renderHook(() => useFormInput(''));
    act(() => {
      result.current.onChange('direct value');
    });
    expect(result.current.value).toBe('direct value');
  });
});

describe('usePrevious', () => {
  it('returns null on initial render', () => {
    const { result } = renderHook(() => usePrevious('test'));
    expect(result.current).toBeNull();
  });

  it('returns previous value after rerender', () => {
    const { result, rerender } = renderHook(
      ({ val }: { val: string }) => usePrevious(val),
      { initialProps: { val: 'first' } },
    );
    rerender({ val: 'second' });
    expect(result.current).toBe('first');
  });
});