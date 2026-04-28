#!/usr/bin/env tsx
/**
 * build-operators.ts — CLI wrapper around `src/variants/patches/build-lib.ts`.
 *
 * Writes the build artefact `apply-all-individual.js` to disk. All real
 * logic lives in `build-lib.ts` (under src/) so it can be imported by
 * tests within the TypeScript rootDir.
 *
 * Usage: npm run build:operators
 */
import { writeFileSync } from 'node:fs';
import {
  OPERATOR_ORDER,
  OUT_PATH_ABSOLUTE,
  buildArtefact,
} from '../src/variants/patches/build-lib.js';

const startedAt = Date.now();
const artefact = buildArtefact();
writeFileSync(OUT_PATH_ABSOLUTE, artefact, 'utf-8');
const lines = artefact.split('\n').length;
const bytes = Buffer.byteLength(artefact, 'utf-8');
console.log(
  `[build-operators] wrote ${OUT_PATH_ABSOLUTE} — ${OPERATOR_ORDER.length} operators, ` +
  `${lines} lines, ${bytes} bytes, ${Date.now() - startedAt} ms`,
);
