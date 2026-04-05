# Ma11y Operator Mapping — Low Variant Audit

Reference: Ma11y [ISSTA 2024] — https://dl.acm.org/doi/10.1145/3650212.3652113
GitHub: https://github.com/mahantaf/web-a11y-tool-analyzer

## Summary

- Ma11y defines **25 mutation operators** based on WCAG 2.1 failure techniques
- Our `apply-low.js` currently implements **10 mutation categories**
- **8 Ma11y operators** are directly covered by our existing patches
- **5 Ma11y operators** are partially covered or have agent-relevant overlap
- **12 Ma11y operators** are NOT covered — 4 are recommended for Pilot 3
- **3 of our operators** have no Ma11y equivalent — these are our **novel extensions**

## Part 1: Current apply-low.js Patches → Ma11y Mapping

| # | Our Patch (apply-low.js) | Ma11y Op | WCAG | Status |
|---|--------------------------|----------|------|--------|
| 1 | Replace semantic elements (nav/main/header/footer/article/section/aside) → `<div>` | — | 1.3.1 | **EXTENSION (E1)**: Ma11y only does headings (F2) and links (F42). We extend to all landmark elements. |
| 2 | Remove all `aria-*` and `role` attributes | F96 (partial) | 2.5.3+ | **PARTIAL**: F96 specifically corrupts `aria-label` with random strings on buttons. We do broader removal of ALL aria attrs on ALL elements. Our approach is more aggressive. |
| 3 | Remove all `<label>` elements | F68 | 4.1.2 | **MATCH**: F68 removes labels + placeholder from form inputs. We remove all labels globally. |
| 4 | Remove keyboard event handlers (onkeydown/onkeyup/onkeypress) | F54 (related) | 2.1.1 | **PARTIAL**: F54 replaces `onclick` with `onmousedown` (device-dependent). We remove keyboard handlers specifically. Different mechanism, same WCAG criterion. |
| 5 | Wrap interactive elements in closed Shadow DOM | — | — | **EXTENSION (E2)**: Novel operator. Hides elements from a11y tree via Shadow DOM encapsulation. No Ma11y equivalent. Directly tests agent's ability to discover hidden interactive elements. |
| 6 | Replace headings (h1-h6) → styled `<div>` | F2 | 1.3.1 | **MATCH**: F2 replaces `<h2>` → `<p>` with CSS styling. We do all heading levels (h1-h6) → `<div>`. |
| 7 | Remove `alt` text from images | F65 | 1.1.1 | **MATCH**: F65 removes alt, aria-label, and title from images. We remove alt only. |
| 8 | Remove `tabindex` attributes | F44 (related) | 2.4.3 | **PARTIAL**: F44 reverses tabindex order on list links. We remove tabindex entirely. Different degradation strategy for same criterion. |
| 9 | Break table semantics (thead/tbody/tfoot → div, th → td) | F91 | 1.3.1 | **MATCH**: F91 replaces `<th>` → `<td>`. We also flatten thead/tbody/tfoot → div. |
| 10 | Remove `lang` attribute from `<html>` | — | 3.1.1 | **EXTENSION (E3)**: No Ma11y operator for language identification. WCAG SC 3.1.1 (Level A). |

## Part 2: Ma11y Operators NOT in Our apply-low.js

### Recommended for Pilot 3 (agent-relevant, Level A)

| Ma11y Op | Code | WCAG | What It Does | Why Add It | Priority |
|----------|------|------|--------------|------------|----------|
| **F42** | RAS | 1.3.1, 2.1.1 | Replace `<a>` → `<span>` with onclick handler + CSS underline | Breaks link semantics in a11y tree — agent sees `<span>` not `<a>`, can't identify navigable links. High impact on agent navigation. | **P0** |
| **F77** | MDI | 4.1.1 | Inject duplicate IDs on adjacent elements | Breaks `aria-labelledby`/`aria-describedby` ID references. Agent may get wrong label text for form controls. | **P1** |
| **F55** | RFA | 2.1.1, 3.2.1 | Add `onfocus="this.blur()"` to links | Creates focus trap — agent's keyboard navigation gets stuck. Directly tests keyboard navigability pathway. | **P1** |
| **F89** | RAI | 2.4.4, 4.1.2 | Remove accessible name from image links (clear alt, remove aria-label) | Agent can't determine link purpose when link contains only an image with no text alternative. | **P2** |

### Lower Priority (visual/CSS-only, less agent-relevant for text-only agent)

| Ma11y Op | Code | WCAG | What It Does | Why Lower Priority |
|----------|------|------|--------------|-------------------|
| F3 | RID | 1.1.1 | Replace `<img>` with CSS background-image `<div>` | Visual change — text-only agent doesn't see CSS backgrounds anyway. Relevant for vision agent control. |
| F24 | CFC | 1.4.3 | Set `body { color: white }` (contrast failure) | Pure visual — text-only agent unaffected. Vision agent control only. |
| F73 | RAD | 1.4.1 | Remove link underline + cursor styling | Pure visual — text-only agent uses a11y tree, not visual cues. |
| F78 | ROA | 2.4.7 | Remove focus outline (`outline: none`) | Pure visual — text-only agent doesn't see focus indicators. |
| F80 | CIF | 1.4.4 | Set fixed font-size (8pt) on text inputs | Pure visual — text-only agent unaffected. |
| F94 | CPF | 1.4.4 | Set viewport-relative font-size (2vh) on paragraphs | Pure visual — text-only agent unaffected. |
| F4 | MTB | 2.2.2 | Add CSS blink animation to `<span>` | Pure visual — text-only agent unaffected. |
| F25 | CPT | 2.4.2 | Replace `<title>` with random string | Minor — agent rarely uses page title for task completion. |
| F30 | CIA | 1.1.1 | Replace img alt with random string | Similar to our alt removal but corrupts rather than removes. Could add as variant. |
| F32 | ASB | 1.3.2 | Insert spaces between characters in `<span>` text | Breaks screen reader pronunciation. Agent sees spaced text in a11y tree — may confuse NLP. |
| F9 | CCB | 3.2.5 (AAA) | Add `onblur` that opens new window | AAA conformance — beyond our A/AA scope. Also opens external URL (sandbox issue). |
| F22 | CCC | 3.2.5 (AAA) | Add `onclick` to `<span>` that opens new window | AAA conformance — beyond our A/AA scope. |
| F36 | CCI | 3.2.2 | Add `onchange` to form input that auto-submits | Interesting but risky — could break WebArena task flow. |
| F37 | CCS | 3.2.2 | Add `onclick` to radio button that opens new window | Opens external URL — sandbox issue in WebArena. |

## Part 3: Our Novel Extensions (not in Ma11y)

These operators are unique to our platform and should be explicitly labeled in the paper.

| ID | Our Patch | WCAG | Rationale |
|----|-----------|------|-----------|
| **E1** | Landmark element flattening (nav/main/header/footer/article/section/aside → div) | 1.3.1 | Ma11y only targets headings (F2) and links (F42). We extend semantic flattening to ALL HTML5 landmark elements. This is particularly relevant for AI agents because landmarks provide the primary navigation structure in the a11y tree. |
| **E2** | Closed Shadow DOM encapsulation of interactive elements | — | Completely novel. No WCAG failure technique exists for this because Shadow DOM is a newer web platform feature. Directly tests whether agents can discover elements hidden from the accessibility tree via Shadow DOM boundaries. |
| **E3** | `lang` attribute removal | 3.1.1 | Ma11y has no operator for SC 3.1.1. Minor impact on agents but included for completeness. |
| **E4** | Tabpanel ARIA relationship destruction (in medium-low variant) | 4.1.2 | Breaks `aria-controls`/`aria-selected` relationships on tab panels. Ma11y's F96 corrupts aria-label text but doesn't break ARIA relationship attributes. This specifically targets the "pseudo-compliance" pattern where ARIA attributes exist but reference wrong targets. |

## Part 4: Recommended Changes to apply-low.js for Pilot 3

### Add These Operators

1. **F42 (Link → Span)**: Replace `<a>` elements with `<span>` + onclick + CSS underline
   - High agent impact: breaks link discovery in a11y tree
   - Implementation: ~20 lines in apply-low.js

2. **F77 (Duplicate IDs)**: Set duplicate IDs on adjacent elements
   - Breaks aria-labelledby/describedby references
   - Implementation: ~15 lines in apply-low.js

3. **F55 (Focus Blur)**: Add `onfocus="this.blur()"` to focusable elements
   - Creates keyboard navigation trap
   - Implementation: ~10 lines in apply-low.js

### Modify Existing Operators

4. **Patch #7 (alt removal)**: Also remove `aria-label` and `title` from images (align with F65's full behavior)

5. **Patch #2 (ARIA removal)**: For a subset of elements, corrupt aria-label with random strings instead of removing (align with F96's approach) — this creates the "pseudo-compliance" signal where ARIA is present but wrong.

## Part 5: Literature Cross-References

| Paper | Relevance | Key Insight |
|-------|-----------|-------------|
| Ma11y [ISSTA 2024](https://dl.acm.org/doi/10.1145/3650212.3652113) | Mutation operators baseline | 25 WCAG failure operators; our low variant extends 8 + adds 4 novel |
| Aegis [2025](https://arxiv.org/abs/2508.19504) | Failure taxonomy comparison | 6 failure modes vs our 11-type taxonomy — see separate comparison |
| WAREX [2025](https://arxiv.org/abs/2510.03285) | Fault injection architecture | Proxy-based injection vs our page.evaluate approach |
| GUI-Robust [2025](https://arxiv.org/abs/2506.14477) | Anomaly classification | 7 anomaly types — compare with our variant levels |
| Chung et al. [2025](https://arxiv.org/abs/2512.04307) | Token threshold | 150K collapse threshold; our low variant avg 186K exceeds this |
| AgentOccam [2024](https://arxiv.org/abs/2410.13825) | Pivotal node filtering | Observation pruning strategy — relates to our semantic density metric |
| Prune4Web [2025](https://arxiv.org/abs/2511.21398) | DOM element reduction | Complementary to our token inflation analysis |
| Screen2AX [2025](https://arxiv.org/abs/2507.16704) | Screenshot → a11y tree | Motivates vision agent as control condition |
| Power et al. [CHI 2012](https://dl.acm.org/doi/10.1145/2207676.2207736) | WCAG coverage gap | 50.4% of blind user problems covered by WCAG |
| ADeLe [Nature 2026](https://arxiv.org/abs/2503.06378) | IRT framework | 18 cognitive dimensions; future work for formal experiment |
| nohacks.co [CHI 2026](https://nohacks.co/blog/how-ai-agents-see-your-website) | Keyboard constraint experiment | 78.33%→41.67% with keyboard constraints |
| Build the Web for Agents [2025](https://arxiv.org/abs/2506.10953) | Position paper | Agent-web interaction design principles |
| Gibson Affordance [2025](https://arxiv.org/abs/2501.09233) | Computational affordance theory | Theoretical framing for agent-environment interaction |
| EnviSAgE [2025](https://arxiv.org/abs/2511.09586) | Environment-centric survey | Comprehensive survey of agent environments |
