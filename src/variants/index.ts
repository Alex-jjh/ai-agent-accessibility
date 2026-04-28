// Module 2: Variant Generator — WebArena DOM manipulation
export { applyVariant, applyVariantSpec } from './patches/index.js';
export { revertVariant } from './patches/revert.js';
export { validateVariant, VARIANT_SCORE_RANGES } from './validation/index.js';
export type { Scanner } from './validation/index.js';
export type {
  VariantLevel,
  DomChange,
  VariantDiff,
  VariantValidationResult,
} from './types.js';
export { VARIANT_LEVELS } from './types.js';
