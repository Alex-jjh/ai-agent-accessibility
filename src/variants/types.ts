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
}

/** Result of validating a variant against expected score ranges */
export interface VariantValidationResult {
  variantLevel: VariantLevel;
  compositeScore: import('../scanner/types.js').CompositeScoreResult;
  inExpectedRange: boolean;
  expectedRange: { min: number; max: number };
}

/** All variant levels as a constant array */
export const VARIANT_LEVELS: readonly VariantLevel[] = ['low', 'medium-low', 'base', 'high'] as const;
