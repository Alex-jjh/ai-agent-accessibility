import { describe, it, expect } from 'vitest';
import { isValidMetricValue } from './types.js';

describe('isValidMetricValue', () => {
  it('returns true for 0.0', () => {
    expect(isValidMetricValue(0.0)).toBe(true);
  });

  it('returns true for 0.5', () => {
    expect(isValidMetricValue(0.5)).toBe(true);
  });

  it('returns true for 1.0', () => {
    expect(isValidMetricValue(1.0)).toBe(true);
  });

  it('returns false for -0.1', () => {
    expect(isValidMetricValue(-0.1)).toBe(false);
  });

  it('returns false for 1.1', () => {
    expect(isValidMetricValue(1.1)).toBe(false);
  });

  it('returns false for NaN', () => {
    expect(isValidMetricValue(NaN)).toBe(false);
  });

  it('returns false for Infinity', () => {
    expect(isValidMetricValue(Infinity)).toBe(false);
  });

  it('returns false for -Infinity', () => {
    expect(isValidMetricValue(-Infinity)).toBe(false);
  });

  it('returns false for non-number values cast to number', () => {
    expect(isValidMetricValue('0.5' as unknown as number)).toBe(false);
    expect(isValidMetricValue(null as unknown as number)).toBe(false);
    expect(isValidMetricValue(undefined as unknown as number)).toBe(false);
  });
});
