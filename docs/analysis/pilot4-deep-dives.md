# Pilot 4 Deep Dive Analysis

**Date:** 2026-04-08
**Data:** 240/240 traces, Run ID f4929214
---

## 1. reddit:67 Anomaly — Why base/high = 20%

**Loaded:** 20 text-only traces for reddit:67

### Per-Variant Results

| Variant | Success | Total | Rate | Avg Tokens | Avg Steps |
|---------|---------|-------|------|-----------|-----------|
| low | 2 | 5 | 40% | 109,546 | 5.2 |
| medium-low | 5 | 5 | 100% | 137,063 | 4.0 |
| base | 1 | 5 | 20% | 460,570 | 7.6 |
| high | 1 | 5 | 20% | 503,379 | 7.8 |

### Base Variant Trace-by-Trace

**reddit_base_67_0_1:** failure, steps=9, tokens=608,149
  Last reasoning: LLM call failed
  Actions: [(1, 'click("43")'), (2, 'click("544")'), (3, 'click("152")'), (4, 'go_back()'), (5, 'click("454")'), (6, 'go_back()'), (7, 'click("604")'), (8, 'go_back()')]

**reddit_base_67_0_2:** failure, steps=9, tokens=608,262
  Last reasoning: LLM call failed
  Actions: [(1, 'click("43")'), (2, 'click("544")'), (3, 'click("152")'), (4, 'click("120")'), (5, 'click("454")'), (6, 'click("120")'), (7, 'click("604")'), (8, 'click("120")')]

**reddit_base_67_0_3:** failure, steps=9, tokens=609,422
  Last reasoning: LLM call failed
  Actions: [(1, 'click("43")'), (2, 'click("544")'), (3, 'click("152")'), (4, 'go_back()'), (5, 'click("454")'), (6, 'go_back()'), (7, 'click("604")'), (8, 'go_back()')]

**reddit_base_67_0_4:** success, steps=3, tokens=43,858
  Answer: `The Haunting of Hill House, The Hobbit, A Christmas Carol`
  Last reasoning: Great! I'm now in the books forum and can see the posts sorted by 'Hot' which should show the top posts. I can see the first 25 posts displayed. I need to examine the top 10 posts to identify which on
  Actions: [(1, 'click("43")'), (2, 'click("544")'), (3, 'send_msg_to_user("The Haunting of Hill House, The Hobbit, A Christmas Carol")')]

**reddit_base_67_0_5:** failure, steps=8, tokens=433,157
  Last reasoning: LLM call failed
  Actions: [(1, 'click("43")'), (2, 'click("544")'), (3, 'click("152")'), (4, 'click("120")'), (5, 'click("454")'), (6, 'click("120")'), (7, 'click("604")'), (8, 'noop()')]

### High Variant Trace-by-Trace

**reddit_high_67_0_1:** failure, steps=9, tokens=617,566

**reddit_high_67_0_2:** failure, steps=9, tokens=618,765

**reddit_high_67_0_3:** failure, steps=9, tokens=618,746

**reddit_high_67_0_4:** success, steps=3, tokens=43,843
  Answer: `The Haunting of Hill House, Misty of Chincoteague, The Hobbit, A Christmas Carol`

**reddit_high_67_0_5:** failure, steps=9, tokens=617,976

### Medium-Low (100% success) — What's Different?

**reddit_medium-low_67_0_1:** success, steps=3
  Answer: `The Haunting of Hill House, The Hobbit, A Christmas Carol`

**reddit_medium-low_67_0_2:** success, steps=8
  Answer: `Based on the top 10 posts in the books forum that recommend single books, here are the book names: 1. The Haunting of Hill House 2. The Hobbit   3. A Christmas Carol 4. Things Fall Apart 5. The Bell J`

### Diagnosis

Base answers: ['The Haunting of Hill House, The Hobbit, A Christmas Carol']
ML answers: ['The Haunting of Hill House, The Hobbit, A Christmas Carol', 'Based on the top 10 posts in the books forum that recommend single books, here are the book names: 1. The Haunting of Hill House 2. The Hobbit   3. A Christmas Carol 4. Things Fall Apart 5. The Bell J', 'The Haunting of Hill House, The Hobbit, A Christmas Carol', 'The Haunting of Hill House, The Hobbit, A Christmas Carol', 'The Haunting of Hill House, Misty of Chincoteague, The Hobbit, A Christmas Carol']

## 2. ecom:24 Low — The 1/5 Success Case

**Loaded:** 5 traces

### All 5 Traces

❌ **ecommerce_low_24_0_1:** steps=12, tokens=143,744, outcome=failure
  Answer: `cannot complete`
  tablist=False, tabpanel=False
  Actions: ['click("1557")', 'scroll(0, 500)', 'scroll(0, 800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'scroll(0, 500)', 'scroll(0, -300)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'noop()', 'scroll(0, 800)', 'scroll(0, -400)', 'scroll(0, 1000)', 'send_msg_to_user("cannot complete")']

❌ **ecommerce_low_24_0_2:** steps=10, tokens=109,832, outcome=partial_success
  Answer: `Cannot access the review content. The page indicates there are 2 reviews for this product, but the detailed review text containing reviewer information and comments about pricing is not accessible thr`
  tablist=False, tabpanel=False
  Actions: ['click("1556")', 'scroll(0, 500)', 'scroll(0, 800)', 'go_back()', 'scroll(0, -500)', 'scroll(0, -800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'scroll(0, 800)', 'scroll(0, 1000)', 'send_msg_to_user("Cannot access the review content. The page indicates there are']

❌ **ecommerce_low_24_0_3:** steps=9, tokens=97,259, outcome=failure
  Answer: `cannot complete`
  tablist=False, tabpanel=False
  Actions: ['click("1556")', 'scroll(0, 500)', 'scroll(0, 800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'scroll(0, -500)', 'scroll(0, -800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'scroll(0, 1000)', 'send_msg_to_user("cannot complete")']

❌ **ecommerce_low_24_0_4:** steps=11, tokens=125,787, outcome=failure
  Answer: `cannot complete`
  tablist=False, tabpanel=False
  Actions: ['click("1556")', 'scroll(0, 500)', 'scroll(0, 800)', 'go_back()', 'scroll(0, -800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'noop()', 'scroll(0, 800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'scroll(0, 1000)', 'send_msg_to_user("cannot complete")']

✅ **ecommerce_low_24_0_5:** steps=10, tokens=113,440, outcome=success
  Answer: `No reviewers found mentioning unfair pricing - the review content is not accessible on this page despite showing 2 reviews exist`
  tablist=False, tabpanel=False
  Actions: ['click("1557")', 'scroll(0, 500)', 'scroll(0, 800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'scroll(0, -500)', 'scroll(0, -800)', 'goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-5', 'scroll(0, 1000)', 'scroll(0, 1500)', 'send_msg_to_user("No reviewers found mentioning unfair pricing - the review cont']

### Success Case Deep Dive

Step 1: action=`click("1557")`
  result=success, reasoning=I need to find reviews that mention price being unfair. I can see there's a "Reviews (2)" tab on this product page. Let me click on it to see the revi

Step 2: action=`scroll(0, 500)`
  result=success, reasoning=I can see that I clicked on the Reviews tab, but the actual review content is not visible in the current accessibility tree. The page seems to have lo

Step 3: action=`scroll(0, 800)`
  result=success, reasoning=I still don't see the actual review content. Let me try scrolling down more to find the reviews section, as it might be further down the page.

{"reas

Step 4: action=`goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-550-peat-us-7.html")`
  result=success, reasoning=I'm still not seeing the actual review content. Let me try refreshing the page or going back to the original URL to see if I can access the reviews di

Step 5: action=`scroll(0, -500)`
  result=success, reasoning=I'm back on the main product page. I can see there are 2 reviews mentioned, but I need to find a way to access the actual review content. Let me try c

Step 6: action=`scroll(0, -800)`
  result=success, reasoning=I can see the page structure but I'm not seeing the clickable elements with their BIDs clearly. Let me scroll up to get back to the product details se

Step 7: action=`goto("http://10.0.1.49:7770/haflinger-men-s-wool-felt-open-back-slippers-beige-550-peat-us-7.html")`
  result=success, reasoning=I can see the page content but I'm not seeing the clickable elements with their BIDs in the accessibility tree. Let me try refreshing the page to get 

Step 8: action=`scroll(0, 1000)`
  result=success, reasoning=I notice that the accessibility tree is not showing clickable links or buttons with proper BIDs for the reviews section. The "Reviews" and "Add Your R

Step 9: action=`scroll(0, 1500)`
  result=success, reasoning=I can see that there are 2 reviews mentioned in the rating section, but the actual review content is not visible in the accessibility tree. It appears

Step 10: action=`send_msg_to_user("No reviewers found mentioning unfair pricing - the review content is not accessibl`
  result=success, reasoning=After thoroughly examining the page, I can see that while there are 2 reviews mentioned in the rating section, the actual review content is not access


## 3. admin:4 High — The 1 Failure Case

**Loaded:** 5 traces

### All 5 Traces

✅ **ecommerce_admin_high_4_0_1:** steps=11, tokens=143,725, skip-link mentions=11
  Answer: `1. Impulse Duffle (2 units sold)n2. Overnight Duffle (2 units sold)n3. Hawkeye Yoga Short-32-Blue (2 units sold)`

✅ **ecommerce_admin_high_4_0_2:** steps=10, tokens=130,427, skip-link mentions=10
  Answer: `1. Impulse Duffle (2 units), 2. Overnight Duffle (2 units), 3. Hawkeye Yoga Short-32-Blue (2 units)`

✅ **ecommerce_admin_high_4_0_3:** steps=6, tokens=69,097, skip-link mentions=6
  Answer: `1. Overnight Duffle (2 units), 2. Impulse Duffle (2 units), 3. Hawkeye Yoga Short-32-Blue (2 units)`

❌ **ecommerce_admin_high_4_0_4:** steps=10, tokens=130,534, skip-link mentions=10
  Answer: `1. Stellar Solar Jacket-L-Yellow ($75.00), 2. Impulse Duffle ($74.00), 3. Orion Two-Tone Fitted Jacket-XL-Black ($72.00)`

✅ **ecommerce_admin_high_4_0_5:** steps=6, tokens=68,912, skip-link mentions=6
  Answer: `1. Overnight Duffle (2 units), 2. Impulse Duffle (2 units), 3. Hawkeye Yoga Short-32-Blue (2 units)`

### Token Comparison: High vs Base

- High: avg=108,539, med=130,427, values=[143725, 130427, 69097, 130534, 68912]
- Base: avg=107,101, med=116,653, values=[102027, 130269, 117776, 68778, 116653]
- Δ: +1,438 (+1.3%)

### Failure Case Deep Dive

Case: ecommerce_admin_high_4_0_4, outcome=partial_success, steps=10, tokens=130,534
  Step 1: `click("339")` → success
  Step 2: `click("431")` → success
  Step 3: `click("753")` → success
  Step 4: `click("755")` → failure
  Step 5: `click("761")` → success
  Step 6: `fill("761", "01/01/2023")` → success
  Step 7: `click("768")` → success
  Step 8: `fill("768", "01/31/2023")` → success
  Step 9: `click("726")` → success
  Step 10: `send_msg_to_user("1. Stellar Solar Jacket-L-Yellow ($75.00), 2. Impulse Duffle ($74.00), 3. Orion Tw` → success

## 4. Vision Phantom Label Classification

Sampling 2-3 vision-only failure traces per site to classify phantom label modes.

### Classification Results

- **Mode A** (element exists, not visible): 2 traces
- **Mode B** (element doesn't exist): 0 traces
- **Other**: 7 traces

### Trace Details

- `ecommerce_admin_base_4_1_1`: Other (none) — errors: {}
- `ecommerce_admin_base_4_1_2`: Other (none) — errors: {}
- `ecommerce_admin_base_4_1_3`: Other (none) — errors: {}
- `ecommerce_admin_base_4_1_1`: Other (none) — errors: {}
- `ecommerce_admin_base_4_1_2`: Other (none) — errors: {}
- `ecommerce_admin_base_4_1_3`: Other (none) — errors: {}
- `reddit_base_29_1_1`: Other (other) — errors: {'not_visible': 3, 'other': 4}
- `reddit_base_29_1_2`: A (exists, not visible) — errors: {'not_visible': 2, 'other': 1}
- `reddit_base_29_1_3`: A (exists, not visible) — errors: {'not_visible': 2}

## 5. reddit:29 High — 3 Failures (60%)

**Loaded:** 5 traces

### All 5 Traces

❌ **reddit_high_29_0_1:** steps=7, tokens=323,593, skip-links=7
  Answer: `0`

✅ **reddit_high_29_0_2:** steps=6, tokens=171,985, skip-links=6
  Answer: `1`

❌ **reddit_high_29_0_3:** steps=5, tokens=172,322, skip-links=5
  Answer: `0`

✅ **reddit_high_29_0_4:** steps=6, tokens=172,169, skip-links=6
  Answer: `1`

✅ **reddit_high_29_0_5:** steps=6, tokens=172,359, skip-links=6
  Answer: `1`

### Comparison: High vs Base

- High tokens: avg=202,486, values=[323593, 171985, 172322, 172169, 172359]
- Base tokens: avg=169,531, values=[169255, 169266, 170349, 169356, 169429]
- High success: 3/5
- Base success: 5/5

### 2 Failure Traces

**reddit_high_29_0_1:** outcome=partial_success, steps=7, tokens=323,593
  Answer: `0`
  Last reasoning: I've now thoroughly examined all of Maoman1's comments that are visible on this page. After scrolling through multiple times, I can see that this appears to be the complete list of comments from this user. All 16 comments show positive vote scores: 3
  Actions: [(1, 'click("403")'), (2, 'scroll(0, 500)'), (3, 'scroll(0, 500)'), (4, 'click("115")'), (5, 'scroll(0, 500)'), (6, 'scroll(0, 500)'), (7, 'send_msg_to_user("0")')]

**reddit_high_29_0_3:** outcome=partial_success, steps=5, tokens=172,322
  Answer: `0`
  Last reasoning: I have thoroughly examined all of Maoman1's comments on this page. After scrolling through the entire comments section, I can see that all 16 comments displayed have positive vote scores:

1. Comment [t1_je5auqz]: 3 upvotes
2. Comment [t1_je2r0hi]: 1
  Actions: [(1, 'click("403")'), (2, 'click("115")'), (3, 'scroll(0, 500)'), (4, 'scroll(0, 1000)'), (5, 'send_msg_to_user("0")')]

## 6. Token Inflation — Controlled Comparison

Compare high vs base tokens on tasks where BOTH have 100% success,

eliminating failure-driven token inflation as a confound.

### ecom:24 (text-only, both 100% success)

- High: [10480, 10473, 10450, 10484, 10482] → avg=10,474
- Base: [10500, 10467, 10477, 10453, 10486] → avg=10,477
- **Δ = -3 (-0.0%)**

### ecom:23 (text-only, both 100% success)

- High: [29864, 29861, 29864, 29821, 29876] → avg=29,857
- Base: [29852, 29819, 29847, 29802, 29825] → avg=29,829
- **Δ = +28 (+0.1%)**

### ecom:26 (text-only, both 100% success)

- High: [44329, 43992, 44308, 44025, 43948] → avg=44,120
- Base: [43973, 23163, 23157, 23157, 44003] → avg=31,491
- **Δ = +12,630 (+40.1%)**

### admin:4 (text-only, high=80% base=100%)

- High: [143725, 130427, 69097, 130534, 68912] → avg=108,539
- Base: [102027, 130269, 117776, 68778, 116653] → avg=107,101
- **Δ = +1,438 (+1.3%)**

### ISSUE-BR-4 Verdict

Average high-base token delta (100% success tasks): +4,218
🟡 **MODERATE:** Some token inflation detected. May be legitimate ARIA additions.
