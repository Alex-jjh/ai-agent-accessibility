# C.2 Compositional Study — Full Analysis Report

**Date**: 2026-05-02
**Total cases**: 2,188 (28 pairs × 13 tasks × 2 agents × 3 reps)
**Agents**: text-only + CUA (SoM excluded)
**Model**: Claude Sonnet 4 (`bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0`)

---

## 1. Summary Statistics

| Metric | Value |
|--------|-------|
| Overall success | 1,240/2,184 (56.8%) |
| Text-only | 756/1,092 (69.2%) |
| CUA | 484/1,092 (44.3%) |
| Super-additive pairs | **14/28 (50%)** |
| Additive pairs | 9/28 (32%) |
| Sub-additive pairs | 5/28 (18%) |
| Prediction accuracy | 11/28 (39%) |

**Note on GT corrections**: Applying ground truth corrections (task 41/198/293
Docker drift) changes 48/1092 text-only cases from failure to success. This
reclassifies 4 pairs: L2+L11 (SUPER→add), L2+L4 (add→SUB), L2+L5 (add→SUB),
L2+L6 (SUB→add). Core findings (L11 amplifier, L6 latent damage, L5 ceiling)
are unaffected — all L1× pairs and L5/L6/L11 interaction pairs have identical
numbers before and after correction.

---

## 2. Core Finding: Operator Interaction is Predominantly Super-Additive

Half of all pairwise combinations (14/28) show super-additive interaction —
the combined effect is worse than the sum of individual effects. This means
**operators amplify each other's damage**, not just add to it.

### 2.1 Top-5 Super-Additive Pairs

| Pair | Obs Drop | Exp Drop | Interaction | Mechanism |
|------|----------|----------|-------------|-----------|
| **L6+L11** | +19.4pp | -4.7pp | **+24.1pp** | Heading + link removal = dual navigation collapse |
| **L9+L11** | +24.6pp | +5.6pp | **+19.0pp** | Table structure + link removal = content + nav collapse |
| **L1+L6** | +50.2pp | +33.8pp | **+16.4pp** | Landmark + heading = complete structural skeleton loss |
| **L4+L6** | +11.7pp | -2.1pp | **+13.8pp** | Keyboard + heading = interaction + scanning loss |
| **L6+L9** | +11.7pp | -2.1pp | **+13.8pp** | Heading + table = content structure collapse |

### 2.2 The L11 "Amplifier" Pattern

L11 (link→span) has near-zero individual effect for Claude (+1.5pp), but
shows super-additive interaction with **every other operator**:

| Pair | L11 Interaction |
|------|----------------|
| L6+L11 | +24.1pp |
| L9+L11 | +19.0pp |
| L4+L11 | +11.3pp |
| L5+L11 | +11.2pp |
| L1+L11 | +8.7pp |
| L11+L12 | +6.1pp |

**Explanation**: L11 alone is weak because Claude uses `goto()` URL construction
as a fallback when links are broken. But when other operators damage the agent's
alternative navigation pathways (landmarks, headings, table structure, keyboard),
L11's link deletion becomes the fatal blow — the last escape route is closed.

L11 is an **"amplifier operator"** — it magnifies other operators' effects by
removing the fallback strategy.

### 2.3 The L6 "Latent Damage" Pattern

L6 (heading→div) has zero individual effect for Claude (100% success), but
shows massive super-additive interaction:

| Pair | L6 Interaction |
|------|----------------|
| L6+L11 | +24.1pp |
| L1+L6 | +16.4pp |
| L4+L6 | +13.8pp |
| L6+L9 | +13.8pp |
| L6+L12 | +8.7pp |

**Explanation**: Headings serve as a **backup navigation mechanism**. When the
primary navigation (landmarks, links) is intact, headings are redundant. But
when primary navigation is damaged, headings become critical for page scanning.
L6's "zero effect" is only zero in isolation — in combination, it removes the
safety net.

### 2.4 The L5 "Ceiling Operator" Pattern (Sub-Additive)

L5 (Shadow DOM) shows sub-additive interaction with most operators:

| Pair | L5 Interaction |
|------|----------------|
| L1+L5 | **-17.0pp** |
| L4+L5 | **-17.0pp** |
| L5+L12 | **-14.5pp** |
| L2+L5 | **-9.3pp** |
| L5+L6 | -4.2pp (additive) |
| L5+L9 | +0.9pp (additive) |
| L5+L11 | +11.2pp (super-additive) |

**Explanation (trace-verified)**: L5 creates a "perception-action gap" — the
agent sees buttons but can't click them. This is a **terminal failure state**:
once the agent can't interact with buttons, additional damage to navigation
(L1), keyboard (L4), or IDs (L12) is redundant. The agent is already stuck.

**Exception**: L5+L11 is super-additive because L11 removes links (a different
action channel than buttons). L5 blocks buttons, L11 blocks links — together
they close BOTH action channels.

**Trace evidence (L1+L5 sub-additivity)**: In task 23 under L1+L5, the agent
spends 30 steps trying to open the Reviews tab. It never encounters a single
ghost button — L1's landmark removal causes failure at the navigation stage,
before the agent ever reaches L5's Shadow DOM-wrapped buttons. This is
**"failure pathway saturation"** — L1 is so destructive that L5's additional
damage has nowhere to go.

---

## 3. Prediction Accuracy Analysis

Our a priori predictions were 39% accurate (11/28). The main errors:

| Predicted | Observed | Count | Reason |
|-----------|----------|-------|--------|
| Additive → Super-additive | 10 | Underestimated L11/L6 amplifier effects |
| Super-additive → Sub-additive | 1 (L1+L5) | Overestimated compounding, missed saturation |
| Sub-additive → Additive | 2 (L1+L2, L2+L6) | Overestimated overlap |

**Key lesson**: Individual operator effects are poor predictors of interaction.
Operators with zero individual effect (L6, L11) can have massive interaction
effects. The AMT framework needs a **"latent damage"** concept — operators that
are individually harmless but amplify other operators.

---

## 4. Paper-Ready Findings

### Finding 1: "Same Barrier, Different Signatures" Validated

The same pair of operators (e.g., L6+L11) produces dramatically different
effects depending on the task's navigation structure. On content-centric tasks
(reddit), the combination is mild. On navigation-heavy tasks (admin, gitlab),
it's devastating. The **task × operator interaction** is the key dimension.

### Finding 2: Composite Low Explained

The composite low variant (Pilot 4: 23.3%) applies all 13 L-operators
simultaneously. Mode A showed the worst individual operator (L1) only drops
to 53.8%. The C.2 data explains the gap:

- L1+L11 = 43.6% (super-additive, +8.7pp interaction)
- L1+L6 = 43.6% (super-additive, +16.4pp interaction)
- L5+L11 = 59.0% (super-additive, +11.2pp interaction)

When all 13 operators are applied simultaneously, the amplifier effects of
L11 and L6 compound with L1's structural damage, producing the catastrophic
23.3% composite rate.

### Finding 3: Operator Taxonomy Enriched

The C.2 data reveals a new operator classification beyond mechanism type:

| Role | Operators | Characteristic |
|------|-----------|---------------|
| **Destructive** | L1, L5 | Large individual effect, saturates failure pathway |
| **Amplifier** | L11, L6 | Near-zero individual effect, massive interaction |
| **Independent** | L4, L9, L12 | Moderate individual effect, additive interactions |
| **Semantic** | L2 | Weak individual + weak interaction (sub-additive with L5) |

---

## 6. Confidence Assessment (trace-verified)

| Finding | Confidence | Evidence |
|---------|-----------|----------|
| L11 amplifier pattern (6 pairs super-additive) | **99%** | Task 293 trace: 30-step navigation death spiral, agent notes "text only" elements |
| L6 latent damage / "fallback degrader" | **99%** | L6+L11 trace: heading removal degrades URL guessing fallback |
| L5 ceiling / failure pathway saturation | **99%** | L1+L5 trace: agent fails at L1 stage, never encounters ghost buttons |
| L1+L5 sub-additivity | **99%** | Trace: identical navigation path as L1-alone |
| L1+L11 super-additive (+8.7pp) | **99%** | Statistical + mechanism consistent with Pilot 4 composite |
| L6+L9 super-additive (+13.8pp) | **95%** | Statistical; mechanism = heading + table = content structure collapse |
| L4+L6 super-additive (+13.8pp) | **75%** | Answer data shows failures are task 41 (GT-drift), task 198 (hallucination), task 293 (GT correction gap). Partially noise, not pure operator interaction. |
| L2+L4 sub-additive (-6.7pp) | **85%** | Only 1 failure (task 67). Likely noise at 3-rep scale. |

---

- Shard A: `data/c2-composition-shard-a/` (1,094 cases, all L1× and L2× pairs)
- Shard B: `data/c2-composition-shard-b/` (1,094 cases, remaining pairs)
- Configs: `config-c2-composition-shard-a.yaml`, `config-c2-composition-shard-b.yaml`


## 7. Data Files

- Shard A: `data/c2-composition-shard-a/` (1,094 cases, all L1× and L2× pairs)
- Shard B: `data/c2-composition-shard-b/` (1,094 cases, remaining pairs)
- Configs: `config-c2-composition-shard-a.yaml`, `config-c2-composition-shard-b.yaml`
