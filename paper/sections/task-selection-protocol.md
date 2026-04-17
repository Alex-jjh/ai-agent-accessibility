# §3.X Task Selection Protocol

## Flowchart (Mermaid)

```mermaid
graph TD
    A["WebArena v1.0 Task Pool<br/>(Zhou et al., 2024)<br/>812 tasks, 6 sites"] --> B{"Site deployed?"}
    B -->|No| X1["Excluded: map (128), wikipedia (16)<br/>= 144 tasks removed"]
    B -->|Yes| C["668 tasks<br/>4 sites: shopping, admin, reddit, gitlab"]
    C --> D{"eval_type =<br/>string_match?"}
    D -->|No| X2["Excluded: program_html (187),<br/>url_match (89), llm_eval (64)<br/>= 340 tasks removed"]
    D -->|Yes| E["328 tasks<br/>string_match only"]
    E --> F{"Information<br/>retrieval only?"}
    F -->|No| X3["Excluded: state mutation (42),<br/>file upload (8), cross-app (12)<br/>= 62 tasks removed"]
    F -->|Yes| G["266 tasks<br/>read-only, repeatable"]
    G --> H{"Ground truth<br/>stable?"}
    H -->|No| X4["Excluded: time-dependent (15),<br/>stale answers (9)<br/>= 24 tasks removed"]
    H -->|Yes| I["242 candidate tasks"]
    I --> J["Stratified sampling:<br/>≥2 tasks per app,<br/>≥1 per nav depth,<br/>unique templates preferred"]
    J --> K["13 selected + 3 backups<br/>(349, 188, 77)"]
    K --> L{"Smoke test<br/>all 4 variants?"}
    L -->|Fail: task 124| X5["Replaced with backup 188<br/>(stale ground truth at base)"]
    L -->|Pass| M["13 final tasks<br/>4 apps, 11 templates,<br/>3 nav depths"]
```

## Prose (paper-ready, ~1 page)

### 3.X Task Selection

We selected 13 tasks from WebArena v1.0's 812-task pool [Zhou et al., 2024]
through a systematic six-stage filtering protocol designed to maximize
diversity while ensuring experimental validity (Figure X). Complete task
ID lists at each filtering stage are provided in the supplementary materials.

**Stage 1: Site availability.** We excluded tasks targeting map (128 tasks)
and wikipedia (16 tasks), which were not deployed in our WebArena instance,
retaining 668 tasks across four applications: Magento storefront (shopping),
Magento admin panel (shopping_admin), Postmill forum (reddit), and GitLab.
We used WebArena Docker images pinned to commit `ac07c86` (2024-01-15),
with database snapshots frozen at deployment time to prevent ground truth drift.

**Stage 2: Evaluation reliability.** We retained only tasks with
`string_match` evaluation (exact substring matching), excluding
`program_html` (187), `url_match` (89), and `llm_eval` (64) types.
This eliminates dependency on external LLM judges and ensures deterministic,
reproducible evaluation. 328 tasks remained.

**Stage 3: Repeatability.** We excluded tasks requiring state mutation
(e.g., creating posts, submitting forms; 42 tasks), file uploads (8),
or cross-application navigation (12), as these introduce non-deterministic
server-side state that confounds repeated measurements. 266 tasks remained.

**Stage 4: Ground truth stability.** We excluded tasks with time-dependent
answers (e.g., "most recent notification"; 15 tasks) or answers that did
not match the current database snapshot (9 tasks), verified through manual
inspection against the frozen Docker images. 242 candidate tasks remained.

**Stage 5: Stratified sampling.** From the 242 candidates, we selected
13 tasks plus 3 backup candidates (tasks 349, 188, 77) to maximize
coverage across three dimensions:

- **Application diversity**: 4 shopping_admin, 4 shopping, 2 reddit,
  3 gitlab (all four deployed applications represented)
- **Navigation depth**: 5 shallow (1–2 steps), 5 medium (3 steps),
  3 deep (4–5 steps)
- **Template independence**: 11 unique intent templates across 13 tasks
  (tasks 23, 24, and 26 share template 222, exercising the same product
  review page structure with different search terms; all other 10 tasks
  use distinct templates)
- **Page type diversity**: 11 distinct page types including product review
  tabs, search results, admin data grids, forum post lists, comment trees,
  repository contributor pages, and user account pages

**Stage 6: Smoke validation.** Each selected task was tested at all four
accessibility variants with a single repetition before full experiment
execution. We verified three criteria: (a) variant patches applied correctly
to the task's page type (DOM changes count > 0 for non-base variants),
(b) task-critical information — defined as the DOM element(s) containing
the ground-truth answer string — remained present in the accessibility tree
at each variant level (verified via manual trace inspection), and
(c) no platform errors (bridge crashes, timeout, evaluation failures)
occurred. Task 124 (price range query) failed criterion (b) at the base
variant: the expected answer did not match the current product catalog,
indicating stale ground truth. It was replaced with backup task 188
(cancelled order cost). All 13 final tasks passed smoke validation.

Table X summarizes the final task set with navigation depth and page type
annotations.

| ID | App | Nav Depth | Page Type | Template |
|----|-----|-----------|-----------|----------|
| 4 | admin | medium | Report table | 279 |
| 23 | shopping | shallow | Product reviews | 222 |
| 24 | shopping | shallow | Product reviews | 222 |
| 26 | shopping | shallow | Product reviews | 222 |
| 29 | reddit | medium | Comment tree | 33 |
| 41 | admin | medium | Dashboard widget | 285 |
| 67 | reddit | shallow | Post list | 17 |
| 94 | admin | deep | Invoice detail | 274 |
| 132 | gitlab | medium | Contributors table | 322 |
| 188 | shopping | shallow | Order history | 159 |
| 198 | admin | deep | Order filter grid | 366 |
| 293 | gitlab | medium | Clone panel | 329 |
| 308 | gitlab | deep | Contributors chart | 323 |
