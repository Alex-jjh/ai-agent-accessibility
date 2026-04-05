import { describe, it, expect } from 'vitest';
import { FAILURE_DOMAINS, FAILURE_TYPES } from './types.js';

describe('FAILURE_DOMAINS', () => {
  it('has exactly 5 domains', () => {
    expect(FAILURE_DOMAINS).toHaveLength(5);
  });

  it('contains accessibility, model, environmental, task, unclassified', () => {
    expect(FAILURE_DOMAINS).toContain('accessibility');
    expect(FAILURE_DOMAINS).toContain('model');
    expect(FAILURE_DOMAINS).toContain('environmental');
    expect(FAILURE_DOMAINS).toContain('task');
    expect(FAILURE_DOMAINS).toContain('unclassified');
  });
});

describe('FAILURE_TYPES', () => {
  it('maps to exactly 12 total failure types', () => {
    const total = Object.values(FAILURE_TYPES).reduce(
      (sum, types) => sum + types.length,
      0,
    );
    expect(total).toBe(12);
  });

  it('accessibility domain has 5 types: F_ENF, F_WEA, F_KBT, F_PCT, F_SDI', () => {
    expect(FAILURE_TYPES.accessibility).toHaveLength(5);
    expect(FAILURE_TYPES.accessibility).toContain('F_ENF');
    expect(FAILURE_TYPES.accessibility).toContain('F_WEA');
    expect(FAILURE_TYPES.accessibility).toContain('F_KBT');
    expect(FAILURE_TYPES.accessibility).toContain('F_PCT');
    expect(FAILURE_TYPES.accessibility).toContain('F_SDI');
  });

  it('model domain has 3 types: F_HAL, F_COF, F_REA', () => {
    expect(FAILURE_TYPES.model).toHaveLength(3);
    expect(FAILURE_TYPES.model).toContain('F_HAL');
    expect(FAILURE_TYPES.model).toContain('F_COF');
    expect(FAILURE_TYPES.model).toContain('F_REA');
  });

  it('environmental domain has 2 types: F_ABB, F_NET', () => {
    expect(FAILURE_TYPES.environmental).toHaveLength(2);
    expect(FAILURE_TYPES.environmental).toContain('F_ABB');
    expect(FAILURE_TYPES.environmental).toContain('F_NET');
  });

  it('task domain has 1 type: F_AMB', () => {
    expect(FAILURE_TYPES.task).toHaveLength(1);
    expect(FAILURE_TYPES.task).toContain('F_AMB');
  });

  it('unclassified domain has 1 type: F_UNK', () => {
    expect(FAILURE_TYPES.unclassified).toHaveLength(1);
    expect(FAILURE_TYPES.unclassified).toContain('F_UNK');
  });
});
