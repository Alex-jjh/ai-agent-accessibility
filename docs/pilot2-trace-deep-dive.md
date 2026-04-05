# Pilot 2 Trace Deep-Dive Analysis

## Methodology

Examined raw trace JSON files for all 81 cases in run `485dc46c-d349-49dd-a17d-addfb1c80a47`.
Each trace contains step-by-step `observation` (a11y tree), `reasoning` (agent CoT), `action`,
and `result` fields. Compared identical tasks across low/base/high variants to isolate
variant-specific effects.

---

## Finding 1: send_msg_to_user Serialization Bug — Deeper Than Documented

### The Bug Mechanism (confirmed from traces)

The `cleanAction()` regex `^send_msg_to_user\("([\s\S]*)"\)$` requires the action string
to start with `send_msg_to_user("` and end with `")`. But the agent's raw output is
**truncated mid-string** before reaching the closing `")`.

**Task 24, base variant, rep 1 — actual action field from trace:**
```
send_msg_to_user("No reviewers mention price being unfair. The 2 existing reviews are both positive - Jay's review says 'Wonderful!' and Josef Bürger's review (in German)
```

The action is **cut off** — there is no closing `")`. The `cleanAction()` regex doesn't
match, so the raw string (with unescaped quotes and parentheses) is passed directly to
BrowserGym's Python `exec()`, which fails with `ValueError: Received an empty action`.

### NEW INSIGHT: This is NOT a parentheses/quotes parsing bug — it's a TRUNCATION bug

The existing findings doc says the issue is "nested quotes/parentheses in the message text."
But examining the actual traces reveals the real problem: **the LLM's response is being
truncated before the closing delimiter**. The agent's `reasoning` field shows the full
intended message:

```json
"reasoning": "... says the slippers are very good as described and expected.\")"
```

The reasoning contains the complete message with closing `")`, but the `action` field
is cut short. This suggests the truncation happens in the action extraction layer
(between the LLM response and the action field), not in `cleanAction()`.

### Evidence: Identical failure across base AND high

- `ecommerce_base_24_0_1`: action truncated at `(in German)` → failure
- `ecommerce_high_24_0_1`: action truncated at `(in German)` → failure  
- `ecommerce_base_24_0_3`: same truncation → failure
- `ecommerce_high_24_0_2`: same truncation → failure
- `ecommerce_high_24_0_3`: same truncation → failure

All 5 failures have the **exact same truncation point**. The message contains
`Josef Bürger's review (in German)` — the `(` in `(in German)` is likely being
misinterpreted as a function call boundary by the action parser upstream of
`cleanAction()`.

### The REAL fix needed

The action extraction code (likely in `executor.ts` or the BrowserGym bridge) is
splitting on the first unmatched `)` after `send_msg_to_user(`. When the message
contains `(in German)`, the parser sees the `)` after "German" as the function
call's closing paren, truncating everything after it. `cleanAction()` then receives
a malformed string that doesn't match its regex.

**Fix:** Use a proper parenthesis-depth counter or extract the message between the
FIRST `("` and the LAST `")` in the string, not the first `)`.

---

## Finding 2: Task 24 Inversion — Low Variant "Succeeds" Via Information Hiding

### What the low variant sees (and doesn't see)

**Low variant, step 1 observation** — the a11y tree is MISSING:
- `[255] banner ''` (no banner landmark)
- `[1391] main ''` (no main landmark)
- `[1501] tablist` / `[1502] tab 'Details'` / `[1556] tab 'Reviews (2)'` (no tab structure)
- `[1559] tabpanel 'Reviews (2)'` (no review panel)
- All review content (Jay's review, Josef Bürger's review)

Instead, the low variant shows the **Details tab content by default** (product description,
specifications table), and the Reviews tab appears only as a bare link `[1557] link 'Reviews (2)'`.

**Low variant, step 2** — after clicking the Reviews link, the a11y tree STILL doesn't
show review content. The degraded DOM has broken the tab panel's ARIA relationship, so
clicking the tab link doesn't reveal the review panel content in the a11y tree.

**Low variant, steps 3-4** — the agent scrolls and clicks `[1420] link '2 Reviews'` but
the review content never appears. The agent eventually gives up and sends:

```
send_msg_to_user("No reviews mention the price being unfair")
```

This is a SHORT message with no parentheses or quotes — so `cleanAction()` handles it
correctly, and the answer happens to be **correct** (the reviews indeed don't mention
unfair pricing).

### The inversion mechanism

| Variant | Sees reviews? | Message complexity | cleanAction bug? | Correct answer? |
|---------|--------------|-------------------|------------------|-----------------|
| low     | NO           | Simple, short      | No               | Yes (lucky)     |
| base    | YES          | Complex, has `()`  | YES — truncated  | Would be correct |
| high    | YES          | Complex, has `()`  | YES — truncated  | Would be correct |

The low variant "succeeds" because:
1. Degraded DOM hides review content → agent can't see reviews
2. Agent gives a simple "no reviews mention X" answer
3. Simple answer has no special characters → no serialization bug
4. Answer happens to be factually correct

Base and high variants "fail" because:
1. Full DOM shows review content → agent reads reviews
2. Agent gives a detailed answer quoting reviewer names and content
3. Detailed answer contains `(in German)` → triggers truncation bug
4. Truncated action → BrowserGym ValueError → failure

**This is a platform bug masquerading as an accessibility effect.**

---

## Finding 3: High Variant A11y Tree Differences — Subtle but Real

### Skip-link injection (confirmed)

**High variant, step 1:**
```
[1700] link 'Skip to main content'
[255] banner ''
```

**Base variant, step 1:**
```
[255] banner ''
```

The high variant injects `[1700] link 'Skip to main content'` as the FIRST element.
Node IDs for subsequent elements remain the same (255, 258, etc.) because BrowserGym
assigns IDs based on DOM order, and the skip-link gets a high ID (1700) since it's
injected after initial ID assignment.

### Form/banner semantic enrichment (NEW FINDING)

The high variant adds semantic roles that base doesn't have:

**High variant, step 2 (after navigation):**
```
[300] form ''          ← was [300] Section '' in base
[1431] form ''         ← was [1431] Section '' in base  
[1565] form ''         ← was [1565] Section '' in base
[1628] form ''         ← was [1628] Section '' in base
```

And in the reddit traces:
```
[26] banner ''         ← wraps the Home link (not in base)
[42] form ''           ← wraps the search box (was Section in base)
[153] form ''          ← wraps Subscribe buttons (was Section in base)
[150] banner ''        ← wraps article headers (not in base)
```

### Impact on agent behavior

In the reddit high variant, the agent's first action `click("42")` targets different
elements across variants:

- **Base:** `[42] Section '' → [51] searchbox 'Search query'` — this is the search section
- **High:** `[42] form '' → [51] searchbox 'Search query'` — same search section, but now a form

The agent clicks `[42]` in step 1 of both base and high reddit_29 traces. In base,
this targets the search Section. In high, it targets the search form. Both navigate
to the same place, so the skip-link ID shift is NOT causing element mis-targeting
in this case.

### Reddit high variant failure mechanism (task 29)

Comparing `reddit_base_29_0_1` (success) vs `reddit_high_29_0_1` (failure):

Both traces follow the same navigation path through steps 1-3 (forums list → page 2 → DIY forum).
The high variant's extra `banner` elements inside each article add ~20 tokens per article
(25 articles per page = ~500 extra tokens per page view). Over 8 steps of navigation,
this accumulates.

**Token comparison from CSV:**
- `reddit_base_29_0_1`: 166,599 tokens, 8 steps → SUCCESS
- `reddit_high_29_0_1`: 152,911 tokens, 8 steps → FAILURE
- `reddit_high_29_0_2`: 152,771 tokens, 8 steps → FAILURE
- `reddit_high_29_0_3`: 169,540 tokens, 8 steps → SUCCESS

The high variant failures use FEWER tokens than the base success. This rules out
token overflow as the cause. The failure is likely due to **stochastic agent behavior**
(temperature=0 doesn't eliminate all randomness in Claude) or subtle differences in
the a11y tree structure affecting element selection in later steps.

---

## Finding 4: Ecommerce Admin Low Variant — Token Explosion Confirmed

### Token comparison

| Case | Tokens | Steps | Outcome |
|------|--------|-------|---------|
| `ecommerce_admin_base_4_0_1` | 129,985 | 10 | SUCCESS |
| `ecommerce_admin_base_4_0_2` | 130,412 | 10 | FAILURE |
| `ecommerce_admin_low_4_0_1`  | **625,439** | 13 | FAILURE |
| `ecommerce_admin_low_4_0_2`  | **347,398** | 10 | FAILURE |
| `ecommerce_admin_low_4_0_3`  | **348,490** | 10 | FAILURE |
| `ecommerce_admin_high_4_0_1` | 69,053 | 6 | FAILURE |
| `ecommerce_admin_high_4_0_2` | 69,053 | 6 | SUCCESS |
| `ecommerce_admin_high_4_0_3` | 130,782 | 10 | SUCCESS |

The low variant uses **2.7-4.8x more tokens** than base for the same task.
Rep 1 hits 625K tokens in 13 steps — that's ~48K tokens per step on average.

### What the low variant's a11y tree looks like

Comparing step 1 observations for the admin dashboard:

**Low variant differences from base:**
- `[255] banner ''` → MISSING (no banner landmark)
- `[1391] main ''` → MISSING (no main landmark)
- Navigation menu items: `menuitem` → `link` (semantic downgrade)
- `[300] Section ''` with labeled search → `[300] Section ''` with bare `textbox`
- Tab labels lose their `tab` role → become bare `link` elements
- `button 'Search', disabled=True` loses its `[310]` ID → becomes anonymous `button`

However, the step 1 observation for the admin dashboard is actually similar in size
between low and base. The token explosion happens in **later steps** when the agent
navigates to report pages with large data tables. The degraded DOM in the low variant
exposes more raw table data without proper ARIA table structure, causing the a11y tree
serializer to emit more verbose representations.

### Agent behavior difference

The low variant agent gets stuck in a loop clicking REPORTS repeatedly (steps 1-3 all
click `[339]` REPORTS) because the degraded DOM doesn't expose the submenu structure.
In the base variant, the REPORTS menu expands to show sub-items. In the low variant,
the menu structure is flattened, so the agent can't find the "Ordered Products" report
sub-link.

---

## Finding 5: Empty/Short Observation Patterns

### Task 24 low variant — review content invisible

Steps 2-4 of `ecommerce_low_24` show the agent clicking the Reviews tab and link,
but the a11y tree never shows review content. The observation is not "empty" — it's
the full page tree, but with the review panel content MISSING. The degraded DOM broke
the `tabpanel` → content relationship, so the reviews exist in the DOM but aren't
exposed in the a11y tree.

### Task 50 — context overflow pattern

All task 50 cases fail across all variants. Token counts:
- Base: 161K-257K tokens over 11-16 steps
- Low: 128K-247K tokens over 10-17 steps  
- High: 234K-235K tokens over 16 steps

Task 50 involves navigating the ecommerce site's order history, which generates
very large a11y trees. The agent exhausts its 30-step budget without completing
the task. This is a task difficulty issue, not a variant effect.

### Reddit low task 67 rep 1 — massive token spike

`reddit_low_67_0_1` uses **556,205 tokens** in 9 steps (61K/step average) and fails.
Compare with `reddit_base_67_0_1` at 41,739 tokens in 4 steps (10K/step). The low
variant's degraded DOM on reddit causes a 13x token inflation for this task, likely
because the forum post content is exposed without proper semantic containment.

---

## Finding 6: High Variant form/banner Injection — A New Confound

### What apply-high.js actually does to the a11y tree

Beyond the documented skip-link, the high variant's patches change element roles:

1. **`Section` → `form`**: Search boxes, subscribe buttons, newsletter signup, and
   review submission sections all get wrapped in `<form>` elements. This changes
   their a11y tree representation from `Section ''` to `form ''`.

2. **Article headers get `banner` role**: In reddit, each article's header section
   gets a `banner` landmark, adding `[NNN] banner ''` wrapper nodes.

3. **These changes are INVISIBLE to the agent's reasoning** — the agent never
   mentions or reacts to the form/banner changes. They add tokens but don't
   change the agent's navigation strategy.

### Quantified impact

Per reddit forum page (25 articles):
- Base: ~25 `Section` wrappers for subscribe buttons
- High: ~25 `form` wrappers + ~25 `banner` wrappers = 50 extra wrapper nodes

Each wrapper node adds ~15 characters to the a11y tree text. Over 25 articles,
that's ~750 extra characters per page. Over 8 steps of navigation, ~6000 extra
characters — roughly 1500 extra tokens. This is modest but measurable.

---

## Summary of NEW Insights (beyond pilot2-findings.md)

1. **send_msg_to_user bug is a TRUNCATION issue, not a parsing issue.** The action
   string is being cut at the first `)` inside the message text, before `cleanAction()`
   ever sees it. The fix needs to be in the action extraction layer, not just in
   `cleanAction()`.

2. **Task 24 inversion is fully explained by the truncation bug + information hiding.**
   Low variant can't see reviews → gives simple answer → no truncation. Base/high see
   reviews → give detailed answer with `(in German)` → truncation → failure.

3. **High variant injects form/banner roles, not just skip-links.** This is a previously
   undocumented effect of apply-high.js that adds ~1500 tokens per multi-page navigation
   task on reddit.

4. **Reddit high variant failures are NOT caused by token overflow or element mis-targeting.**
   The token counts are actually LOWER than successful base runs. The failures appear to
   be stochastic — 1/3 reps succeed even in the high variant.

5. **Ecommerce admin low variant fails because menu structure is flattened.** The agent
   can't find report sub-menu items because the degraded DOM converts the hierarchical
   menu into flat links, causing the agent to click the same top-level REPORTS link
   repeatedly.

6. **The low variant hides content, not just structure.** On task 24, the review panel
   content is completely invisible in the a11y tree because the tabpanel ARIA relationship
   is broken. This is a stronger effect than just "more verbose DOM."

---

## Recommendations for Pilot 3

1. **Fix action extraction, not just cleanAction()** — use balanced-paren matching
2. **Audit apply-high.js form/banner injection** — ensure it doesn't add unnecessary
   wrapper elements that inflate tokens without improving accessibility
3. **Add task 24 to the "investigate" list** — it's a pure platform bug, not an
   accessibility signal
4. **Track per-step token counts** — the CSV only has totals; per-step data would
   reveal exactly which pages cause token explosion
5. **Consider the "information hiding" effect as a real accessibility mechanism** —
   degraded DOM doesn't just add noise, it actively hides content that the agent
   needs to complete tasks
