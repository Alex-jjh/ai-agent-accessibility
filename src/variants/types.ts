// Module 2: Variant Generator — Type definitions for DOM variant manipulation

/** Accessibility variant levels applied to WebArena apps */
export type VariantLevel = 'low' | 'medium-low' | 'base' | 'high' | 'pure-semantic-low';

/** A single DOM change recorded during variant manipulation */
export interface DomChange {
  selector: string;
  changeType: 'replace' | 'remove-attr' | 'add-attr' | 'remove-element' | 'add-element' | 'remove-handler';
  original: string;
  modified: string;
}

/** Full diff produced by applying a variant to a page */
export interface VariantDiff {
  variantLevel: VariantLevel;
  appName: string;
  changes: DomChange[];
  domHashBefore: string; // SHA-256 of serialized DOM
  domHashAfter: string;
  /** AMT individual-mode only: the operator IDs requested for this run.
   *  Absent for composite-mode runs (legacy N=1,040 baseline data).
   *  For Plan D re-injection, the same IDs are re-injected on every
   *  HTML response via browsergym_bridge.py's `_deferred_script`. */
  operatorIds?: string[];
}

/** Result of validating a variant against expected score ranges */
export interface VariantValidationResult {
  variantLevel: VariantLevel;
  compositeScore: import('../scanner/types.js').CompositeScoreResult;
  inExpectedRange: boolean;
  expectedRange: { min: number; max: number };
}

/** All variant levels as a constant array */
export const VARIANT_LEVELS: readonly VariantLevel[] = ['low', 'medium-low', 'base', 'high', 'pure-semantic-low'] as const;

/**
 * Variant specification for the DOM patch engine.
 *
 * Two shapes, discriminated by `kind`:
 *
 *  - 'composite' — the five legacy variant levels (apply-low/medium-low/
 *    high/pure-semantic-low/base). These produce the N=1,040 baseline
 *    and stay unchanged for cross-batch comparability.
 *
 *  - 'individual' — AMT v8 per-operator injection. `operatorIds` is a
 *    subset of the 26 operator IDs declared in docs/amt-operator-spec.md
 *    §7 (e.g. ['L3'] for a single-operator Mode A case, or ['L3','H2']
 *    for a compositional study case). Operators always apply in the
 *    canonical H → ML → L source order regardless of array order.
 *
 * See docs/amt-operator-spec.md §8 for the runtime protocol.
 */
export type VariantSpec =
  | { kind: 'composite'; level: VariantLevel }
  | { kind: 'individual'; operatorIds: string[] };
