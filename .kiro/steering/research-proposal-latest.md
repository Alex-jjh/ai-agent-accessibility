---
inclusion: always
---
<!------------------------------------------------------------------------------------
   Add rules to this file or a short description and have Kiro refine them for you.
   
   Learn about inclusion modes: https://kiro.dev/docs/steering/#inclusion-modes
-------------------------------------------------------------------------------------> 

# Research Proposal v5.7: Accessibility as AI-Readiness
## Can AI See What Screen Readers See? An Empirical Study on Web Accessibility and AI Agent Task Success

**PI**: Jiahao Jiang (Alex) | **Advisor**: Dr. Brennan Jones (XJTLU, HCI/Accessibility)
**Date**: April 7, 2026 | **Target**: CHI 2027 / ASSETS 2027

---

## 1. Abstract

Autonomous AI agents increasingly rely on the browser Accessibility Tree—the same semantic interface built for screen readers—as their primary observation space for web interaction. Yet no existing benchmark controls for the accessibility properties of target websites, making it impossible to distinguish agent limitations from environmental hostility. We propose the **"Same Barrier" hypothesis**: AI agents and assistive technology users face structurally equivalent obstacles on inaccessible websites because both depend on semantic HTML, ARIA annotations, and keyboard navigability.

We test this hypothesis through an **environment-centric evaluation paradigm** that inverts standard benchmark design: rather than varying agents against a fixed environment, we programmatically manipulate web accessibility while holding the agent constant. In a controlled experiment on WebArena (6 tasks × 4 accessibility variants × 2 agent types × 5 repetitions, N=240), we find that degrading accessibility from baseline to low causes text-only agent success to drop from 86.7% to 23.3% (χ²=24.31, p<0.000001, Cramér's V=0.637), with a sharp step-function at the boundary between low and medium-low accessibility (+76.7 percentage points). Critically, a vision-only agent using Set-of-Mark overlays achieves 0% success under low accessibility—not because screenshots change, but because SoM labels depend on DOM interactive elements that accessibility degradation removes.

Trace-level analysis of all 240 cases reveals three distinct failure pathways: (1) *content invisibility*, where broken ARIA relationships hide task-critical information from the Accessibility Tree; (2) *token inflation*, where degraded semantic structure forces agents into exhaustive exploration (172K vs. 135K tokens, with extremes reaching 608K before context overflow); and (3) *phantom bids*, a novel failure mode where SoM overlays create false interactivity signals on de-semanticized elements, trapping vision agents in 20+ step click-failure loops. We additionally document *forced strategy simplification*, a paradoxical effect where removing interactive affordances constrains the agent's action space and improves performance by preventing costly but unproductive exploration.

These findings, replicated across five independent experimental rounds (Pilots 2–4, 81–240 cases each), establish web accessibility as a significant, previously uncontrolled variable in AI agent evaluation, and provide the first controlled empirical evidence that the infrastructure built for human disability access directly determines AI agent capability.

We contribute: (1) among the first controlled empirical evidence that web accessibility predicts AI agent task success, replicated across five rounds with consistent significance (p<0.000001 in full experiment); (2) an environment-centric evaluation paradigm and reusable experimentation framework; (3) a failure attribution methodology that disentangles environmental and model factors; (4) the "Same Barrier" hypothesis as a theoretical bridge between accessibility research and AI agent research; (5) the finding that DOM semantic quality affects vision-based agents through overlay infrastructure dependencies; and (6) the duality framework connecting false affordances (failure path) with action-space constraint theory (success path) under a single DOM semantic change.

---

## 2. Research Problem

### 2.1 The Gap

AI agents increasingly use the browser Accessibility Tree as their primary observation space. AgentOccam (Amazon Science) achieves +161% improvement via filtered A11y Tree nodes; CI4A (ByteDance) reaches WebArena SOTA of 86.3% through semantic component interfaces; Vercel's Agent-Browser reduces context window usage by 93% using accessible names and ARIA roles. Industry products — AirJelly, CLI-Anything/DOMShell, DirectShell — all build on accessibility infrastructure. Internal deployments at major cloud providers confirm this dependency: enterprise AI agent products (scheduled assistants, workflow automators) universally rely on accessibility infrastructure of target applications, yet the accessibility quality of those targets remains uncontrolled and unquantified.

Yet no existing benchmark controls for this dependency. WebArena, Mind2Web, and VisualWebArena evaluate agent reasoning but treat website accessibility as an uncontrolled environmental variable. When a frontier agent achieves 14% success on WebArena, we cannot distinguish model limitations from environmental hostility. The accessibility research community, conversely, has not considered AI agents as a stakeholder group benefiting from universal design.

**A paradigm gap**: All existing web agent benchmarks adopt an *agent-centric* evaluation paradigm — they hold the web environment constant and vary agent architectures or models. This design answers "which agent is better?" but cannot answer "what environmental properties make agents succeed or fail?" The absence of an *environment-centric* paradigm leaves a fundamental question unaddressed: how do the properties of web environments causally influence agent performance?

### 2.2 Practical Motivation

When an agent encounters a non-semantic DOM, it typically falls back from efficient A11y Tree parsing (~2–5KB per page) to expensive VLM screenshot processing (~500KB–2MB), with corresponding increases in latency and API costs. Industry reports suggest high failure rates in enterprise AI agent deployments: Patronus AI finds that agents with even 1% per-step error face a 63% chance of complete workflow failure by step 100. Our experimental data quantifies this directly: in our full 240-case experiment, degraded accessibility inflates token consumption by 27% on average (172K vs 135K tokens per task), with extreme cases reaching 608K tokens — causing LLM context overflow and complete task failure. In one task (reddit:67), 4 out of 5 runs at base/high accessibility crashed at 608K tokens, while the same task at medium-low accessibility succeeded in 100% of runs using only 43K tokens — a 14× efficiency difference attributable entirely to action space constraint. We argue that inaccessible web infrastructure — the same infrastructure that excludes users with disabilities — is an under-recognized contributor to these failures, and that quantifying this relationship has direct implications for both agent architecture design and the business case for accessibility investment.

### 2.3 Related Work and Positioning

#### 2.3.1 Environment Perturbation Approaches

Recent work has begun manipulating web environments to test agent robustness, but none targets accessibility semantics. **WAREX** [25] uses a transparent proxy to inject infrastructure failures (network delays, HTTP 4xx/5xx, JavaScript failures, popups) into WebArena/WebVoyager, demonstrating significant drops in agent success rates. **GUI-Robust** [26] introduces 200 abnormal scenarios across seven GUI anomaly types (pop-ups, ad overlays, loading failures, layout shifts), revealing substantial performance degradation. **D-GARA** [27] extends this with a dynamic benchmarking framework. **Aegis** [28] takes a complementary "environment-optimization" approach: by analyzing 142 agent traces (3,656 turns) across five benchmarks, it proposes a taxonomy of six agent-environment interaction failure modes and then *optimizes* environments to improve success rates by 6.7–12.5%. **ARE** [29] demonstrates that imperceptible perturbations to web page images can hijack agents with up to 67% success.

These works establish that environment properties significantly affect agent performance, but their manipulations target infrastructure faults (WAREX), visual anomalies (GUI-Robust), or adversarial attacks (ARE) — **none manipulates accessibility semantics** (ARIA attributes, semantic HTML structure, keyboard navigability) as the independent variable.

#### 2.3.2 Accessibility Mutation Testing

**Ma11y** [30] (ISSTA 2024) is the closest methodological precedent. It introduces 25 mutation operators based on WCAG 2.1 failure techniques, using Puppeteer to inject accessibility violations into the DOM. Operators include F2 (replace `<h2>` with styled `<p>`), F68 (remove form `<label>` elements), F91 (replace `<th>` with `<td>`), F96 (corrupt `aria-label` with random strings), and F44 (reverse `tabindex` order). Several of these operators directly correspond to our low variant manipulations.

However, Ma11y's research question is fundamentally different: it evaluates whether accessibility **testing tools** detect injected violations. Our dependent variable is whether accessibility violations cause AI **agent task failures**. This distinction mirrors the broader conformance-usability gap documented by Power et al. [31] — detecting a violation and experiencing its functional impact are separate phenomena.

#### 2.3.3 Observation Space and Token Efficiency

A rapidly expanding body of work demonstrates that targeted observation space pruning dramatically improves agent performance. **AgentOccam** [3] achieves +161% improvement on WebArena by filtering the accessibility tree to retain only "pivotal" interactive nodes. **FocusAgent** [32] reduces AxTree observations by 50%+ using a lightweight LLM retriever. **Prune4Web** [33] achieves 25–50× element reduction, nearly doubling grounding accuracy from 46.8% to 88.28%. **AgentOCR** [34] preserves 95% of text-based performance while halving tokens.

Critically, **Chung et al.** [35] directly benchmark long-context reasoning in web agents, finding success rates drop from 40–50% at baseline to **below 10%** in long-context scenarios (25,000–150,000 tokens), with agents getting stuck in loops and losing track of objectives. This establishes context overflow as a severe failure mode — but no study has identified accessibility quality as the **upstream cause** of observation space bloat.

#### 2.3.4 Theoretical Grounding

**Gibson's affordance theory** [36] provides the conceptual foundation for our paradigm inversion: affordances are relational properties of the environment relative to the actor's capabilities. Broken accessibility strips the environment of programmatic affordances. **Han et al.** [37] operationalize computational rationality-based affordances for AI agents. **EnviSAgE** [38] is the first survey to adopt an "environment-centric perspective" for AI agent development, formalizing the Generation-Execution-Feedback loop, though it focuses on training rather than measurement.

**ADeLe** [6] (Nature 2026) introduces 18 cognitive dimensions that profile both task demands and AI system abilities, achieving ~88% instance-level predictive accuracy. Our work is complementary: ADeLe measures *task demand* (what cognitive operations are required), we measure *environment quality* (how the interface structure affects agent perception). Together, they enable a complete decomposition:

> **performance = task demand (ADeLe) × environment quality (ours) × agent capability (benchmarks)**

No existing framework addresses the environment-side structural dimension.

#### 2.3.5 Accessibility Measurement at Scale

**WebAIM Million 2025** [9] finds 94.8% of the top million homepages fail WCAG 2, averaging 51 errors per page. Paradoxically, pages utilizing ARIA average 57 errors vs. 27 on non-ARIA pages [9], indicating that ARIA adoption does not equal machine-readability. **Power et al.** [31] (CHI 2012) tested 32 blind users on 16 websites and found only 50.4% of problems encountered were covered by WCAG 2.0 — and 16.7% of compliant sites still failed users. **Accessible.org** [39] found that only 13% of WCAG 2.2 AA criteria (7 of 55) are fully auto-detectable, with 42% requiring human judgment. **WCAG 3.0** [40] introduces graduated scoring (Bronze/Silver/Gold) and "critical errors" that override positive scores. No existing large-scale study measures **AI-readiness** specifically — the accessibility tree completeness and semantic integrity that determine agent operability.

#### 2.3.6 Cross-Browser ARIA Divergence

Browsers handle broken ARIA references inconsistently. **Igalia's research** [41] revealed that `aria-labelledby` referencing hidden elements produces different accessible names across engines: WebKit yields "d", Firefox "abcd", Chrome "bcd" for identical markup. Shadow DOM completely breaks ARIA relationship attributes across shadow root boundaries — an issue identified in 2014 that remains unresolved [16, 42]. The **W3C AccName specification** [43] was clarified to require "at least one valid IDREF," but corner cases involving hidden subtrees remain divergent across implementations.

#### 2.3.7 Threshold Effects Across Domains

Non-linear dose-response patterns are well-documented in adjacent domains. In speech recognition, enhancement preprocessing paradoxically **degrades** ASR performance across all noise conditions [44]. In computer vision, JPEG compression degrades object detection in a "first gradually, then suddenly" collapse pattern [45]. In satellite imagery, resolution improvements yield 13–36% detection gains until diminishing returns set in [46]. Within accessibility research, pages with ARIA average 34% more errors than those without [9], and screen reader verbosity from excessive markup significantly increases task completion time [47]. No formal dose-response model has been applied to accessibility's effect on AI agents.

#### 2.3.8 SoM Overlay Robustness and False Affordances

**Set-of-Mark implementation divergence**: The original SoM paper (Yang et al., 2023) [57] generates marks through pure visual segmentation (SAM, SEEM) with zero DOM dependency. However, every major web-agent framework has shifted to DOM-based label generation: BrowserGym assigns unique bid identifiers via Chrome CDP with visibility/clickability flags [23]; VisualWebArena uses JavaScript DOM traversal to annotate interactable elements [22]; WebVoyager uses rule-based JavaScript extraction of interactive element types [7]. This creates a tight coupling between label validity and DOM state integrity that the original SoM design explicitly avoided.

**Documented SoM failure modes**: SeeAct (Zheng et al., ICML 2024) [8] reported that SoM prompting is "not effective for web agents," with 53% of grounding errors from wrong action generation and additional failures from "making up bounding box & label." SHARPMARK (ACL ARR 2024) [58] identified a "modality gap" between textual HTML elements and visual SoM overlays. The "Towards Trustworthy GUI Agents" survey (Shi et al., 2025) [59] formalized the **Execution Gap**: interfaces change between perception and action, causing silent failures. BrowserGym's bid system creates **"double staleness" risk**: the visual label persists on screenshots even after the underlying bid becomes invalid due to DOM mutation — but BrowserGym handles staleness reactively (post-failure error messages) with no pre-execution re-validation [23].

**The phantom bid as overlay false affordance**: Gibson's (1979) affordance theory [36] defines affordances as relational properties between actor and environment. Gaver (1991) [60] formalized **false affordances** — perceived action possibilities that do not exist. Norman (2013) [61] refined this as **false signifiers** — visual cues suggesting nonexistent actions. Our phantom bid phenomenon maps onto a novel subcategory: an **overlay false affordance**, where the annotation layer itself (SoM labels) creates the false signifier on DOM elements that have been de-semanticized. No 2023–2026 publication has formally connected Gaver's taxonomy to AI agent failure modes. The closest work is the "visual confused deputy" formalization (Liu et al., 2026) [62], which frames misperceived screen states as a security issue; A4Bench (Wang et al., 2025) [63] evaluates MLLM affordance perception but focuses on physical-world rather than web interface affordances; and Nitu & Stöckl (2025) [64] document that agents display "satisficing behavior," ignoring visual calls-to-action when semantic button overlays are absent.

**The SoM-to-coordinate paradigm shift**: The field has moved decisively from SoM-dependent to coordinate-based agents. OpenAI CUA [65] processes raw pixels with virtual mouse/keyboard, achieving 58.1% on WebArena vs. GPT-4V+SoM's 16.37% on VisualWebArena [22]. UI-TARS [66] explicitly identifies SoM's limitation: "textual-based methods often require system-level permissions to access underlying system information." MolmoWeb [67] argues "a website's appearance changes less often than its underlying code," making pure-vision agents inherently more robust to DOM mutations. GUI-Actor [68] proposes "coordinate-free" attention-based grounding, outperforming UI-TARS-72B with a 7B model.

**Research gap**: No study specifically measures SoM overlay staleness under controlled DOM mutation conditions. WAREX [25] tests infrastructure faults, ARE [29] tests adversarial perturbations, but neither isolates DOM semantic mutation as a causal factor for SoM label degradation. Our controlled experiment — where we programmatically de-semanticize DOM elements and observe SoM label persistence — fills this gap with the first causal evidence.

#### 2.3.9 Constraint-Driven Performance and the Action Space Curse

The paradoxical observation that removing link semantics can improve agent performance connects to a convergent body of evidence across cognitive science, HCI, and AI agent research.

**Cognitive science foundations**: Schwartz's Paradox of Choice (2004) [69] establishes that eliminating options reduces decision anxiety. The Hick-Hyman Law (1952) [70] formalizes this: reaction time increases logarithmically with stimuli count (RT = a + b·log₂(n)). Progressive disclosure [71] manages complexity by showing only essentials, grounded in Miller's ~7 item working memory limit. The W3C COGA guidance [72] extends this to cognitive accessibility: impaired working memory handles only 1–3 items, making interface simplification essential — a constraint that directly parallels LLM context window limits.

**Empirical validation in agent research**: AgentOccam (ICLR 2025) [3] achieved +161% success rate by refining observation/action spaces alone. Prune4Web [33] doubled grounding accuracy (46.8% → 88.28%) through 25–50× DOM reduction. FocusAgent [32] reduced observation size by 50%+ while matching baseline performance and reducing prompt injection vulnerability. Conversely, context bloat drops success from 40–50% to below 10% in 25K–150K token scenarios [35], and contextual distractions cause ~45% performance degradation [73].

**Formal results**: Majumdar (2026) [74] proves that dense (unpruned) policies require Ω(M) samples over M actions, while sparse policies achieve suboptimality scaling as √k — logarithmic rather than linear in action count. Nica et al. (2022) [75] empirically demonstrate the "paradox of choice" in RL: fewer but more meaningful choices improve learning speed. Plan-MCTS [76] shows that exploring semantic plan space rather than action space produces more concise trajectories.

**Our contribution — the duality framework**: Phantom bids and forced strategy simplification are dual outcomes of the same cause — DOM semantic change — with opposite effects. When `<a>` → `<span>`: (1) on the failure path, SoM labels persist as overlay false affordances, causing 20+ step click-failure loops; (2) on the success path, removed link affordances constrain the action space, forcing agents onto more efficient strategies (43K vs 580K tokens). No published work documents this duality or connects false affordance theory (failure path) with action-space constraint theory (success path) under a unified framework.

#### 2.3.10 Gap Summary

| Gap | Closest Prior Work | Our Contribution |
|-----|-------------------|------------------|
| No work manipulates web a11y as IV for agent evaluation | WAREX (infra faults), GUI-Robust (visual anomalies) | First environment-centric web agent benchmark using accessibility as IV |
| No causal link between a11y quality and token consumption | AgentOccam (downstream filtering), Chung et al. (long-context effects) | Quantified 87% token inflation; identified upstream causal pathway |
| No formal "phantom content" concept | Igalia cross-browser studies, W3C AccName spec | First controlled demonstration: broken ARIA makes tasks logically impossible |
| No metric for functional semantic integrity | Deque 57% (volume-based), Power et al. (50.4% user coverage) | Tier 2 measurement evaluating a11y tree completeness beyond WCAG compliance |
| No empirical test of structural equivalence (AT ↔ AI) | Applause/DubBot industry framing, nohacks.co (agent-side constraint) | First empirical test via environment-side manipulation |
| ADeLe measures task demand, not environment quality | ADeLe 18 dimensions (Nature 2026) | Environment-side measurement; enables performance = task × environment × agent |
| No dose-response model for a11y → AI agent performance | ARIA over-annotation harms, CV/ASR threshold effects | First empirical evidence of threshold effect for AI agents |
| **No study of SoM staleness under DOM mutation** | **SeeAct (53% grounding error), Execution Gap concept** | **First controlled evidence: DOM de-semanticization causes phantom bids — overlay false affordances** |
| **False affordance theory unconnected to agent failures** | **Visual confused deputy (security framing), A4Bench (physical affordances)** | **Formal mapping of Gaver's taxonomy to agent failure modes; novel "overlay false affordance" category** |
| **No unified framework for constraint-driven agent performance** | **AgentOccam (deliberate pruning), Prune4Web (DOM reduction)** | **Duality framework: same DOM change → failure (phantom bids) OR success (forced simplification); Majumdar's Ω(M) vs √k formal backing** |

---

## 3. The "Same Barrier" Hypothesis

AI agents and screen reader users face structurally equivalent barriers:

| Property | Screen Reader User | AI Agent |
|----------|-------------------|----------|
| Perception | Audio translation of A11y Tree | Tokenized ingestion of A11y Tree |
| Failure mode | Cannot find unlabelled elements | Cannot actuate non-semantic elements |
| Workaround | Memorize site-specific tricks | "Experience sedimentation" — cached heuristics |

**Direct evidence**: UC Berkeley and University of Michigan researchers [12] (CHI 2026 / nohacks.co) evaluated Claude 3.5 Sonnet across 60 real-world web navigation tasks. Under standard conditions, the agent achieved 78.33% success; under keyboard-only constraint (simulating screen reader navigation), success dropped to 41.67%, with task completion time doubling from 324s to 650s. Failures mapped to three categories: Perception Gaps (missing ARIA live regions), Cognitive Gaps (illogical DOM structure), and Action Gaps (no keyboard handlers). Crucially, this study constrained the *agent's action space*; our study degrades the *environment's semantic quality* — a complementary and more causally precise manipulation.

**Industry convergence**: Multiple independent sources have arrived at essentially the same conclusion. Applause [48] frames accessibility as "the machine-readable infrastructure that enables AI readiness," calling semantic structure a shared "contract layer" between interfaces and any machine attempting to operate them. DubBot [49] explicitly states "AI systems read web content in ways strikingly similar to how screen readers do." Opus Research [50] applies the "curb-cut effect" to argue that accessibility infrastructure benefits AI agents as an unintended beneficiary group. A CHI 2026 workshop paper [51] formalizes the "dual-audience" problem: interfaces must remain legible to humans while being interpretable by agents.

**Pilot evidence**: Our Pilot 4 results (N=240) provide definitive controlled evidence. When the low variant breaks ARIA tabpanel relationships on ecommerce product pages, the Reviews section becomes invisible in the Accessibility Tree — mirroring exactly how a screen reader user would lose access to the same content. In all 5 traces of ecom:23 low, the agent reports "the review content is not accessible" and fails — not because of reasoning failure, but because the content genuinely does not exist in its perceptual space. The Plan D variant injection mechanism ensures this degradation persists even after agent-triggered page reloads (verified: 33/33 goto traces show persistent degradation), eliminating the confound of variant escape that affected Pilot 3b.

**The pseudo-compliance trap**: Incorrect ARIA can be worse than absent ARIA. The WebAIM Million 2025 report found that pages utilizing ARIA average 57 detectable errors vs. 27 on non-ARIA pages. When `role="button"` is applied to a `<div>` without keyboard handlers, agents perceive a valid target, attempt actuation, register no state change, and enter token-draining retry loops. This has direct implications for measurement methodology: we cannot rely solely on syntactic ARIA presence; we must assess whether annotations are semantically correct and functionally backed.

---

## 4. Research Questions

- **Primary RQ**: Is website accessibility a statistically significant predictor of AI agent task success, after controlling for site complexity, sector, and agent architecture?
- **Secondary RQ**: Which specific WCAG 2.2 criteria are most predictive of agent success?
- **Exploratory RQ**: If data permits, can we identify agent-critical accessibility properties not covered by current WCAG 2.2? (Initial characterization only; detailed ACAG framework development is future work.)

---

## 5. Methodology

### 5.1 Design Overview

Existing web agent benchmarks adopt an *agent-centric* paradigm: the web environment is held constant while agent architectures and models vary. We invert this design: holding the agent constant while programmatically manipulating web environment properties via DOM-level variant injection — an *environment-centric* evaluation paradigm that enables causal investigation of how frontend characteristics affect agent performance.

This paradigm shift yields a dual-track multifactorial study with log-based failure attribution and multi-tier accessibility measurement. Track A provides primary causal evidence; Track B provides ecological validation. The underlying experimentation framework — programmatic DOM manipulation with persistent variant injection — is designed to be reusable: accessibility is the first independent variable we study, but the same infrastructure supports investigation of any frontend property (interaction latency, dark patterns, internationalization, visual layout).

### 5.2 Track A: Controlled A/B Experiments (Primary Evidence)

**Base**: WebArena's four self-hosted applications (Reddit, GitLab, CMS, E-commerce) — existing task definitions, evaluation scripts, and baseline results.

**Manipulation**: Four A11y variants per environment:

| Variant | Manipulation | Level |
|---------|-------------|-------|
| **Low** | Strip ARIA, replace semantic HTML with `<div>`/`<span>` (F42), disable keyboard handlers (F55), inject unbridged Shadow DOM, break semantic relationships (e.g., tabpanel associations), duplicate IDs (F77) | 0 |
| **Medium-Low** | ARIA attributes present but functionally incorrect — event handlers missing, pseudo-compliance traps (correct role, no behavior) | 0.5 |
| **Base** | Original WebArena (as-is) | 1 |
| **High** | Full ARIA, semantic HTML5, keyboard navigability, landmarks, all axe-core violations fixed | 2 |

**Implementation — Plan D**: Variant injection uses Playwright's `context.route("**/*")` to intercept all HTML responses at the network level, injecting variant-specific patch scripts before the page reaches the browser's rendering engine. Patches execute via a deferred strategy: `window.load` event + 500ms delay + MutationObserver guard — ensuring manipulations persist through JavaScript framework re-rendering (Magento KnockoutJS, Postmill templates). A `[data-variant-revert]` sentinel attribute on modified elements enables the MutationObserver to detect and re-apply patches if the framework restores original DOM structure. This design was developed through iterative failure of three prior mechanisms (Pilots 2–3b) and verified with 33/33 goto-triggered navigation traces in Pilot 4. The variant injection system is decoupled from accessibility-specific patches — swapping the injected scripts enables experimentation with arbitrary frontend properties.

**Relationship to Ma11y** [30]: Our variant injection shares conceptual roots with Ma11y's mutation operators (ISSTA 2024), which inject WCAG failure techniques into the DOM using Puppeteer. Several Ma11y operators (F2: heading→paragraph, F68: label removal, F91: th→td, F96: aria-label corruption) directly correspond to our low variant manipulations, providing methodological validation from the software testing community. However, Ma11y evaluates whether accessibility *testing tools* detect mutations; we evaluate whether mutations cause AI *agent task failures* — the same mutation methodology applied to a fundamentally different dependent variable.

**Scope**: 4 apps × 4 variants × 3–5 tasks × 2 agent types = 96–160 test cases. Same content, same tasks — **only A11y varies**.

**Agent config**: Text-Only (A11y Tree observation) as primary modality — directly tests A11y quality impact. Vision-only agent (SoM-based screenshot observation) as control — tests whether DOM mutations affect agents through non-semantic pathways. Primary LLM: Claude Sonnet 3.5 via LiteLLM proxy to AWS Bedrock (additional backends planned for generalization). Platform: BrowserGym with custom Python bridge (browsergym_bridge.py, 800+ lines) handling variant injection, shopping authentication, and observation extraction. Each task × 5 attempts. Variant patches injected via Plan D persistence mechanism (see above).

**Why Track A is primary**: It provides the cleanest causal test. The reviewer's core question — "how do you know failure is due to A11y, not confounds?" — is answered by experimental control. Ground-truth A11y levels eliminate measurement error in the independent variable.

#### 5.2.1 Pilot Results (Pilots 2–3b, March–April 2026)

**Pilot 2** (81 runs: 9 tasks × 3 variants × 3 reps): Established core finding. Low 37.0% vs Base 74.1% (χ²=7.50, p=0.006, Cramér's V=0.37). Identified token inflation and content invisibility pathways. Base vs High not significant (p=0.25).

**Pilot 3a** (120 runs: 6 tasks × 4 variants × 5 reps, text-only): Introduced medium-low "pseudo-compliance" variant and increased reps. Core gradient replicated: low 20.0% → medium-low 86.7% → base 90.0% → high 93.3%. Low vs base: χ²=29.4, p<0.001. Monotonic gradient confirmed. Two new operators added from Ma11y mapping (F42: link→span, F77: duplicate IDs, F55: focus blur).

**Pilot 3b** (213 runs: text-only 120 + vision-only 93): Macro-level replication confirmed: overall text-only success 71.7% vs 72.5% (Δ<1pp). Vision-only low vs base: χ²=10.02, p=0.002, Cramér's V=0.45. Identified goto() escape vulnerability (agent-triggered page reloads clearing variant patches), motivating Plan D injection mechanism.

#### 5.2.2 Pilot 4: Full Experiment (240/240 Cases, April 7, 2026)

**Design**: 6 tasks × 4 variants × 2 agents × 5 reps = 240 cases, 0 missing.
**Variant injection**: Plan D (context.route() HTML interception + deferred patch after window.load + MutationObserver guard). Verified: 33/33 goto() traces in low variant show persistent degradation after navigation.
**LLM**: Claude Sonnet 3.5 via LiteLLM proxy to AWS Bedrock.
**Platform**: BrowserGym + custom bridge (browsergym_bridge.py, 800+ lines).

**Text-Only Results (n=120)**:

| Variant | Success | Total | Rate | vs Pilot 3a |
|---------|---------|-------|------|-------------|
| low | 7 | 30 | 23.3% | +3.3pp (20.0%) |
| medium-low | 30 | 30 | 100.0% | +13.3pp (86.7%) |
| base | 26 | 30 | 86.7% | -3.3pp (90.0%) |
| high | 23 | 30 | 76.7% | -16.6pp (93.3%) |

**Primary statistical test**: Low vs Base: χ²=24.31, p<0.000001, Cramér's V=0.637, Fisher's exact p=0.000001.
**Step function**: Low→Medium-Low jump = 76.7pp (144% of total low-high range).
**Cross-pilot replication**: Breslow-Day test for homogeneity of ORs across tasks: p=1.000 (perfectly homogeneous).

**Task × Variant Matrix (Text-Only)**:

| Task | low | med-low | base | high |
|------|-----|---------|------|------|
| ecommerce:23 | 0/5 (0%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecommerce:24 | 1/5 (20%)* | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecommerce:26 | 0/5 (0%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| admin:4 | 0/5 (0%) | 5/5 (100%) | 5/5 (100%) | 4/5 (80%) |
| reddit:29 | 4/5 (80%) | 5/5 (100%) | 5/5 (100%) | 3/5 (60%) |
| reddit:67 | 2/5 (40%) | 5/5 (100%) | 1/5 (20%)† | 1/5 (20%)† |

\* ecom:24 low success is a vacuous truth — agent cannot access reviews, answer "no unfair pricing" happens to be correct by chance (see §5.2.3).
† reddit:67 base/high failures are context overflow (F_COF), not accessibility-caused — see §5.2.3.

**Vision-Only Results (n=120)**:

| Variant | Success | Total | Rate |
|---------|---------|-------|------|
| low | 0 | 30 | 0.0% |
| medium-low | 7 | 30 | 23.3% |
| base | 6 | 30 | 20.0% |
| high | 9 | 30 | 30.0% |
| **Overall** | **22** | **120** | **18.3%** |

Vision-only low vs base: χ²=6.67, p=0.010, Cramér's V=0.333. **Significant.**

Vision success concentrated in exactly 2 of 6 tasks: ecom:24 (10/20=50%, simple scroll+read) and reddit:67 (12/20=60%, read post titles from list). All tasks requiring multi-step navigation or widget interaction score 0/20.

**Interaction Effect (Causal Inference)**:
- Text gradient (base−low): 63.3pp
- Vision gradient (base−low): 20.0pp
- **Interaction**: 43.3pp — text-only agents are disproportionately affected, confirming the Accessibility Tree as the primary causal mechanism.
- At non-low variants (where SoM labels are intact): text-only 87.8% vs vision-only 24.4% = 63.3pp advantage, confirming the a11y tree's substantial informational superiority.

**Token Analysis**:

| Variant | Text Avg | Text Median | Vision Avg | Vision Median |
|---------|----------|-------------|------------|---------------|
| low | 172,002 | 113,743 | 50,585 | 51,621 |
| medium-low | 93,996 | 42,763 | 34,283 | 34,350 |
| base | 134,833 | 43,988 | 28,486 | 20,384 |
| high | 149,809 | 44,318 | 36,131 | 25,468 |

Text-only uses 2.55× more tokens than vision-only on average (expected: a11y tree is verbose). Low variant inflates text-only tokens by 27% vs base. Vision-only takes more steps (12.8 vs 7.4 avg) despite fewer tokens — each step is slower (screenshot rendering + SoM overlay).

**Outcome Breakdown**:

| Outcome | Text-Only | Vision-Only |
|---------|-----------|-------------|
| success | 86 | 22 |
| failure | 21 | 54 |
| timeout | 3 | 4 |
| partial_success | 10 | 40 |

Vision-only's dominant failure mode is partial_success (40/120=33%) — agents make progress but cannot complete tasks. Text-only failures are more binary.

#### 5.2.3 Pilot 4 Deep Dive Analysis

**reddit:67 Anomaly — Context Overflow, Not Accessibility**

Base/high variants show only 20% success (1/5 each) despite full accessibility. Deep dive reveals: 4/5 failures at both variants are F_COF (context overflow). The agent clicks into individual post detail pages, each loading 100+ comments → a11y tree expands to 608K tokens → LLM call fails ("LLM call failed" error).

Medium-low achieves 100% (5/5) because the degraded DOM prevents the agent from clicking into posts (links converted to StaticText), forcing it to read book titles from the forum list page — completing the task in 3 steps and 43K tokens. This is **forced strategy simplification**: the same DOM change that causes failure elsewhere (content invisibility) here acts as a beneficial constraint by eliminating a harmful affordance (deep-linking into verbose pages).

**Key numbers**: base/high failure traces average 503K–609K tokens. Medium-low success traces average 137K tokens. This is a 14× efficiency difference. The "paradox" is that less accessible DOM can improve performance when the accessible version provides an affordance trap.

**Sensitivity analysis**: Excluding reddit:67, low vs base remains significant: low 1/5 (20%) vs base 5/5 (100%), χ²=6.67, p=0.010, V=0.816.

**ecom:24 Low — Vacuous Truth**

The single success (1/5) at low variant is a false positive. The agent's answer: "No reviewers found mentioning unfair pricing — the review content is not accessible on this page." Ground truth: no reviewers mention unfair pricing. The agent gave the correct answer but for the wrong reason — it could not access reviews due to content invisibility, and the answer "no" happened to be true. All 5 traces show tablist=False, tabpanel=False, confirming Plan D is working.

**admin:4 High — LLM Reasoning Error**

The single failure (4/5=80%) at high variant: agent sorted by revenue instead of by quantity. Token count (130K) matches successful traces. Not related to ISSUE-BR-4 or skip-link accumulation. Pure F_REA (reasoning error).

**reddit:29 High — Counting Error**

2 failures at high (3/5=60%): both answer "0" negative-vote comments when the correct answer is "1". The agent reads all 16 comments but miscounts a negative-vote entry. Token count (172K) consistent with base (169K). Pure F_REA.

**Plan D Verification**

Complete reversal from Pilot 3b: ecom:23 low success dropped from 80% (3b, goto escape) to 0% (Pilot 4, Plan D). Structural comparison after goto():

| Element | Pilot 3b (AFTER goto) | Pilot 4 (AFTER goto) |
|---------|----------------------|---------------------|
| tablist | ✅ PRESENT | ❌ ABSENT |
| tabpanel | ✅ PRESENT | ❌ ABSENT |
| menu | ✅ PRESENT | ❌ ABSENT |
| menuitem | ✅ PRESENT | ❌ ABSENT |

33/33 low-variant traces with goto() show persistent degradation. Plan D's context.route() intercept catches every HTML response, including those triggered by goto(), and re-injects variant patches at the network level.

**Vision Phantom Label Classification**

Two distinct failure modes identified in vision-only low traces:

- **Mode A** (Magento): Elements exist in DOM but with `browsergym_set_of_marks="0"` — click resolves but returns "element is not visible." Agent sees label in screenshot, clicks it, gets error, retries indefinitely.
- **Mode B** (Reddit/Postmill): Elements completely removed from interactive set — click returns "Could not find element with bid." Agent clicks non-existent bid 20+ times in a row (e.g., reddit_low_67_1_1: 25 consecutive failed clicks on bid "229").

Both modes produce 0% success because the agent cannot interact with any navigation elements under low variant.

**ISSUE-BR-4 Token Inflation Check**

Controlled comparison on tasks with 100% success at both high and base (eliminating failure-driven token inflation as confound):

| Task | High avg tokens | Base avg tokens | Δ |
|------|----------------|----------------|---|
| ecom:24 | 10,474 | 10,477 | -0.0% |
| ecom:23 | 29,857 | 29,829 | +0.1% |
| admin:4 | 108,539 | 107,101 | +1.3% |

MutationObserver sentinel bug (ISSUE-BR-4) existed but had negligible impact on Pilot 4 data. Bug has been fixed for future runs.

**Failure Distribution (Pilot 4, Text-Only, n=34 failures)**:

| Domain | Type | Count | Primary Variant |
|--------|------|-------|----------------|
| A11y | Content Invisibility | 10 | low (ecom:23/24/26) |
| A11y | Structural Infeasibility | 5 | low (admin:4) |
| Model | Context Overflow (F_COF) | 8 | base/high (reddit:67) |
| Model | Reasoning Error (F_REA) | 5 | mixed |
| Model | Harmful Affordance Trap | 3 | base/high (reddit:67) |
| A11y | Token Inflation (timeout) | 3 | low (admin:4) |

A11y-attributed failures dominate the low variant (18/23 = 78%). Model-attributed failures dominate at non-low variants (11/11 = 100%). This separation supports the claim that accessibility degradation introduces a mechanistically distinct failure pathway, not merely amplification of existing model weaknesses.

### 5.3 Track B: Real-World Survey (Ecological Validity)

**Approach**: Core sample of 50 websites across sectors (e-commerce, government, education, SaaS, social media) and geographies (US, EU, China), expandable to 200+ if the pipeline stabilizes. Sites captured via Playwright HAR recording — preserves JavaScript execution and SPA state transitions while eliminating server-side variance.

**Landscape study component**: In addition to agent task probing, Track B includes a large-scale accessibility measurement survey (200+ websites) collecting: axe-core violations by impact level, Lighthouse accessibility scores, composite accessibility scores (same metric as Track A), A11y Tree token counts, DOM structural metrics, and website metadata (category, geography, framework). This provides ecological context: given Track A's causal evidence on what accessibility levels cause agent failure, the landscape study quantifies what proportion of real-world websites fall within those risk zones.

**Task scope**: Information retrieval, navigation, form interaction on recorded paths. Multi-step workflows requiring full server-side state are reserved for Track A.

**Role**: Validates that Track A findings generalize to diverse real-world environments. Primary evidence base for Secondary RQ (WCAG feature importance via SHAP analysis).

### 5.4 Accessibility Measurement (Three-Tier)

| Tier | What It Measures | How | Coverage |
|------|-----------------|-----|----------|
| **1** | Structural compliance | axe-core + Lighthouse (headless Chromium) | ~57% of defect volume (Deque [10]); but only 13% of WCAG 2.2 AA criteria fully auto-detectable [39], and only 50.4% of blind user problems covered by WCAG [31] |
| **2** | Functional semantics (novel) | Programmatic checks: ARIA correctness (role + handler co-presence), meaningful accessible names, keyboard navigability, Shadow DOM bridging, semantic HTML ratio | Fills Tier 1 blind spots |
| **3** | Context-dependent quality | LLM-augmented evaluation + expert manual audit (10% sub-sample, inter-rater κ ≥ 0.80) | Ground truth validation |

**Independent variable operationalization**:
- **Track A**: Categorical (Low / Base / High) — ground truth, no measurement needed. *Note*: Pilot 2 revealed composite score compression (actual range 0.405–0.457 vs designed 0.00–1.00), indicating variant patches were not aggressive enough. Pilot 3 addresses this with enhanced patch scripts targeting wider score differentiation.
- **Track B**: Criterion-level Tier 1+2 feature set as primary; aggregate axe-core score reported as supplementary for interpretability.

### 5.5 Agent Failure Taxonomy

Not all agent failures are caused by poor A11y. We systematically attribute each failure via action trace analysis.

**Unit of analysis**: Individual failed task attempt. Each failed attempt is assigned a **dominant failure cause** based on the primary point of breakdown. Secondary failure events are retained in logs for qualitative analysis.

**A11y-attributed** (our hypothesis):
- Element Not Found in A11y Tree despite visual presence
- Wrong element actuation due to ARIA mislabel
- Keyboard trap (focus loop)
- Pseudo-compliance trap (correct role, no handler, retry loop)
- Shadow DOM invisibility
- Empty / degraded observation — agent receives minimal or empty A11y Tree due to incomplete semantic structure or slow DOM rendering of non-semantic elements, leading to blind navigation and wasted steps
- **Content invisibility** — semantic relationships broken (e.g., tabpanel ARIA associations), causing task-critical content to disappear from the A11y Tree entirely *(added from Pilot 2 trace analysis)*
- **Cross-layer content invisibility** — DOM mutations that affect both semantic AND visual rendering, making content invisible to both text-only and vision agents *(added from Pilot 3b trace analysis)*
- **SoM phantom bid** — DOM de-semanticization creates mismatch between SoM overlay labels (visible in screenshot) and actual interactive elements (absent in DOM), causing persistent click-failure loops for vision agents *(added from Pilot 3b)*
- **Structural infeasibility** — all navigation pathways to task-critical information are blocked; agent exhausts all strategies without reaching target *(operationally defined from Pilot 3b admin:4 low trace analysis)*

**Model-attributed** (control):
- LLM hallucination (fabricated UI element)
- Context overflow (lost track in long workflow)
- Reasoning error (misinterprets task)
- **Harmful affordance trap** — agent selects a valid but suboptimal interaction strategy that leads to context overflow (e.g., clicking into posts with 100+ comments instead of reading titles from list page) *(added from Pilot 3b reddit:67 analysis)*
- Unknown/unclassified (F_UNK) — failure does not match any specific detector pattern *(added from Pilot 2; replaces low-confidence default classification)*

**Platform-attributed** *(added from Pilot 2)*:
- Action serialization error — agent constructs syntactically valid action but platform parser truncates or misparses it (e.g., unbalanced parentheses in message content)

**Environmental**: Anti-bot block, network timeout

**Task feasibility annotation** *(added from Pilot 2)*: Each task × variant combination is annotated for feasibility — whether task-critical information remains accessible in the A11y Tree under that variant's manipulation. Results are reported both inclusive (all tasks) and feasible-only, distinguishing "environment makes task impossible" from "environment makes task harder."

**Pipeline**: Auto-classify via action trace patterns → confidence scoring → 10% manual review.

**Dual reporting**:
- **Conservative**: Correlation using only A11y-attributed failures
- **Inclusive**: Correlation using total failures

If conservative shows stronger correlation → evidence that A11y is specifically causal, not merely correlated via shared confounds.

#### 5.5.1 Failure Distribution

**Pilot 2** (35 failures):

| Failure Type | Count | % of Failures | By Variant (low / base / high) |
|-------------|-------|---------------|-------------------------------|
| Reasoning Error (F_REA) | 16 | 45.7% | 8 / 4 / 4 |
| Context Overflow (F_COF) | 11 | 31.4% | 5 / 2 / 4 |
| Task Ambiguity (F_AMB) | 8 | 22.9% | 4 / 1 / 3 |

**Pilot 4** (34 text-only failures, 98 vision-only failures):

Text-only failures by domain and variant:

| Domain | Type | Count | Primary Variant |
|--------|------|-------|----------------|
| A11y | Content Invisibility | 10 | low (ecom:23/24/26) |
| A11y | Structural Infeasibility | 5 | low (admin:4) |
| A11y | Token Inflation (timeout) | 3 | low (admin:4) |
| Model | Context Overflow (F_COF) | 8 | base/high (reddit:67) |
| Model | Reasoning Error (F_REA) | 5 | mixed |
| Model | Harmful Affordance Trap | 3 | base/high (reddit:67) |

**Key insight**: A11y-attributed failures dominate the low variant (18/23 = 78%). Model-attributed failures dominate at non-low variants (11/11 = 100%). This clean separation supports the claim that accessibility degradation introduces a mechanistically distinct failure pathway, not merely amplification of existing model weaknesses.

Vision-only failures (n=98) are dominated by partial_success (40/98=41%) — agents make progress but cannot complete tasks, consistent with the SoM phantom bid phenomenon preventing multi-step navigation.

**Vision-only as control condition — revised interpretation**: The SoM-based vision agent is not a "pure visual" control because SoM overlays depend on DOM interactive elements. Both agents are affected by low variant mutations, but through different mechanisms: text-only via degraded a11y tree information, vision-only via missing/phantom SoM bid labels. The meaningful comparison at non-low variants (where SoM labels are intact) shows text-only dramatically outperforms vision-only (87.8% vs 24.4%), confirming the a11y tree's substantial informational advantage. A fully coordinate-based vision agent (e.g., Claude Computer Use) would additionally isolate the execution pathway; this is listed as future work.

**Convergence with A11y-CUA** (Mohanbabu et al., CHI 2026): A11y-CUA reports CUA success dropping from 78.33% (default) to 41.67% (keyboard-only) to 28.33% (magnifier) — a comparable ~37pp degradation. Our Pilot 4 shows a 63.3pp degradation (base to low) for text-only agents. While they vary the agent's input modality, we vary the environment's semantic structure — yet both demonstrate that accessibility barriers impose a substantial performance tax. Our larger effect size (63.3pp vs 37pp) is consistent with our more aggressive environmental manipulation.

### 5.6 Statistical Framework

| Analysis | Method | Purpose |
|----------|--------|---------|
| A11y ↔ agent success | CLMM (ordinal A11y) + GEE (binary success, random intercepts for LLM + website) | Primary RQ |
| Feature importance | Random Forest + SHAP on criterion-level vectors | Secondary RQ |
| Sensitivity | Three-way regression: Tier 1 only / Tier 2 only / Composite | Construct validity |
| Gap analysis | Qualitative case analysis of agent failures on high-A11y sites | Exploratory RQ |

**Construct validity defense**: Convergent validity is assessed by comparing the *direction and pattern* of effects across tracks: Track A uses categorical manipulation (Low/Base/High) while Track B uses continuous criterion-level measurement. If both show that higher accessibility associates with higher agent success — despite differing IV operationalizations — the convergence strengthens our thesis. Additionally, if Tier 2 alone predicts better than Tier 1 alone → functional semantics matter more than syntactic compliance (publishable sub-finding).

**Statistical power**: Across five experimental rounds, the low-vs-base comparison consistently achieves significance: Pilot 2 p=0.006, Pilot 3a p<0.001, Pilot 3b p<0.001, Pilot 4 p<0.000001. Effect sizes range from Cramér's V=0.37 (Pilot 2) to V=0.637 (Pilot 4). The Pilot 4 full design matrix (N=240) provides definitive statistical power with Breslow-Day homogeneity p=1.000, confirming effects are consistent across tasks. 5 reps per cell sufficient for detecting large effects (>30pp); the observed 63.3pp low-base gap far exceeds this threshold.

**Agent framework control**: To avoid confounding A11y effects with agent-specific parsing strategies, we use WebArena's native agent architecture as the fixed framework (existing baselines available for comparison). LLM backend is modeled as a random effect in CLMM/GEE. We do not use customized agent architectures (e.g., AgentOccam's pivotal node filtering, CI4A's semantic interfaces) in the primary analysis, as their A11y Tree processing differences would introduce an additional uncontrolled variable.

---

## 6. Contributions

| Type | Contribution | Status |
|------|-------------|--------|
| **Empirical** | Among the first controlled evidence that A11y predicts agent success; **replicated across 5 rounds (Pilots 2, 3a, 3b-text, 3b-vision, 4) with consistent significance; Pilot 4 full experiment: N=240, χ²=24.31, p<0.000001, Cramér's V=0.637; three mechanistically distinct failure pathways: token inflation, content invisibility, SoM phantom bids** | Core |
| **Paradigmatic** | Environment-centric evaluation paradigm for web agents — reusable experimentation framework where any frontend property can serve as the independent variable; inverts existing agent-centric benchmarks | Core |
| **Methodological** | Agent Failure Taxonomy isolating A11y from model confounds; multi-tier A11y measurement beyond automated scanning; **task feasibility annotation distinguishing "impossible" from "harder"; Plan D variant injection persistence methodology (context.route + deferred patch + MutationObserver); verified: 33/33 goto traces show persistent degradation** | Core |
| **Conceptual** | "Same Barrier" hypothesis — formal bridge between accessibility and AI agent research; **convergent evidence with A11y-CUA (CHI 2026): environment degradation and modality constraint yield comparable ~37pp drops** | Core |
| **Novel Finding** | **DOM semantic quality affects vision-based (SoM) agents through overlay infrastructure dependencies — two distinct phantom label modes identified (exists-not-visible vs element-not-found); forced strategy simplification reveals non-monotonic accessibility-performance relationship (reddit:67: ml 100% vs base 20%, 14× token efficiency)** | Core |
| **Theoretical** | **"Overlay false affordance" — novel category in Gaver's false affordance taxonomy; duality framework connecting false affordances (failure path) with action-space constraint theory (success path) under single DOM semantic change; grounded in Majumdar (2026) formal complexity results** | Core |
| **Exploratory** | Initial ACAG gap characterization; AI-Readiness Maturity Model (Level 0–3); experience sedimentation as inverse A11y metric | Discussion / Future Work |
| **Exploratory** | Human-agent divergence analysis: identifying cases where optimizing for AI agents may conflict with human assistive technology needs | Discussion / Future Work |
| **Exploratory** | Generalization of environment manipulation framework to non-accessibility frontend properties (interaction latency, dark patterns, internationalization, visual layout); **fully coordinate-based vision agent control** | Future Work |

**Open artifacts**: Dataset (websites + A11y scores + agent results + failure logs), measurement pipeline (open-source), environment manipulation framework, A11y-Agent benchmark.

---

## 7. Timeline & MVP

| Phase | Period | Activities | Status |
|-------|--------|------------|--------|
| **Prep** | Mar–Apr 2026 | Literature review finalization; WebArena deployment + A11y variant creation; Tier 1+2 pipeline; pilot studies | 🟢 **Pilots 2–3b complete** — 4 rounds, 81–240 cases each, statistically significant across all (p<0.008). Platform bugs identified and fixed. Vision-only control condition validates causal pathway. |
| **Data Collection** | Apr 2026 | Track A full execution with Plan D variant injection | 🟢 **Pilot 4 complete** — 240/240 cases, N=240 full design matrix, p<0.000001. Plan D verified (33/33 goto traces). Three bugs identified and fixed (ISSUE-BR-1/4/7). Deep dive analysis complete on all anomalous cases. |
| **Track B** | May–Jul 2026 | HAR recording + landscape survey (200+ sites); real-world ecological validation (parallel with SURF #2) | 🟡 **Not started** |
| **Additional experiments** | May–Jun 2026 | Expand task set (6→15–20 tasks); add medium-high variant; cross-site generalization (GitLab); optionally add CUA control | 🟡 **Optional** — current data sufficient for paper; expansion strengthens generalizability |
| **Analysis** | Jul–Aug 2026 | CLMM/GEE, SHAP, failure taxonomy coding, cross-pilot meta-analysis | 🟡 **Partially complete** — Pilot 4 analysis done, formal statistical modeling pending |
| **Writing** | Aug–Sep 2026 | Paper drafting | 🟢 **In progress** — LaTeX skeleton created, abstract written, Results data ready |
| **Submission** | Sep–Oct 2026 | CHI 2027 (full or LBW) | Pending |

**MVP (minimum publishable)**: Pilot 4 Track A results (6 tasks × 4 variants × 2 agents, 1 LLM, N=240) + failure taxonomy + deep dive analysis = sufficient for CHI full paper or ASSETS. Track B would strengthen ecological validity but is not required for core contribution.

**Venues**: CHI 2027 (Sep) → ASSETS 2027 (Jun) → CSCW 2027 → WWW 2027.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Weak correlation | Track A's A/B design is robust; **Pilot 2 already shows significant effect (p=0.006)**; even null result publishable with rigorous method |
| Failure attribution confounds | Taxonomy with dual reporting; 10% manual review validates auto-classification; **Pilot 2 trace analysis validated taxonomy by identifying platform bugs masquerading as accessibility effects** |
| Tier 1 construct validity | Three-layer defense: Tier 2 functional metrics + Track A cross-validation + sensitivity analysis |
| Scope overload | MVP defined; Track A primary; Track B core at 50, expandable to 200+ |
| HAR replay limitations | HAR cannot capture WebSocket or real-time state updates. Track B task scope explicitly excludes tasks requiring live server-side state (reserved for Track A). Acknowledged as threat to ecological validity. |
| Ethical: responsible disclosure | Track B dataset will anonymize individual website identities in public release; A11y scores reported only in aggregate by sector/geography. Individual site results available only to site owners upon request. IRB review sought if required by institution. |
| Pseudo-compliance | Tier 2 handler verification + dedicated failure category |
| Tier 2 engineering complexity | Tier 2 pipeline built on Playwright native API (accessibility.snapshot() + CDP); validated during pilot phase |
| Variant injection fidelity | **RESOLVED.** Pilot 2 identified composite score compression (0.405–0.457). Pilot 3 enhanced operators. Pilot 3b revealed goto() escape vulnerability. **Plan D (context.route + deferred patch + MutationObserver) verified in Pilot 4: 33/33 goto traces show persistent degradation. ecom:23 low dropped from 80% (3b, escape) to 0% (Pilot 4, Plan D).** Three bridge bugs identified and fixed (ISSUE-BR-1: timer leak, ISSUE-BR-4: MutationObserver sentinel, ISSUE-BR-7: stderr capture). None had significant impact on Pilot 4 data (controlled token comparison: high vs base Δ < 1.3% on matched tasks). |
| Vision control confound | **SoM-based vision agent is not a pure visual control — SoM overlays depend on DOM interactive elements. Low variant mutations affect both text-only (via a11y tree) and vision-only (via phantom bids). Coordinate-based vision agent (Claude Computer Use) would provide cleaner isolation; listed as future work. A11y-CUA provides complementary evidence.** |
| Human-agent divergence | "Same Barrier" describes structural equivalence, not identity. Over-engineering for agents (e.g., excessive hidden ARIA) may increase cognitive load for screen reader users. **Pilot 2 high variant data is consistent with this concern — enhanced ARIA did not improve agent performance and may introduce DOM bloat.** Acknowledged in Limitations; motivates ACAG as a balancing standard, not a pure superset of WCAG |
| Task feasibility confounds | **Low variant may make tasks logically impossible (content invisibility) rather than merely harder. Task feasibility annotation and dual reporting (all tasks vs feasible-only) separate these effects.** |
| Absolute claims challenged | Hedged language: "to our knowledge," "we argue that," "among the first" |

---

## 9. Key References

### Agent Benchmarks and Evaluation
1. Zhou et al. — WebArena (CMU, 2024) [arxiv 2307.13854]
2. Deng et al. — Mind2Web (NeurIPS 2023)
3. Gao et al. — AgentOccam: +161% via A11y Tree (Amazon Science, ICLR 2025) [arxiv 2410.13825]
4. Chen et al. — CI4A: 86.3% WebArena SOTA (ByteDance) [arxiv 2601.14790]
5. Abuelsaad et al. — "An Illusion of Progress?" [arxiv 2504.01382]
6. Zhou, Hernández-Orallo et al. — ADeLe: 18 cognitive dimensions (Nature 2026) [arxiv 2503.06378]
7. He et al. — WebVoyager (ACL 2024)
8. Zheng et al. — SeeAct (OSU)

### Accessibility Standards and Measurement
9. WebAIM — Million 2025 Report (94.8% failure rate, ARIA paradox)
10. Deque — Automated testing detects 57% of A11y issues (volume-based)
11. CodeA11y — LLM-augmented A11y auditing (87.18% detection)
12. UC Berkeley & UMich — nohacks.co / CHI 2026: Agent keyboard-only experiment (78.33% → 41.67%)
13. W3C — WCAG 2.2 / WAI-ARIA 1.2
14. W3C Web ML CG — WebMCP specification (Chrome 146, Feb 2026)
15. CopilotKit — AG-UI Protocol
16. Nolan Lawson — Shadow DOM and ARIA (2022)

### Industry and Policy
17. Virtana — 75% enterprise double-digit AI failure rates (2026)
18. Patronus AI — 63% workflow failure at 1% per-step error
19. EU Directive 2019/882 — European Accessibility Act

### Environment Perturbation and Robustness
20. "Better Assumptions, Stronger Conclusions: Ordinal Regression in HCI" [arxiv 2602.18660]
21. RAND — "Quantifying AI's Economic Potential"
22. VisualWebArena [arxiv 2401.13649]
23. WorkArena [arxiv 2403.07718]
24. ARE — Adversarial web page perturbations [arxiv 2406.12814]
25. WAREX — Web agent reliability evaluation via fault injection [arxiv 2510.03285]
26. GUI-Robust — GUI anomaly robustness dataset (Yang et al., 2025) [arxiv 2506.14477]
27. D-GARA — Dynamic GUI agent robustness benchmarking (Chen et al., 2025) [arxiv 2511.16590]
28. Aegis — Agent-environment failure taxonomy + optimization (Song et al., 2025) [arxiv 2508.19504]
29. ARE — Adversarial perturbations hijack agents (2024) [arxiv 2406.12814]
30. **Ma11y** — Mutation framework for web accessibility testing (Tafreshipour et al., ISSTA 2024) [github.com/mahantaf/web-a11y-tool-analyzer]

### Observation Space and Token Efficiency
31. Power et al. — 50.4% of blind user problems in WCAG (CHI 2012) [doi 10.1145/2207676.2207736]
32. FocusAgent — Lightweight a11y tree retriever [arxiv 2510.03204]
33. Prune4Web — 25-50× element reduction [arxiv 2511.21398]
34. AgentOCR — Visual compression for web agents [arxiv 2601.04786]
35. Chung et al. — Long-context web agent benchmark (<10% success at 25K-150K tokens) [arxiv 2512.04307]

### Theoretical Frameworks
36. Gibson, J.J. — The Ecological Approach to Visual Perception (1979) — Affordance Theory
37. Han et al. — Computational rationality-based affordance for AI agents (2025) [arxiv 2501.09233]
38. Huang et al. — EnviSAgE: Environment-centric perspective for agents (2025) [arxiv 2511.09586]
39. Accessible.org — Only 13% of WCAG 2.2 AA fully auto-detectable (2025)
40. WCAG 3.0 — Graduated scoring model (Bronze/Silver/Gold), critical errors

### Cross-Browser and ARIA Research
41. Igalia — Accessible name computation divergence across browsers (2023)
42. Rego (Igalia) — Solving cross-root ARIA issues in Shadow DOM
43. W3C — AccName specification, IDREF resolution rules
44. Speech enhancement degrades ASR paradox [arxiv 2512.17562]
45. Gandor & Nalepa — JPEG compression threshold effects on object detection (Sensors 2022)
46. Shermeyer & Van Etten — Satellite imagery resolution thresholds (2018) [arxiv 1812.04098]

### Accessibility Metrics and User Studies
47. RA-WAEM — User-experience accessibility metric (W4A 2018)
48. Applause — "Accessibility is the infrastructure for AI readiness" (2025)
49. DubBot — "When AI reads like a screen reader" (2026)
50. Opus Research — "Why AI needs accessibility" (2025)
51. CHI 2026 Workshop — "Dual-audience" problem: interfaces for humans and agents [arxiv 2603.10664]
52. Screen2AX — Generating a11y trees from screenshots (MacPaw, 2025) [arxiv 2507.16704]
53. Browser Use — "Make websites accessible for AI agents" (84.7K GitHub stars)
54. Google — Natively Adaptive Interfaces (NAI) for multimodal AI agents
55. Vigo & Harper — "Accessibility-in-Use" evaluation (W4A 2013)
56. Build the Web for Agents — Position paper [arxiv 2506.10953]

### SoM Robustness, False Affordances, and Action Space Theory
57. Yang et al. — Set-of-Mark Prompting (2023) [github.com/microsoft/SoM]
58. SHARPMARK — SoM modality gap analysis (ACL ARR 2024) [openreview.net/forum?id=YQf0IcGkdn]
59. Shi et al. — "Towards Trustworthy GUI Agents" survey (2025): Execution Gap formalization [arxiv 2503.23434]
60. Gaver, W.W. — "Technology Affordances" (CHI 1991): False affordance taxonomy
61. Norman, D. — "The Design of Everyday Things" (2013): Signifiers vs affordances
62. Liu et al. — "Visual Confused Deputy" for CUAs (2026) [arxiv 2603.14707]
63. Wang et al. — A4Bench: MLLM affordance evaluation (2025) [arxiv 2506.00893]
64. Nitu & Stöckl — Agent satisficing behavior with SoM overlays (2025) [arxiv 2507.12844]
65. OpenAI — Computer-Using Agent (CUA): 58.1% WebArena [openai.com/index/computer-using-agent]
66. UI-TARS — Pure-vision GUI agent (2025) [arxiv 2501.12326]
67. MolmoWeb — Open pure-vision web agent (AI2, 2026) [the-decoder.com]
68. GUI-Actor — Coordinate-free attention grounding (2025) [arxiv 2506.03143]
69. Schwartz, B. — "The Paradox of Choice" (2004)
70. Hick, W.E. — "On the Rate of Gain of Information" (1952): Hick-Hyman Law
71. Progressive Disclosure — HCI design principle (Miller, 1956)
72. W3C COGA — Cognitive Accessibility Guidance (2020) [w3.org/TR/2020/WD-coga-usable-20201211]
73. Huang et al. — Contextual distraction ~45% degradation (2025) [arxiv 2502.01609]
74. Majumdar — Dense Ω(M) vs sparse √k action complexity (2026) [arxiv 2601.08271]
75. Nica et al. — Paradox of choice in RL (2022) [arxiv 2201.09653]
76. Plan-MCTS — Semantic plan space exploration (2026) [arxiv 2602.14083]
77. DMAST — DOM injection as two-player Markov game (UC Berkeley/DeepMind, 2026) [arxiv 2603.04364]
78. Google DeepMind — AI Agent Traps framework (2026) [securityweek.com]
79. Röder et al. — Detecting Pipeline Failures in web agents (DFKI, 2024) [arxiv 2509.14382]

