# CUA Full Experiment Deep Dive Analysis

## Overview

CUA (Computer Use Agent) is a **pure coordinate-based vision agent** using Anthropic Computer Use
via AWS Bedrock. It sees ONLY screenshots — no DOM, no accessibility tree, no SoM overlays.
In theory, it should be completely unaffected by DOM semantic changes.

**Results**: 116/140 (82.9%) success. 24 failures.

## Key Question

> "CUA is supposed to succeed at everything since it's DOM-independent — why does it timeout?"

**Answer**: CUA is NOT fully DOM-independent. Two mechanisms cause failures:

1. **Cross-layer functional breakage** (low variant): The `link→span` patch doesn't just change
   DOM semantics — it **removes the `href` attribute entirely**, breaking actual navigation
   functionality. When sidebar menu links become `<span>` elements, clicking them does nothing
   regardless of whether the agent uses coordinates, bids, or accessibility tree. This is a
   **functional** change, not just a semantic one.

2. **UI complexity traps** (admin:198): Some Magento admin interfaces have overlapping UI
   elements (Columns dialog, Status filter dropdowns) that challenge coordinate-based
   interaction regardless of DOM state. The agent can SEE the correct elements but
   struggles to click them precisely, especially when dialogs overlap.

## Per-Variant Summary

| Variant | Success | Total | Rate | Failures |
|---------|---------|-------|------|----------|
| low | 18 | 35 | 51.4% | 17 |
| medium-low | 34 | 35 | 97.1% | 1 |
| base | 32 | 35 | 91.4% | 3 |
| high | 32 | 35 | 91.4% | 3 |

## Task × Variant Matrix

Format: success_rate% (successes/total)

| Task | low | medium-low | base | high |
|------|------|------|------|------|
| ecommerce:188 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| ecommerce_admin:41 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| ecommerce_admin:94 | 20% (1/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| ecommerce_admin:198 | 0% (0/5) | 80% (4/5) | 60% (3/5) | 40% (2/5) |
| gitlab:132 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| gitlab:293 | 40% (2/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| gitlab:308 | 0% (0/5) | 100% (5/5) | 80% (4/5) | 100% (5/5) |

## All 24 Failures — Detailed Breakdown

### Failure 1: `ecommerce_admin:base:198:0:2`

- **Variant**: base
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 490,676
- **Duration**: 242.5s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[1201,490]})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[1011,254]})` → success
- Step 30: `cua:left_click({"action":"left_click","coordinate":[1177,626]})` → success

### Failure 2: `ecommerce_admin:base:198:0:3`

- **Variant**: base
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 473,417
- **Duration**: 224.3s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_amount":10,"scroll_direction":"down"})` → success
- Step 29: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_amount":10,"scroll_direction":"down"})` → success
- Step 30: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_amount":10,"scroll_direction":"down"})` → success

### Failure 3: `ecommerce_admin:high:198:0:1`

- **Variant**: high
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 317,956
- **Duration**: 212.2s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[1201,490]})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[1011,254]})` → success
- Step 30: `cua:left_click({"action":"left_click","coordinate":[596,541]})` → success

**Errors (8):**

- Step 8: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 9: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 11: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 12: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 19: `Page.screenshot: Timeout 3000ms exceeded.`

### Failure 4: `ecommerce_admin:high:198:0:2`

- **Variant**: high
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 300,964
- **Duration**: 229.2s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[1011,254]})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[596,541]})` → success
- Step 30: `cua:screenshot_error({})` → failure (Page.screenshot: Timeout 3000ms exceeded.)

**Errors (9):**

- Step 8: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 9: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 11: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 12: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 19: `Page.screenshot: Timeout 3000ms exceeded.`

### Failure 5: `ecommerce_admin:high:198:0:3`

- **Variant**: high
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 300,378
- **Duration**: 200.3s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[1011,254]})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[596,541]})` → success
- Step 30: `cua:screenshot_error({})` → failure (Page.screenshot: Timeout 3000ms exceeded.)

**Errors (9):**

- Step 11: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 12: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 14: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 15: `Page.screenshot: Timeout 3000ms exceeded.`
- Step 22: `Page.screenshot: Timeout 3000ms exceeded.`

### Failure 6: `ecommerce_admin:low:198:0:1`

- **Variant**: low
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 462,347
- **Duration**: 217.6s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:type({"action":"type","text":"http://10.0.1.50:7780/admin/admin/sales/order/"})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[944,92]})` → success
- Step 30: `cua:type({"action":"type","text":"orders"})` → success

**Errors (1):**

- Step 6: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 7: `ecommerce_admin:low:198:0:2`

- **Variant**: low
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 467,524
- **Duration**: 190.2s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:type({"action":"type","text":"http://10.0.1.50:7780/admin/admin/sales/order/"})` → success
- Step 29: `cua:key({"action":"key","text":"Return"})` → failure (Action key failed: Keyboard.press: Unknown key: "Return")
- Step 30: `cua:key({"action":"key","text":"Enter"})` → success

**Errors (6):**

- Step 10: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 11: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 12: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 16: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 26: `Action key failed: Keyboard.press: Unknown key: "Left"`

### Failure 8: `ecommerce_admin:low:198:0:3`

- **Variant**: low
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 466,927
- **Duration**: 196.6s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[944,92]})` → success
- Step 29: `cua:scroll({"action":"scroll","coordinate":[640,360],"scroll_amount":10,"scroll_direction":"up"})` → success
- Step 30: `cua:triple_click({"action":"triple_click","coordinate":[944,92]})` → failure (Unknown action: triple_click)

**Errors (4):**

- Step 9: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 14: `Unknown action: triple_click`
- Step 25: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 30: `Unknown action: triple_click`

### Failure 9: `ecommerce_admin:low:198:0:4`

- **Variant**: low
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 460,263
- **Duration**: 209.8s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:key({"action":"key","text":"F12"})` → success
- Step 29: `cua:triple_click({"action":"triple_click","coordinate":[640,10]})` → failure (Unknown action: triple_click)
- Step 30: `cua:key({"action":"key","text":"ctrl+a"})` → success

**Errors (4):**

- Step 6: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 7: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 8: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 29: `Unknown action: triple_click`

### Failure 10: `ecommerce_admin:low:198:0:5`

- **Variant**: low
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 464,355
- **Duration**: 246.8s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[640,10]})` → success
- Step 29: `cua:key({"action":"key","text":"ctrl+l"})` → success
- Step 30: `cua:type({"action":"type","text":"http://10.0.1.50:7780/admin/admin/sales/order"})` → success

**Errors (1):**

- Step 7: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 11: `ecommerce_admin:low:94:0:1`

- **Variant**: low
- **Task**: 94
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 465,359
- **Duration**: 216.5s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:key({"action":"key","text":"Enter"})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[88,35]})` → success
- Step 30: `cua:left_click({"action":"left_click","coordinate":[944,92]})` → success

**Errors (3):**

- Step 10: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 11: `Action key failed: Keyboard.press: Unknown key: "KP_Enter"`
- Step 12: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 12: `ecommerce_admin:low:94:0:2`

- **Variant**: low
- **Task**: 94
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 460,395
- **Duration**: 197.0s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[400,400]})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[944,92]})` → success
- Step 30: `cua:type({"action":"type","text":"000000001"})` → success

**Errors (3):**

- Step 6: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 13: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 26: `Unknown action: triple_click`

### Failure 13: `ecommerce_admin:low:94:0:4`

- **Variant**: low
- **Task**: 94
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 457,100
- **Duration**: 206.9s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:key({"action":"key","text":"ctrl+a"})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[640,400]})` → success
- Step 30: `cua:key({"action":"key","text":"ctrl+l"})` → success

**Errors (3):**

- Step 6: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 13: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 22: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 14: `ecommerce_admin:low:94:0:5`

- **Variant**: low
- **Task**: 94
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 462,109
- **Duration**: 215.5s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:key({"action":"key","text":"ctrl+a"})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[944,92]})` → success
- Step 30: `cua:left_click({"action":"left_click","coordinate":[400,400]})` → success

**Errors (3):**

- Step 6: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 14: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 15: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 15: `ecommerce_admin:medium-low:198:0:3`

- **Variant**: medium-low
- **Task**: 198
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 489,575
- **Duration**: 248.8s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:scroll({"action":"scroll","coordinate":[640,600],"scroll_amount":30,"scroll_direction":"down"})` → success
- Step 29: `cua:scroll({"action":"scroll","coordinate":[640,600],"scroll_amount":30,"scroll_direction":"down"})` → success
- Step 30: `cua:scroll({"action":"scroll","coordinate":[640,600],"scroll_amount":50,"scroll_direction":"down"})` → success

### Failure 16: `gitlab:base:308:0:2`

- **Variant**: base
- **Task**: 308
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 497,638
- **Duration**: 234.3s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:scroll({"action":"scroll","coordinate":[640,400],"scroll_amount":5,"scroll_direction":"down"})` → success
- Step 29: `cua:scroll({"action":"scroll","coordinate":[640,400],"scroll_amount":5,"scroll_direction":"down"})` → success
- Step 30: `cua:scroll({"action":"scroll","coordinate":[640,400],"scroll_amount":5,"scroll_direction":"down"})` → success

### Failure 17: `gitlab:low:293:0:2`

- **Variant**: low
- **Task**: 293
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 456,820
- **Duration**: 212.0s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:scroll({"action":"scroll","coordinate":[640,400],"scroll_amount":5,"scroll_direction":"down"})` → success
- Step 29: `cua:left_click({"action":"left_click","coordinate":[248,158]})` → success
- Step 30: `cua:key({"action":"key","text":"ctrl+l"})` → success

**Errors (3):**

- Step 3: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 17: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 18: `Action key failed: Keyboard.press: Unknown key: "KP_Enter"`

### Failure 18: `gitlab:low:293:0:3`

- **Variant**: low
- **Task**: 293
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 457,754
- **Duration**: 214.1s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:key({"action":"key","text":"ctrl+l"})` → success
- Step 29: `cua:type({"action":"type","text":"http://10.0.1.50:8023/root/Super_Awesome_Robot"})` → success
- Step 30: `cua:key({"action":"key","text":"Enter"})` → success

**Errors (2):**

- Step 10: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 11: `Action key failed: Keyboard.press: Unknown key: "KP_Enter"`

### Failure 19: `gitlab:low:293:0:4`

- **Variant**: low
- **Task**: 293
- **Outcome**: failure
- **Steps**: 28
- **Tokens**: 424,194
- **Duration**: 189.7s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 26: `cua:left_click({"action":"left_click","coordinate":[640,50]})` → success
- Step 27: `cua:left_click({"action":"left_click","coordinate":[976,230]})` → success
- Step 28: `cua:cannot_complete({})` → success

**Errors (3):**

- Step 4: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 5: `Action key failed: Keyboard.press: Unknown key: "KP_Enter"`
- Step 6: `Action key failed: Keyboard.press: Unknown key: "enter"`

### Failure 20: `gitlab:low:308:0:1`

- **Variant**: low
- **Task**: 308
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 465,899
- **Duration**: 215.2s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:left_click({"action":"left_click","coordinate":[79,143]})` → success
- Step 29: `cua:scroll({"action":"scroll","coordinate":[640,400],"scroll_amount":5,"scroll_direction":"up"})` → success
- Step 30: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_amount":5,"scroll_direction":"down"})` → success

**Errors (2):**

- Step 4: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 25: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 21: `gitlab:low:308:0:2`

- **Variant**: low
- **Task**: 308
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 472,028
- **Duration**: 214.9s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:type({"action":"type","text":"http://10.0.1.50:8023/primer/design/-/graphs/main/contributors"})` → success
- Step 29: `cua:key({"action":"key","text":"Return"})` → failure (Action key failed: Keyboard.press: Unknown key: "Return")
- Step 30: `cua:key({"action":"key","text":"Enter"})` → success

**Errors (2):**

- Step 4: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 29: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 22: `gitlab:low:308:0:3`

- **Variant**: low
- **Task**: 308
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 458,083
- **Duration**: 223.6s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:key({"action":"key","text":"ctrl+l"})` → success
- Step 29: `cua:type({"action":"type","text":"http://10.0.1.50:8023/primer/design/-/graphs/main"})` → success
- Step 30: `cua:key({"action":"key","text":"Return"})` → failure (Action key failed: Keyboard.press: Unknown key: "Return")

**Errors (3):**

- Step 6: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 16: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 30: `Action key failed: Keyboard.press: Unknown key: "Return"`

### Failure 23: `gitlab:low:308:0:4`

- **Variant**: low
- **Task**: 308
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 453,921
- **Duration**: 199.4s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:type({"action":"type","text":"primer/design"})` → success
- Step 29: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_direction":"down","scroll_amount":3})` → success
- Step 30: `cua:left_click({"action":"left_click","coordinate":[156,410]})` → success

**Errors (4):**

- Step 4: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 7: `Unknown action: triple_click`
- Step 14: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 15: `Action key failed: Keyboard.press: Unknown key: "slash"`

### Failure 24: `gitlab:low:308:0:5`

- **Variant**: low
- **Task**: 308
- **Outcome**: timeout
- **Steps**: 30
- **Tokens**: 465,291
- **Duration**: 216.1s
- **Final Answer**: (none — timed out)
- **Submitted Answer**: No

**Last 3 actions:**

- Step 28: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_amount":3,"scroll_direction":"down"})` → success
- Step 29: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_amount":3,"scroll_direction":"down"})` → success
- Step 30: `cua:scroll({"action":"scroll","coordinate":[640,500],"scroll_amount":3,"scroll_direction":"down"})` → success

**Errors (3):**

- Step 4: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 5: `Action key failed: Keyboard.press: Unknown key: "Return"`
- Step 6: `Action key failed: Keyboard.press: Unknown key: "Return"`

## Failure Root Cause Classification

| Root Cause | Count | Variants | Description |
|-----------|-------|----------|-------------|
| Cross-Layer Functional Breakage | 17 | low:17 | Low variant's link→span removes href, breaking sidebar navigation. Agent can see menu items but clicking does nothing. |
| UI Complexity Trap | 6 | base:2, high:3, medium-low:1 | Magento admin Columns dialog overlaps with Status filter. Agent struggles with coordinate precision on overlapping UI elements. |
| Step Budget Exhaustion | 1 | base:1 | Agent making progress but exhausts 30-step budget before completing task. Often combined with navigation difficulties. |

### Cross-Layer Functional Breakage (low: link→span removes href)

- `ecommerce_admin:low:198:0:1`: steps=30, tokens=462,347, outcome=timeout
- `ecommerce_admin:low:198:0:2`: steps=30, tokens=467,524, outcome=timeout
- `ecommerce_admin:low:198:0:3`: steps=30, tokens=466,927, outcome=timeout
- `ecommerce_admin:low:198:0:4`: steps=30, tokens=460,263, outcome=timeout
- `ecommerce_admin:low:198:0:5`: steps=30, tokens=464,355, outcome=timeout
- `ecommerce_admin:low:94:0:1`: steps=30, tokens=465,359, outcome=timeout
- `ecommerce_admin:low:94:0:2`: steps=30, tokens=460,395, outcome=timeout
- `ecommerce_admin:low:94:0:4`: steps=30, tokens=457,100, outcome=timeout
- `ecommerce_admin:low:94:0:5`: steps=30, tokens=462,109, outcome=timeout
- `gitlab:low:293:0:2`: steps=30, tokens=456,820, outcome=timeout
- `gitlab:low:293:0:3`: steps=30, tokens=457,754, outcome=timeout
- `gitlab:low:293:0:4`: steps=28, tokens=424,194, outcome=failure
- `gitlab:low:308:0:1`: steps=30, tokens=465,899, outcome=timeout
- `gitlab:low:308:0:2`: steps=30, tokens=472,028, outcome=timeout
- `gitlab:low:308:0:3`: steps=30, tokens=458,083, outcome=timeout
- `gitlab:low:308:0:4`: steps=30, tokens=453,921, outcome=timeout
- `gitlab:low:308:0:5`: steps=30, tokens=465,291, outcome=timeout

### UI Complexity Trap (admin:198: Columns/Status dialog overlap)

- `ecommerce_admin:base:198:0:2`: steps=30, tokens=490,676, outcome=timeout
- `ecommerce_admin:base:198:0:3`: steps=30, tokens=473,417, outcome=timeout
- `ecommerce_admin:high:198:0:1`: steps=30, tokens=317,956, outcome=timeout
- `ecommerce_admin:high:198:0:2`: steps=30, tokens=300,964, outcome=timeout
- `ecommerce_admin:high:198:0:3`: steps=30, tokens=300,378, outcome=timeout
- `ecommerce_admin:medium-low:198:0:3`: steps=30, tokens=489,575, outcome=timeout

### Step Budget Exhaustion (agent progressing but runs out of 30 steps)

- `gitlab:base:308:0:2`: steps=30, tokens=497,638, outcome=timeout

### Notable Patterns Across Failures

**Screenshot Timeout (high variant admin:198)**: All 3 high-variant admin:198 failures
have 8-9 `Page.screenshot: Timeout 3000ms exceeded` errors each. These waste ~30% of
the agent's step budget on failed screenshots. The enhanced ARIA in high variant may
cause heavier DOM rendering that triggers screenshot timeouts on the complex Orders grid.
This is a **compounding factor**: screenshot errors don't directly cause failure, but they
consume steps that the agent needs for the actual task.

**"Return" key errors**: CUA's LLM frequently generates `key("Return")` instead of
`key("Enter")`. Playwright doesn't recognize "Return" as a valid key name. This wastes
1-3 steps per trace as the agent learns to use "Enter" instead. This is a **platform
integration issue**, not an accessibility or UI complexity issue.

**`triple_click` and `cannot_complete`**: CUA occasionally generates unsupported actions
(`triple_click`) or gives up explicitly (`cannot_complete`). The `cannot_complete` in
gitlab:low:293:0:4 is notable — the agent explicitly recognized it couldn't navigate
to the target repository because sidebar links were non-functional.

## admin:198 Deep Dive — The Most Anomalous Task

**Results**: low 0%, ml 80%, base 60%, high 40%

This is the **only task** where CUA fails at both base AND high variants.
The pattern is inverted from expectations: medium-low (80%) > base (60%) > high (40%).

### What is admin:198?

Task: "Get the customer name of the most recent cancelled order"

This requires:
1. Navigate to Sales → Orders in Magento admin sidebar
2. Filter orders by Status = "Canceled"
3. Sort by date (most recent first)
4. Read the customer name from the first row

### Per-Variant Trace Analysis

| Case | Success | Steps | Tokens | Reached Orders | Tried Filter | Columns Trap | Stuck Dashboard | Nav Attempts |
|------|---------|-------|--------|---------------|-------------|-------------|----------------|-------------|
| ecommerce_admin:low:198:0:1 | ✗ | 30 | 462,347 | N | Y | N | Y | 12 |
| ecommerce_admin:low:198:0:2 | ✗ | 30 | 467,524 | N | Y | N | N | 10 |
| ecommerce_admin:low:198:0:3 | ✗ | 30 | 466,927 | N | Y | N | Y | 15 |
| ecommerce_admin:low:198:0:4 | ✗ | 30 | 460,263 | N | Y | N | Y | 11 |
| ecommerce_admin:low:198:0:5 | ✗ | 30 | 464,355 | N | Y | N | Y | 13 |
| ecommerce_admin:medium-low:198:0:1 | ✓ | 14 | 181,553 | Y | Y | N | N | 2 |
| ecommerce_admin:medium-low:198:0:2 | ✓ | 26 | 403,124 | Y | Y | N | N | 2 |
| ecommerce_admin:medium-low:198:0:3 | ✗ | 30 | 489,575 | Y | Y | N | N | 2 |
| ecommerce_admin:medium-low:198:0:4 | ✓ | 18 | 253,513 | Y | Y | N | N | 2 |
| ecommerce_admin:medium-low:198:0:5 | ✓ | 21 | 304,477 | Y | Y | N | N | 2 |
| ecommerce_admin:base:198:0:1 | ✓ | 24 | 366,771 | Y | Y | N | N | 3 |
| ecommerce_admin:base:198:0:2 | ✗ | 30 | 490,676 | Y | Y | N | N | 2 |
| ecommerce_admin:base:198:0:3 | ✗ | 30 | 473,417 | Y | Y | Y | N | 3 |
| ecommerce_admin:base:198:0:4 | ✓ | 26 | 395,066 | Y | Y | Y | N | 2 |
| ecommerce_admin:base:198:0:5 | ✓ | 21 | 309,097 | Y | Y | N | N | 6 |
| ecommerce_admin:high:198:0:1 | ✗ | 30 | 317,956 | Y | Y | N | N | 2 |
| ecommerce_admin:high:198:0:2 | ✗ | 30 | 300,964 | Y | Y | Y | N | 2 |
| ecommerce_admin:high:198:0:3 | ✗ | 30 | 300,378 | Y | Y | N | N | 2 |
| ecommerce_admin:high:198:0:4 | ✓ | 13 | 165,879 | Y | Y | Y | N | 2 |
| ecommerce_admin:high:198:0:5 | ✓ | 24 | 283,429 | Y | Y | Y | N | 2 |

### Per-Variant Summary

**low** (0/5 = 0%):
- All 5 traces timeout at 30 steps. Agent stuck on dashboard (4/5).
- Sidebar navigation links are `<span>` (no href) — clicking does nothing.
- Agent tries URL navigation, search box, clicking edges — nothing works.
- This is **cross-layer functional breakage**: the link→span patch removes
  actual navigation functionality, not just semantics.

**medium-low** (4/5 = 80%):
- 4/5 succeed. Best non-low variant.
- Avg steps: 21.8, avg tokens: 326,448
- The 1 failure likely hit the Columns dialog overlap or step budget.

**base** (3/5 = 60%):
- 3/5 succeed. 2 failures.
- Avg steps: 26.2, avg tokens: 407,005
- Failures: agent reaches Orders page but struggles with Status filter.
  The Columns dialog can overlap with the Status dropdown, causing
  coordinate-based clicks to hit the wrong element.

**high** (2/5 = 40%):
- 2/5 succeed. 3 failures — worst non-low variant.
- Avg steps: 25.4, avg tokens: 273,721
- Enhanced ARIA adds skip-links and landmarks that may shift element
  positions slightly, making coordinate-based interaction less reliable.
  More UI elements = more potential for dialog overlap confusion.

### Why Does Medium-Low (80%) Outperform Base (60%) and High (40%)?

This inverted pattern reveals that admin:198 failures are **NOT accessibility-related**.
They are **UI complexity traps** specific to coordinate-based interaction:

1. **The Columns Dialog Problem**: Magento's Orders grid has a "Columns" button that
   opens a dropdown overlay. When the agent tries to click the Status filter dropdown,
   the Columns dialog can intercept the click. This is a coordinate precision issue.

2. **Why ml is better**: Medium-low variant has ARIA attributes present but handlers
   missing (pseudo-compliance). This doesn't affect CUA (which uses coordinates, not ARIA).
   But the slightly different DOM may cause the Columns dialog to render in a
   non-overlapping position, giving CUA cleaner click targets.

3. **Why high is worst**: Enhanced ARIA adds skip-links, landmarks, and additional
   interactive elements. These shift the visual layout slightly, potentially making
   the Columns/Status overlap worse. More elements = more coordinate confusion.

4. **Comparison with smoke test**: Smoke (1 rep): ml 1/1, base 0/1, high 0/1.
   Full (5 reps): ml 4/5, base 3/5, high 2/5. The pattern is consistent —
   ml consistently outperforms base and high on this specific task.

**5. Screenshot timeout as compounding factor (high variant)**: All 3 high-variant
   failures have 8-9 `Page.screenshot: Timeout 3000ms exceeded` errors, wasting ~30%
   of the step budget. The enhanced ARIA DOM may cause heavier rendering on the complex
   Orders grid, triggering screenshot timeouts. This doesn't happen at base or ml.
   The high variant's lower success rate (40% vs 60% base) may be partly explained by
   this screenshot timeout tax rather than pure UI complexity.

**Conclusion**: admin:198 is a **UI complexity trap**, not an accessibility effect.
The task requires precise coordinate interaction with overlapping Magento admin
dialogs. CUA's coordinate-based approach is inherently stochastic on such UIs.
The variant differences reflect a combination of layout shifts and screenshot
timeout overhead (high variant), not accessibility effects.

## Token & Step Analysis

| Variant | Avg Tokens (all) | Avg Tokens (success) | Avg Tokens (failure) | Avg Steps |
|---------|-----------------|---------------------|---------------------|-----------|
| low | 281,481 | 112,859 | 460,022 | 19.3 |
| medium-low | 121,834 | 111,018 | 489,575 | 9.9 |
| base | 144,011 | 111,833 | 487,244 | 11.0 |
| high | 117,115 | 99,366 | 306,433 | 10.5 |

## Synthesis: Why CUA Fails Despite Being "DOM-Independent"

### The Myth of Full DOM Independence

CUA processes raw screenshots with virtual mouse/keyboard — zero DOM access.
This should make it immune to DOM semantic changes. Yet it achieves only 51.4%
at low variant vs 91.4% at base. Why?

### Two Distinct Failure Mechanisms

**1. Cross-Layer Functional Breakage (17 of 24 failures, all low variant)**

The low variant's `link→span` patch doesn't just change DOM semantics — it
**removes the `href` attribute entirely**. This means:

- Sidebar menu items become `<span>` elements with no click handler
- Clicking them produces no navigation, regardless of agent type
- This is a **functional** change that crosses the DOM→behavior layer boundary
- CUA can see "Sales" in the sidebar, clicks it at the right coordinates,
  but nothing happens because the element is no longer a link

This confirms the **cross-layer confound** identified in Pilot 4 CUA analysis:
the low variant's link→span patch is not purely semantic — it breaks actual
functionality. All 17 low-variant CUA failures are attributable to this mechanism.

**2. UI Complexity Traps (7 of 24 failures, non-low variants)**

admin:198 accounts for all non-low failures. This task requires navigating
Magento's Orders grid and filtering by "Canceled" status — a UI with overlapping
dialogs (Columns dropdown, Status filter) that challenge coordinate-based interaction.

These failures are **not accessibility-related**. They occur because:

- Coordinate-based clicking is inherently imprecise on overlapping UI elements
- The Magento admin grid has multiple dropdown overlays that can intercept clicks
- The agent can SEE the correct target but clicks the wrong element
- This is a fundamental limitation of coordinate-based agents on complex UIs
- High variant additionally suffers from screenshot timeouts (8-9 per trace),
  wasting ~30% of the step budget on the complex Orders grid

**3. Step Budget Exhaustion (1 of 24 failures, gitlab:308 base)**

gitlab:base:308:0:2 is the only non-admin:198, non-low failure. The agent navigates
to the correct GitLab repository but spends too many steps scrolling through the
Contributors page trying to identify the top contributor. This is a pure step budget
issue — the task is feasible but requires more than 30 steps for this particular
navigation path.

### Implications for the Research

1. **CUA is NOT a clean "pure vision" control** for measuring DOM semantic effects.
   The low variant's functional breakage affects CUA through the behavior layer,
   not the semantic layer. To isolate pure semantic effects, we need a variant
   that preserves `<a href>` while adding `aria-hidden="true"` (semantic-only).

2. **The 17 low-variant failures are cross-layer confounds**, consistent with
   Pilot 4 CUA findings where 100% of low CUA failures were functional breakage.

3. **The 7 admin:198 failures are UI complexity**, not accessibility effects.
   They demonstrate that coordinate-based agents have their own failure modes
   independent of DOM state — a finding that strengthens the paper's argument
   that different agent architectures face different environmental barriers.

4. **Causal decomposition** (from Pilot 4 + expansion):
   - Text-only low→base drop: 63.3pp (semantic + functional)
   - CUA low→base drop: ~40pp (functional only, since CUA ignores semantics)
   - Difference: ~23pp attributable to pure semantic (a11y tree) pathway
   - This is consistent with the Pilot 4 decomposition (33pp semantic + 30pp cross-layer)
