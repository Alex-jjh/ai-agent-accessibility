# `docs/analysis/` — Deep-dive analysis reports

This directory holds 48 deep-dive analysis reports accumulated across the
project's 6 phases. They're frozen historical content — when a phase
moves to "active in paper", a per-stage main entry is created at
`docs/by-stage/phase{N}.md` and these deep-dives become its citations.

## Where to start

- **Looking up a specific phase?** Read `docs/by-stage/phase{N}.md` first.
  It links to the relevant deep-dives here.
- **Want a discoverability index of all 48 files?** See [`INDEX.md`](INDEX.md).
- **Frozen Mode A / C.2 reports** carry STATUS banners noting pre-2026-05-15
  numbers (e.g. "C.2 = 2,188" was a +4 typo; banners explain).

## Layout

This directory is **flat** by design (no per-phase subdirectories).
Reasoning: many trace reports cross-reference siblings; moving them
would break cross-refs and git blame. INDEX.md provides the
classification without rearranging files.
