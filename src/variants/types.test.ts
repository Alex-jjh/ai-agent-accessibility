import { describe, it, expect } from 'vitest';
import { VARIANT_LEVELS } from './types.js';

describe('VARIANT_LEVELS', () => {
  it('contains exactly 4 levels', () => {
    expect(VARIANT_LEVELS).toHaveLength(4);
  });

  it('contains low', () => {
    expect(VARIANT_LEVELS).toContain('low');
  });

  it('contains medium-low', () => {
    expect(VARIANT_LEVELS).toContain('medium-low');
  });

  it('contains base', () => {
    expect(VARIANT_LEVELS).toContain('base');
  });

  it('contains high', () => {
    expect(VARIANT_LEVELS).toContain('high');
  });
});
