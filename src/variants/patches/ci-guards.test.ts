/**
 * ci-guards.test.ts — CI-level invariants that protect the AMT v8 pipeline
 * from silent corruption of research data.
 *
 * Two invariants protected here:
 *
 *   (B2) BUILD ARTEFACT FRESHNESS — `apply-all-individual.js` on disk must
 *        byte-match the output of `buildArtefact()` over the current
 *        operator sources. If someone edits `operators/L3.js` but forgets
 *        `npm run build:operators`, CI fails here. Without this guard,
 *        production runs stale operator code for an entire Mode A batch
 *        (2,808 cases, ~$850 of Bedrock spend).
 *
 *   (B3) LEGACY FILE FREEZE — the five composite-v1 files that produced
 *        the existing N=1,040 experimental baseline must NEVER be edited.
 *        Editing them invalidates the parity test (apply-low.js ≡
 *        L1..L13 relies on apply-low.js being exactly what it was when
 *        N=1,040 ran). If someone "fixes" a bug in apply-low.js (e.g.
 *        the link→span cross-layer confound documented in
 *        docs/analysis/visual-equivalence-decision-memo.md), the old
 *        data and new data become incomparable, but the parity test
 *        still passes because both sides shifted together.
 *
 * These tests DO run in CI (they're .test.ts) and DO run locally via
 * `npm test`. They are cheap — no browser, no Playwright, pure fs + hash.
 */
import { describe, it, expect } from 'vitest';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildArtefact, OUT_PATH_ABSOLUTE } from './build-lib.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '../../..');
const INJECT_DIR = join(REPO_ROOT, 'src/variants/patches/inject');

// ─────────────────────────────────────────────────────────────────────
// B2 — Build artefact freshness
// ─────────────────────────────────────────────────────────────────────

describe('AMT build artefact freshness (B2, LOAD-BEARING)', () => {
  it('apply-all-individual.js on disk is byte-identical to buildArtefact() output', () => {
    const expected = buildArtefact();
    const actual = readFileSync(OUT_PATH_ABSOLUTE, 'utf-8');

    if (expected === actual) {
      // happy path
      return;
    }

    // Failure diagnostic — help the user diagnose what drifted.
    const expLines = expected.split('\n').length;
    const actLines = actual.split('\n').length;
    const msg = [
      `apply-all-individual.js is STALE.`,
      ``,
      `  disk:  ${actual.length} bytes, ${actLines} lines`,
      `  build: ${expected.length} bytes, ${expLines} lines`,
      ``,
      `Fix: run  npm run build:operators  and commit the regenerated file.`,
      `If you meant to commit an intentional change to an operator source,`,
      `run the build first so disk and build are in sync.`,
    ].join('\n');

    // Use toBe for a diff-friendly failure output on short mismatches;
    // if the diff is huge, the message above is the primary signal.
    expect(actual, msg).toBe(expected);
  });
});

// ─────────────────────────────────────────────────────────────────────
// B3 — Legacy composite file freeze
// ─────────────────────────────────────────────────────────────────────

/**
 * SHA-256 of each legacy file as of 2026-04-28, pre-Mode-A baseline freeze.
 * These files generated the existing N=1,040 experimental dataset
 * (Pilot 4, Llama 4 cross-model, SoM expansion, CUA expansion, ecological
 * validity audit) and the visual-equivalence replay study. Any change to
 * these files breaks cross-batch comparability.
 *
 * If a legacy file genuinely needs to change (rare — consider a new
 * operator or a new variant level instead), that change is a Type-2 patch
 * (see project-context.md "Handling variant bugs during task expansion"),
 * requires a batch boundary in the data manifest, and the new hash must be
 * updated HERE with a commit message explaining the rationale and the
 * cross-batch analysis strategy.
 */
const LEGACY_FROZEN_SHA256: Record<string, string> = {
  'apply-low.js':
    '03f67bf68c19fe04e5c64bafab0dafa260698214d83a955f9772de7a95f83afe',
  'apply-medium-low.js':
    '9fb91420953943574858115aec82592448c2fc6abae4bcf48a6c4c02c963a413',
  'apply-high.js':
    '4df9fffc530187cda204b720266c0216586efb5bae19752625f6afe920f081a6',
  'apply-pure-semantic-low.js':
    'c52b235b17d9357d3f818ed7f70dc35e7dd6f299b1ccff42fa5604e407cf53df',
  'apply-low-individual.js':
    '96eb1b5d875283bbedd990aef80a3610b0adfd62159737fbc2e3847c64896edf',
};

function sha256File(path: string): string {
  const bytes = readFileSync(path);
  return createHash('sha256').update(bytes).digest('hex');
}

describe('AMT legacy composite file freeze (B3, LOAD-BEARING)', () => {
  for (const [name, expectedHash] of Object.entries(LEGACY_FROZEN_SHA256)) {
    it(`${name} SHA-256 matches the 2026-04-28 frozen baseline`, () => {
      const actual = sha256File(join(INJECT_DIR, name));

      if (actual === expectedHash) return;

      const msg = [
        `Legacy composite file '${name}' has changed.`,
        ``,
        `  expected (frozen 2026-04-28): ${expectedHash}`,
        `  actual:                        ${actual}`,
        ``,
        `These files generated the N=1,040 baseline. Changing them`,
        `silently invalidates cross-batch comparability with all`,
        `previously collected Track A data.`,
        ``,
        `If this change is intentional:`,
        `  1. Document it in docs/platform-engineering-log.md as a`,
        `     Type-2 semantic change with an explicit batch boundary.`,
        `  2. Update LEGACY_FROZEN_SHA256 in this file with the new hash.`,
        `  3. Acknowledge the data-merge implications in the paper.`,
        ``,
        `If it was accidental: revert the change.`,
      ].join('\n');
      expect(actual, msg).toBe(expectedHash);
    });
  }
});
