# AMT Operators

24 independent accessibility manipulation operators, one per file.

**Normative spec**: `docs/amt-operator-spec.md`

## Conventions

- Filename = operator ID (`L1.js`, `H5a.js`, etc.).
- File body is a single IIFE `(() => { ... })()`.
- Body declares `const changes = []` as the first statement.
- Body returns `changes` as the last statement.
- Do NOT set `operatorId` on Change records — the build wrapper does that.
- Copy blocks verbatim from the composite files when possible (see the
  "Source block" column in the spec) to keep `git blame` honest about
  provenance.

## When editing

1. Edit the individual `{ID}.js` in this directory.
2. Run `npm run build:operators` — regenerates `../inject/apply-all-individual.js`.
3. Run `npm test -- operators` — validates contract, parity, idempotence.
4. Commit both the operator source AND the regenerated build artefact
   in the same commit.

Never hand-edit `../inject/apply-all-individual.js`. The build comment
at the top of that file warns against it; CI would overwrite.

## When adding a new operator

1. Pick a fresh ID that has never been used (see spec §6).
2. Add the file here.
3. Register the ID in `scripts/build-operators.ts` (the registry is the
   single source of truth for the application order).
4. Document it in `docs/amt-operator-spec.md` §7.
5. Run the full test battery before committing.
