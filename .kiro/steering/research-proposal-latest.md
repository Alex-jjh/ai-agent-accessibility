---
inclusion: always
---
<!------------------------------------------------------------------------------------
   Add rules to this file or a short description and have Kiro refine them for you.
   
   Learn about inclusion modes: https://kiro.dev/docs/steering/#inclusion-modes
-------------------------------------------------------------------------------------> 
# Research Proposal v6.2: Accessibility as AI-Readiness
## Same Barrier, Different Users: How Web Accessibility Determines AI Agent Task Success

**PI**: Jiahao Jiang (Alex) | **Advisor**: Dr. Brennan Jones (XJTLU, HCI/Accessibility)
**Date**: April 14, 2026 | **Target**: CHI 2027 / ASSETS 2027

---

## 1. Abstract

Autonomous AI agents increasingly rely on the browser Accessibility Tree-the same semantic interface built for screen readers-as their primary observation space for web interaction. Yet no existing benchmark controls for the accessibility properties of target websites, making it impossible to distinguish agent limitations from environmental hostility. We propose the **"Same Barrier" hypothesis**: AI agents and assistive technology users face structurally equivalent obstacles on inaccessible websites because both depend on semantic HTML, ARIA annotations, and keyboard navigability.

We test this hypothesis through an **environment-centric evaluation paradigm** that inverts standard benchmark design: rather than varying agents against a fixed environment, we programmatically manipulate web accessibility while holding the agent constant. In a multi-phase experiment on WebArena (13 tasks × 4 accessibility variants × 2 LLMs × 4 agent architectures, **N=1,040 total cases across 9 experimental rounds**), we find that degrading accessibility from baseline to low causes Claude Sonnet text-only agent success to drop from 100% to 51.4% across 13 tasks, with a sharp step-function at the boundary between low and medium-low accessibility (+48.6 percentage points). Cross-model replication with Meta Llama 4 Maverick (260 cases) reveals a complementary pattern: a gradient rather than step function (low 36.9% → ml 61.5% → base 70.8% → high 75.4%), demonstrating that weaker models are affected across the entire accessibility spectrum, not just at the low extreme. A coordinate-based Computer Use Agent (CUA) with zero DOM dependency shows a +40.0pp accessibility gradient across all 13 tasks (low 58.5% → base 93.8%), confirming that accessibility degradation operates through cross-layer functional breakage independent of DOM semantic reading. A Set-of-Mark (SoM) vision-only agent reveals a weaker but consistent gradient (+25.7pp), dominated by a novel "phantom bid" failure mode where SoM overlays create false interactivity signals on de-semanticized elements. Three-agent causal decomposition attributes 33.3pp specifically to the Accessibility Tree pathway and 30.0pp to cross-layer functional breakage, with converging evidence across Pilot 4 and expansion tasks.

An ecological validity study scanning 34 real-world websites (including Amazon, JD.com, GitHub, Wikipedia, and the WebArena Docker environments) with axe-core and custom detectors establishes that our experimental manipulations reflect real-world conditions. We introduce a **three-severity framework**: L1 decorative violations (img alt, lang attributes) appear on 70% of sites but have zero agent impact; L2 annotation violations (aria-label, aria-live) appear on 20% but have zero agent impact; **L3 structural violations (landmark→div, link→span) appear on 83.3% of sites and are fatal to agents** - the only severity level that drives the observed performance collapse. This framework explains why WebArena's base applications (which contain L1/L2 imperfections) support near-100% agent success: only L3 structural integrity matters.

Trace-level analysis across all experiments reveals four distinct failure pathways: (1) *content invisibility*, where broken ARIA relationships hide task-critical information from the Accessibility Tree; (2) *token inflation*, where degraded semantic structure forces agents into exhaustive exploration (up to 8.95× inflation with extremes reaching 514K tokens); (3) *phantom bids*, a novel failure mode where SoM overlays create false interactivity signals on de-semanticized elements; and (4) *cross-layer functional breakage*, where DOM mutations (link→span) destroy navigation affordances independent of semantic or visual channels. We additionally document *forced strategy simplification*, a paradoxical effect replicated across both model families where removing interactive affordances constrains the agent's action space and improves performance.

These findings, replicated across nine independent experimental rounds with two model families (Anthropic Claude, Meta Llama) and four agent architectures (text-only, SoM vision-only, coordinate-based CUA, and cross-model text-only), establish web accessibility as a significant, previously uncontrolled variable in AI agent evaluation, and provide the first controlled empirical evidence that the infrastructure built for human disability access directly determines AI agent capability.

We contribute: (1) the first controlled empirical evidence that web accessibility predicts AI agent task success, replicated across 9 rounds with 2 LLMs and 4 agent architectures (N=1,040, p<0.000001); (2) cross-model generalizability evidence showing model-dependent dose-response profiles (step function for strong models, gradient for weak); (3) cross-architecture generalizability showing the accessibility gradient is consistent across all four agent types (text-only, SoM, CUA, Llama 4), with mechanism-specific failure modes for each; (4) an ecological validity study establishing that 83.3% of real-world websites contain the structural violations that cause agent failure; (5) a three-severity framework (L1/L2/L3) mapping accessibility violation types to agent impact levels; (6) an environment-centric evaluation paradigm and reusable experimentation framework; (7) a three-agent causal decomposition methodology quantifying the Accessibility Tree pathway (33.3pp) versus cross-layer functional breakage (30.0pp); (8) a failure attribution methodology identifying five distinct SoM failure modes (phantom bid loops 48%, visual misread 26%, form interaction failure 17%, exploration spirals 13%, navigation failure 13%) and three CUA failure modes (cross-layer functional breakage, UI complexity traps, step budget exhaustion); (9) the "Same Barrier" hypothesis refined to operate at the DOM structural level (L3) rather than ARIA annotation level; and (10) the duality framework connecting false affordances (failure path) with action-space constraint theory (success path) under a single DOM semantic change.

---

## 2. Research Problem

### 2.1 The Gap

AI agents increasingly use the browser Accessibility Tree as their primary observation space. AgentOccam (Amazon Science) achieves +161% improvement via filtered A11y Tree nodes; CI4A (ByteDance) reaches WebArena SOTA of 86.3% through semantic component interfaces; Vercel's Agent-Browser reduces context window usage by 93% using accessible names and ARIA roles. Industry products - AirJelly, CLI-Anything/DOMShell, DirectShell - all build on accessibility infrastructure. Internal deployments at major cloud providers confirm this dependency: enterprise AI agent products (scheduled assistants, workflow automators) universally rely on accessibility infrastructure of target applications, yet the accessibility quality of those targets remains uncontrolled and unquantified.

Yet no existing benchmark controls for this dependency. WebArena, Mind2Web, and VisualWebArena evaluate agent reasoning but treat website accessibility as an uncontrolled environmental variable. When a frontier agent achieves 14% success on WebArena, we cannot distinguish model limitations from environmental hostility. The accessibility research community, conversely, has not considered AI agents as a stakeholder group benefiting from universal design.

**A paradigm gap**: All existing web agent benchmarks adopt an *agent-centric* evaluation paradigm - they hold the web environment constant and vary agent architectures or models. This design answers "which agent is better?" but cannot answer "what environmental properties make agents succeed or fail?" The absence of an *environment-centric* paradigm leaves a fundamental question unaddressed: how do the properties of web environments causally influence agent performance?

### 2.2 Practical Motivation

When an agent encounters a non-semantic DOM, it typically falls back from efficient A11y Tree parsing (~2-5KB per page) to expensive VLM screenshot processing (~500KB-2MB), with corresponding increases in latency and API costs. Industry reports suggest high failure rates in enterprise AI agent deployments: Patronus AI finds that agents with even 1% per-step error face a 63% chance of complete workflow failure by step 100. Our experimental data quantifies this directly: in our full 240-case experiment, degraded accessibility inflates token consumption by 27% on average (172K vs 135K tokens per task), with extreme cases reaching 608K tokens - causing LLM context overflow and complete task failure. In one task (reddit:67), 4 out of 5 runs at base/high accessibility crashed at 608K tokens, while the same task at medium-low accessibility succeeded in 100% of runs using only 43K tokens - a 14× efficiency difference attributable entirely to action space constraint. We argue that inaccessible web infrastructure - the same infrastructure that excludes users with disabilities - is an under-recognized contributor to these failures, and that quantifying this relationship has direct implications for both agent architecture design and the business case for accessibility investment.

**Token inflation as environmental cost**: Recent critiques from the inference infrastructure community [Zhao, 2026] argue that agent frameworks waste tokens through poor context management. Our data identifies a complementary upstream cause: **environmental hostility**. Low-accessibility websites produce inflated Accessibility Trees with low information density-redundant generic containers, broken semantic relationships, missing landmarks-forcing agents to process 2.15× more tokens regardless of framework optimization (366K vs 178K for CUA, low vs base). Combined with compounding error theory [Patronus AI: 1% per-step → 63% workflow failure by step 100], this creates a double penalty: more tokens per step → more steps per task → higher cumulative failure probability. Token optimization must address both the framework layer (cache-aware context construction) and the **environment layer** (web accessibility).

**Ecological validity**: A critical question for any controlled experiment is whether the manipulations reflect real-world conditions. Our ecological validity study (§5.4) directly addresses this: automated axe-core scanning of 34 real-world websites across 5 categories reveals that L3 structural violations-the specific manipulation category that drives our experimental effects-appear on **83.3% of surveyed sites**. The most prevalent violation, missing landmark elements (P7: landmark→div), appears on 82.4% of sites with an average of 37 affected nodes per site. Chinese e-commerce platforms (AliExpress: 266 violations, Bilibili: 350, JD.com: 86) are particularly affected. This establishes that our low variant is not a contrived worst case but a composite of violations routinely found on high-traffic websites.

### 2.3 Related Work and Positioning

#### 2.3.1 Environment Perturbation Approaches

Recent work has begun manipulating web environments to test agent robustness, but none targets accessibility semantics. **WAREX** [25] uses a transparent proxy to inject infrastructure failures (network delays, HTTP 4xx/5xx, JavaScript failures, popups) into WebArena/WebVoyager, demonstrating significant drops in agent success rates. **GUI-Robust** [26] introduces 200 abnormal scenarios across seven GUI anomaly types (pop-ups, ad overlays, loading failures, layout shifts), revealing substantial performance degradation. **D-GARA** [27] extends this with a dynamic benchmarking framework. **Aegis** [28] takes a complementary "environment-optimization" approach: by analyzing 142 agent traces (3,656 turns) across five benchmarks, it proposes a taxonomy of six agent-environment interaction failure modes and then *optimizes* environments to improve success rates by 6.7-12.5%. **ARE** [29] demonstrates that imperceptible perturbations to web page images can hijack agents with up to 67% success.

These works establish that environment properties significantly affect agent performance, but their manipulations target infrastructure faults (WAREX), visual anomalies (GUI-Robust), or adversarial attacks (ARE) - **none manipulates accessibility semantics** (ARIA attributes, semantic HTML structure, keyboard navigability) as the independent variable.

#### 2.3.2 Accessibility Mutation Testing

**Ma11y** [30] (ISSTA 2024) is the closest methodological precedent. It introduces 25 mutation operators based on WCAG 2.1 failure techniques, using Puppeteer to inject accessibility violations into the DOM. Operators include F2 (replace `<h2>` with styled `<p>`), F68 (remove form `<label>` elements), F91 (replace `<th>` with `<td>`), F96 (corrupt `aria-label` with random strings), and F44 (reverse `tabindex` order). Several of these operators directly correspond to our low variant manipulations.

However, Ma11y's research question is fundamentally different: it evaluates whether accessibility **testing tools** detect injected violations. Our dependent variable is whether accessibility violations cause AI **agent task failures**. This distinction mirrors the broader conformance-usability gap documented by Power et al. [31] - detecting a violation and experiencing its functional impact are separate phenomena.

#### 2.3.3 Observation Space and Token Efficiency

A rapidly expanding body of work demonstrates that targeted observation space pruning dramatically improves agent performance. **AgentOccam** [3] achieves +161% improvement on WebArena by filtering the accessibility tree to retain only "pivotal" interactive nodes. **FocusAgent** [32] reduces AxTree observations by 50%+ using a lightweight LLM retriever. **Prune4Web** [33] achieves 25-50× element reduction, nearly doubling grounding accuracy from 46.8% to 88.28%. **AgentOCR** [34] preserves 95% of text-based performance while halving tokens.

Critically, **Chung et al.** [35] directly benchmark long-context reasoning in web agents, finding success rates drop from 40-50% at baseline to **below 10%** in long-context scenarios (25,000-150,000 tokens), with agents getting stuck in loops and losing track of objectives. This establishes context overflow as a severe failure mode - but no study has identified accessibility quality as the **upstream cause** of observation space bloat.

#### 2.3.4 Theoretical Grounding

**Gibson's affordance theory** [36] provides the conceptual foundation for our paradigm inversion: affordances are relational properties of the environment relative to the actor's capabilities. Broken accessibility strips the environment of programmatic affordances. **Han et al.** [37] operationalize computational rationality-based affordances for AI agents. **EnviSAgE** [38] formalizes the environment-centric perspective via the GEF (Goal-Environment-Feedback) loop, arguing that environment properties-observability, controllability, and feedback quality-are the primary determinants of agent success. Our work provides the first large-scale empirical evidence within this paradigm.

**ADeLe** [6] (Nature 2026) introduces 18 cognitive dimensions that profile both task demands and AI system abilities, achieving ~88% instance-level predictive accuracy. Our work is complementary: ADeLe measures *task demand* (what cognitive operations are required), we measure *environment quality* (how the interface structure affects agent perception). Together with EnviSAgE's theoretical framework, they enable a complete decomposition:

> **performance = task demand (ADeLe) × environment quality (EnviSAgE framework, our data) × agent capability (benchmarks)**

**Compounding error theory** provides additional motivation. Patronus AI [18] demonstrates that a 1% per-step error rate compounds to 63% workflow failure by 100 steps. Our data shows that degraded accessibility *increases* per-step error rates while simultaneously inflating token consumption and step counts, creating a double penalty that amplifies compounding failure.

No existing framework addresses the environment-side structural dimension with empirical data.

#### 2.3.5 Accessibility Measurement at Scale

**WebAIM Million 2025** [9] finds 94.8% of the top million homepages fail WCAG 2, averaging 51 errors per page. Paradoxically, pages utilizing ARIA average 57 errors vs. 27 on non-ARIA pages [9], indicating that ARIA adoption does not equal machine-readability. **Power et al.** [31] (CHI 2012) tested 32 blind users on 16 websites and found only 50.4% of problems encountered were covered by WCAG 2.0 - and 16.7% of compliant sites still failed users. **Accessible.org** [39] found that only 13% of WCAG 2.2 AA criteria (7 of 55) are fully auto-detectable, with 42% requiring human judgment. **WCAG 3.0** [40] introduces graduated scoring (Bronze/Silver/Gold) and "critical errors" that override positive scores. No existing large-scale study measures **AI-readiness** specifically - the accessibility tree completeness and semantic integrity that determine agent operability.

#### 2.3.6 Cross-Browser ARIA Divergence

Browsers handle broken ARIA references inconsistently. **Igalia's research** [41] revealed that `aria-labelledby` referencing hidden elements produces different accessible names across engines: WebKit yields "d", Firefox "abcd", Chrome "bcd" for identical markup. Shadow DOM completely breaks ARIA relationship attributes across shadow root boundaries - an issue identified in 2014 that remains unresolved [16, 42]. The **W3C AccName specification** [43] was clarified to require "at least one valid IDREF," but corner cases involving hidden subtrees remain divergent across implementations.

#### 2.3.7 Threshold Effects Across Domains

Non-linear dose-response patterns are well-documented in adjacent domains. In speech recognition, enhancement preprocessing paradoxically **degrades** ASR performance across all noise conditions [44]. In computer vision, JPEG compression degrades object detection in a "first gradually, then suddenly" collapse pattern [45]. In satellite imagery, resolution improvements yield 13-36% detection gains until diminishing returns set in [46]. Within accessibility research, pages with ARIA average 34% more errors than those without [9], and screen reader verbosity from excessive markup significantly increases task completion time [47]. No formal dose-response model has been applied to accessibility's effect on AI agents.

#### 2.3.8 SoM Overlay Robustness and False Affordances

**Set-of-Mark implementation divergence**: The original SoM paper (Yang et al., 2023) [57] generates marks through pure visual segmentation (SAM, SEEM) with zero DOM dependency. However, every major web-agent framework has shifted to DOM-based label generation: BrowserGym assigns unique bid identifiers via Chrome CDP with visibility/clickability flags [23]; VisualWebArena uses JavaScript DOM traversal to annotate interactable elements [22]; WebVoyager uses rule-based JavaScript extraction of interactive element types [7]. This creates a tight coupling between label validity and DOM state integrity that the original SoM design explicitly avoided.

**Documented SoM failure modes**: SeeAct (Zheng et al., ICML 2024) [8] reported that SoM prompting is "not effective for web agents," with 53% of grounding errors from wrong action generation and additional failures from "making up bounding box & label." SHARPMARK (ACL ARR 2024) [58] identified a "modality gap" between textual HTML elements and visual SoM overlays. The "Towards Trustworthy GUI Agents" survey (Shi et al., 2025) [59] formalized the **Execution Gap**: interfaces change between perception and action, causing silent failures. BrowserGym's bid system creates **"double staleness" risk**: the visual label persists on screenshots even after the underlying bid becomes invalid due to DOM mutation - but BrowserGym handles staleness reactively (post-failure error messages) with no pre-execution re-validation [23].

**The phantom bid as overlay false affordance**: Gibson's (1979) affordance theory [36] defines affordances as relational properties between actor and environment. Gaver (1991) [60] formalized **false affordances** - perceived action possibilities that do not exist. Norman (2013) [61] refined this as **false signifiers** - visual cues suggesting nonexistent actions. Our phantom bid phenomenon maps onto a novel subcategory: an **overlay false affordance**, where the annotation layer itself (SoM labels) creates the false signifier on DOM elements that have been de-semanticized. No 2023-2026 publication has formally connected Gaver's taxonomy to AI agent failure modes. The closest work is the "visual confused deputy" formalization (Liu et al., 2026) [62], which frames misperceived screen states as a security issue; A4Bench (Wang et al., 2025) [63] evaluates MLLM affordance perception but focuses on physical-world rather than web interface affordances; and Nitu & Stöckl (2025) [64] document that agents display "satisficing behavior," ignoring visual calls-to-action when semantic button overlays are absent.

**The SoM-to-coordinate paradigm shift**: The field has moved decisively from SoM-dependent to coordinate-based agents. OpenAI CUA [65] processes raw pixels with virtual mouse/keyboard, achieving 58.1% on WebArena vs. GPT-4V+SoM's 16.37% on VisualWebArena [22]. UI-TARS [66] explicitly identifies SoM's limitation: "textual-based methods often require system-level permissions to access underlying system information." MolmoWeb [67] argues "a website's appearance changes less often than its underlying code," making pure-vision agents inherently more robust to DOM mutations. GUI-Actor [68] proposes "coordinate-free" attention-based grounding, outperforming UI-TARS-72B with a 7B model.

**Research gap**: No study specifically measures SoM overlay staleness under controlled DOM mutation conditions. WAREX [25] tests infrastructure faults, ARE [29] tests adversarial perturbations, but neither isolates DOM semantic mutation as a causal factor for SoM label degradation. Our controlled experiment - where we programmatically de-semanticize DOM elements and observe SoM label persistence - fills this gap with the first causal evidence.

#### 2.3.9 Constraint-Driven Performance and the Action Space Curse

The paradoxical observation that removing link semantics can improve agent performance connects to a convergent body of evidence across cognitive science, HCI, and AI agent research.

**Cognitive science foundations**: Schwartz's Paradox of Choice (2004) [69] establishes that eliminating options reduces decision anxiety. The Hick-Hyman Law (1952) [70] formalizes this: reaction time increases logarithmically with stimuli count (RT = a + b·log2(n)). Progressive disclosure [71] manages complexity by showing only essentials, grounded in Miller's ~7 item working memory limit. The W3C COGA guidance [72] extends this to cognitive accessibility: impaired working memory handles only 1-3 items, making interface simplification essential - a constraint that directly parallels LLM context window limits.

**Empirical validation in agent research**: AgentOccam (ICLR 2025) [3] achieved +161% success rate by refining observation/action spaces alone. Prune4Web [33] doubled grounding accuracy (46.8% → 88.28%) through 25-50× DOM reduction. FocusAgent [32] reduced observation size by 50%+ while matching baseline performance and reducing prompt injection vulnerability. Conversely, context bloat drops success from 40-50% to below 10% in 25K-150K token scenarios [35], and contextual distractions cause ~45% performance degradation [73].

**Formal results**: Majumdar (2026) [74] proves that dense (unpruned) policies require Ω(M) samples over M actions, while sparse policies achieve suboptimality scaling as √k - logarithmic rather than linear in action count. Nica et al. (2022) [75] empirically demonstrate the "paradox of choice" in RL: fewer but more meaningful choices improve learning speed. Plan-MCTS [76] shows that exploring semantic plan space rather than action space produces more concise trajectories.

**Our contribution - the duality framework**: Phantom bids and forced strategy simplification are dual outcomes of the same cause - DOM semantic change - with opposite effects. When `<a>` → `<span>`: (1) on the failure path, SoM labels persist as overlay false affordances, causing 20+ step click-failure loops; (2) on the success path, removed link affordances constrain the action space, forcing agents onto more efficient strategies (43K vs 580K tokens). No published work documents this duality or connects false affordance theory (failure path) with action-space constraint theory (success path) under a unified framework.

#### 2.3.10 Concurrent Work: Agent-Side Accessibility

**A11y-CUA** (Mohanbabu et al., CHI 2026) [77] takes the complementary agent-side perspective. They collect a multimodal dataset of 16 participants (8 blind/low-vision users, 8 sighted users) performing 60 everyday desktop tasks (40.4 hours, 158,325 events), then evaluate CUAs under assistive technology conditions. Claude Sonnet 4.5's CUA drops from 78.3% (default) to 41.67% (keyboard-only) and 28.3% (magnified viewport); Qwen3-VL drops from 20% to 0% under both AT conditions.

Critically, A11y-CUA and our work manipulate **orthogonal variables**: they constrain *how the agent interacts* (input modality), while we manipulate *what the agent interacts with* (DOM semantic structure). Their performance drops stem from agents lacking keyboard navigation and magnified-viewport skills; ours stem from the environment itself losing semantic integrity. Together, these two perspectives decompose the accessibility–agent relationship into agent-side capability and environment-side quality — both independently predict task failure, and both must be addressed for truly robust agents. Our work provides the missing environment-side causal evidence that complements their agent-side characterization.

#### 2.3.11 Gap Summary

| Gap | Closest Prior Work | Our Contribution |
|-----|-------------------|------------------|
| No work manipulates web a11y as IV for agent evaluation | WAREX (infra faults), GUI-Robust (visual anomalies) | First environment-centric web agent benchmark using accessibility as IV |
| No causal link between a11y quality and token consumption | AgentOccam (downstream filtering), Chung et al. (long-context effects) | Quantified 87% token inflation; identified upstream causal pathway |
| No formal "phantom content" concept | Igalia cross-browser studies, W3C AccName spec | First controlled demonstration: broken ARIA makes tasks logically impossible |
| No metric for functional semantic integrity | Deque 57% (volume-based), Power et al. (50.4% user coverage) | Tier 2 measurement evaluating a11y tree completeness beyond WCAG compliance |
| No empirical test of structural equivalence (AT ↔ AI) | Applause/DubBot industry framing, nohacks.co (agent-side constraint) | First empirical test via environment-side manipulation |
| ADeLe measures task demand, not environment quality | ADeLe 18 dimensions (Nature 2026) | Environment-side measurement; enables performance = task × environment × agent |
| No dose-response model for a11y → AI agent performance | ARIA over-annotation harms, CV/ASR threshold effects | First empirical evidence of threshold effect for AI agents |
| **No study of SoM staleness under DOM mutation** | **SeeAct (53% grounding error), Execution Gap concept** | **First controlled evidence: DOM de-semanticization causes phantom bids - overlay false affordances** |
| **False affordance theory unconnected to agent failures** | **Visual confused deputy (security framing), A4Bench (physical affordances)** | **Formal mapping of Gaver's taxonomy to agent failure modes; novel "overlay false affordance" category** |
| **No unified framework for constraint-driven agent performance** | **AgentOccam (deliberate pruning), Prune4Web (DOM reduction)** | **Duality framework: same DOM change → failure (phantom bids) OR success (forced simplification); Majumdar's Ω(M) vs √k formal backing** |
| **No environment-side causal evidence for a11y → agent failure** | **A11y-CUA (agent-side: input modality constraint) [77]** | **First controlled DOM manipulation; complements A11y-CUA's agent-side characterization** |

---

## 3. The "Same Barrier" Hypothesis

### 3.1 The Three-Layer Independence of Web Interfaces

Modern web pages are built on three independent layers that can be-and routinely are-completely decoupled:

| Layer | What It Determines | Who Uses It |
|-------|-------------------|-------------|
| **DOM semantic layer** | What an element *is* (button, link, heading) | Screen readers, AI agents (a11y tree) |
| **JavaScript behavior layer** | What an element *does* (click handlers, navigation) | All users (via mouse/keyboard events) |
| **Visual/CSS layer** | What an element *looks like* (color, shape, position) | Sighted users, screenshot-based AI agents |

A `<div>` styled to look like a button with a JavaScript click handler is visually and functionally indistinguishable from a `<button>` for sighted users-but invisible as a button to screen readers and AI agents that read the DOM semantic layer. This decoupling is not an edge case: `<div>` and `<span>` together comprise approximately 40% of all HTML elements on the web (HTTP Archive 2024), and `role="button"` appears on 53-54% of pages, often applied to non-semantic elements (HTTP Archive 2025).

The decoupling is largely unintentional. Modern frontend development is highly abstracted: developers write React/Vue components, not HTML. The framework compiles components into DOM nodes, and developers may never inspect the final HTML output. Combined with historical CSS limitations that encouraged `<div>`-based styling, the result is that most of the web's interactive elements lack proper semantic markup-not because developers chose to exclude assistive technology users, but because the toolchain never surfaced this concern.

### 3.2 Structural Equivalence at the DOM Layer

AI agents and screen reader users face structurally equivalent barriers when the DOM semantic layer is broken:

| Property | Screen Reader User | AI Agent |
|----------|-------------------|----------|
| Perception | Audio translation of A11y Tree | Tokenized ingestion of A11y Tree |
| Failure mode | Cannot find unlabelled elements | Cannot actuate non-semantic elements |
| Workaround | Memorize site-specific tricks | "Experience sedimentation" - cached heuristics |

**Direct evidence**: UC Berkeley and University of Michigan researchers [12] (CHI 2026 / nohacks.co) evaluated Claude 3.5 Sonnet across 60 real-world web navigation tasks. Under standard conditions, the agent achieved 78.33% success; under keyboard-only constraint (simulating screen reader navigation), success dropped to 41.67%, with task completion time doubling from 324s to 650s. Failures mapped to three categories: Perception Gaps (missing ARIA live regions), Cognitive Gaps (illogical DOM structure), and Action Gaps (no keyboard handlers). Crucially, this study constrained the *agent's action space*; our study degrades the *environment's semantic quality* - a complementary and more causally precise manipulation.

**Industry convergence**: Multiple independent sources have arrived at essentially the same conclusion. Applause [48] frames accessibility as "the machine-readable infrastructure that enables AI readiness," calling semantic structure a shared "contract layer" between interfaces and any machine attempting to operate them. DubBot [49] explicitly states "AI systems read web content in ways strikingly similar to how screen readers do." Opus Research [50] applies the "curb-cut effect" to argue that accessibility infrastructure benefits AI agents as an unintended beneficiary group. A CHI 2026 workshop paper [51] formalizes the "dual-audience" problem: interfaces must remain legible to humans while being interpretable by agents.

**Pilot evidence**: Our Pilot 4 results (N=240) provide definitive controlled evidence. When the low variant breaks ARIA tabpanel relationships on ecommerce product pages, the Reviews section becomes invisible in the Accessibility Tree - mirroring exactly how a screen reader user would lose access to the same content. In all 5 traces of ecom:23 low, the agent reports "the review content is not accessible" and fails - not because of reasoning failure, but because the content genuinely does not exist in its perceptual space. The Plan D variant injection mechanism ensures this degradation persists even after agent-triggered page reloads (verified: 33/33 goto traces show persistent degradation), eliminating the confound of variant escape that affected Pilot 3b.

**The pseudo-compliance trap**: Incorrect ARIA can be worse than absent ARIA. The WebAIM Million 2025 report found that pages utilizing ARIA average 57 detectable errors vs. 27 on non-ARIA pages. When `role="button"` is applied to a `<div>` without keyboard handlers, agents perceive a valid target, attempt actuation, register no state change, and enter token-draining retry loops. This has direct implications for measurement methodology: we cannot rely solely on syntactic ARIA presence; we must assess whether annotations are semantically correct and functionally backed.

### 3.3 Divergence at the ARIA Annotation Layer

The "Same Barrier" hypothesis requires an important refinement based on our PSL experiment (§5.2.5). While the hypothesis holds at the **DOM structural level** (element replacement, semantic relationship removal), it **diverges at the ARIA annotation level** due to differences between BrowserGym's a11y tree serialization and real screen reader behavior:

| ARIA Manipulation | Real Screen Reader | BrowserGym Agent |
|-------------------|--------------------|------------------|
| `aria-hidden="true"` | Element completely invisible | Element shows as `hidden=True` with bid preserved, clickable |
| `role="presentation"` | Semantic role removed | Role may still appear in serialized tree |
| `<a>` → `<span>` (structural) | Not a link | Not a link ✔ (consistent) |

This means BrowserGym-based agents have an unintended "superpower" at the ARIA layer: they can perceive and interact with elements that real screen reader users cannot. All BrowserGym-based benchmarks (WebArena, VisualWebArena, WorkArena) therefore **systematically overestimate** agent robustness to ARIA-level accessibility failures.

**Implications for our results**: Our measured effects are a **conservative lower bound**. The true impact of accessibility degradation on agents using faithful screen reader representations would be equal or greater. This conservatism strengthens rather than weakens our claims-and motivates the SRF (Screen-Reader-Faithful) serialization proposal (§7.2) to correct this systemic bias across the entire BrowserGym ecosystem.

**Implications for practice**: This divergence does not mean companies can ignore accessibility because "AI can work around ARIA problems." The DOM structural barriers that affect both screen readers and AI agents-missing semantic elements, broken relationships, div soup-represent the vast majority of real-world accessibility failures (94.8% of top websites, WebAIM 2025). ARIA-level "workarounds" only help with a narrow subset of issues. More fundamentally, a web environment that AI agents struggle with despite their ARIA-level advantages will be even more hostile to human assistive technology users.

**Three-severity framework operationalization (from §5.3.1 ecological validity study)**: Our experimental data and ecological survey converge on a three-level severity framework that operationalizes the Same Barrier hypothesis:

| Severity | Layer | Examples | Real-world prevalence | Agent impact |
|----------|-------|----------|-----------------------|--------------|
| **L1: Decorative** | ARIA + metadata | Missing img alt, html lang, heading order | 70.6% of sites | Zero (Δ=0pp) |
| **L2: Annotation** | ARIA labels/associations | Missing aria-label, aria-live, form labels | 20.6% of sites | Zero for strong models, moderate for weak (Δ=0pp Claude, Δ38.5pp Llama) |
| **L3: Structural** | DOM element type | link→span, nav→div, heading→div | **83.3% of sites** | **Fatal** (Δ48.6pp Claude, Δ33.9pp Llama) |

L3 is the only severity level where the Same Barrier hypothesis manifests in practice under current BrowserGym serialization. L1 and L2 violations are invisible to agents due to the BrowserGym divergence described above. This does not invalidate the hypothesis—it means the barrier is specifically structural, and real screen reader users face the same (or worse) structural barriers.

---

## 4. Research Questions

- **Primary RQ**: Is website accessibility a statistically significant predictor of AI agent task success, after controlling for site complexity, sector, and agent architecture?
- **Secondary RQ**: Which specific WCAG 2.2 criteria are most predictive of agent success?
- **Exploratory RQ**: If data permits, can we identify agent-critical accessibility properties not covered by current WCAG 2.2? (Initial characterization only; detailed ACAG framework development is future work.)

---

## 5. Methodology

### 5.1 Design Overview

Existing web agent benchmarks adopt an *agent-centric* paradigm: the web environment is held constant while agent architectures and models vary. We invert this design: holding the agent constant while programmatically manipulating web environment properties via DOM-level variant injection - an *environment-centric* evaluation paradigm that enables causal investigation of how frontend characteristics affect agent performance.

This paradigm shift yields a dual-track multifactorial study with log-based failure attribution and multi-tier accessibility measurement. Track A provides primary causal evidence; Track B provides ecological validation. The underlying experimentation framework - programmatic DOM manipulation with persistent variant injection - is designed to be reusable: accessibility is the first independent variable we study, but the same infrastructure supports investigation of any frontend property (interaction latency, dark patterns, internationalization, visual layout).

### 5.2 Track A: Controlled A/B Experiments (Primary Evidence)

**Base**: WebArena's four self-hosted applications (Reddit, GitLab, CMS, E-commerce) - existing task definitions, evaluation scripts, and baseline results.

**Manipulation**: Four A11y variants per environment:

| Variant | Manipulation | Level |
|---------|-------------|-------|
| **Low** | Strip ARIA, replace semantic HTML with `<div>`/`<span>` (F42), disable keyboard handlers (F55), inject unbridged Shadow DOM, break semantic relationships (e.g., tabpanel associations), duplicate IDs (F77) | 0 |
| **Medium-Low** | ARIA attributes present but functionally incorrect - event handlers missing, pseudo-compliance traps (correct role, no behavior) | 0.5 |
| **Base** | Original WebArena (as-is) | 1 |
| **High** | Full ARIA, semantic HTML5, keyboard navigability, landmarks, all axe-core violations fixed | 2 |

**Implementation - Plan D**: Variant injection uses Playwright's `context.route("**/*")` to intercept all HTML responses at the network level, injecting variant-specific patch scripts before the page reaches the browser's rendering engine. Patches execute via a deferred strategy: `window.load` event + 500ms delay + MutationObserver guard - ensuring manipulations persist through JavaScript framework re-rendering (Magento KnockoutJS, Postmill templates). A `[data-variant-revert]` sentinel attribute on modified elements enables the MutationObserver to detect and re-apply patches if the framework restores original DOM structure. This design was developed through iterative failure of three prior mechanisms (Pilots 2-3b) and verified with 33/33 goto-triggered navigation traces in Pilot 4. The variant injection system is decoupled from accessibility-specific patches - swapping the injected scripts enables experimentation with arbitrary frontend properties.

**Relationship to Ma11y** [30]: Our variant injection shares conceptual roots with Ma11y's mutation operators (ISSTA 2024), which inject WCAG failure techniques into the DOM using Puppeteer. Several Ma11y operators (F2: heading→paragraph, F68: label removal, F91: th→td, F96: aria-label corruption) directly correspond to our low variant manipulations, providing methodological validation from the software testing community. However, Ma11y evaluates whether accessibility *testing tools* detect mutations; we evaluate whether mutations cause AI *agent task failures* - the same mutation methodology applied to a fundamentally different dependent variable.

**Scope**: 4 apps × 4 variants × 3-5 tasks × 3 agent types = 144-240+ test cases. Same content, same tasks - **only A11y varies**. Full design with CUA: 6 tasks × 4 variants × 3 agents × 5 reps = **360 cases** (240 complete for text-only + SoM; CUA 120 cases pending).

**Agent config**: Three agent types spanning the full observation modality spectrum:

| Agent | Observation | Execution | LLM | Purpose |
|-------|------------|-----------|-----|---------|
| **Text-only** | Accessibility Tree (serialized) | BrowserGym action API (bid-based) | Claude Sonnet 3.5 via LiteLLM → Bedrock | Primary condition - directly tests a11y quality impact |
| **Vision-only (SoM)** | Screenshot + Set-of-Mark overlay | BrowserGym action API (bid-based) | Claude Sonnet 3.5 via LiteLLM → Bedrock | Tests DOM dependency of "visual" agents |
| **CUA (coordinate)** | Raw screenshot (no SoM, no DOM) | Pixel coordinates via Playwright mouse/keyboard | Claude Sonnet 4 via direct Bedrock Converse API (`computer_20250124` tool) | True visual control - zero DOM dependency |

The CUA agent runs a self-contained agent loop in `cua_bridge.py` (350 lines), calling Bedrock directly via boto3 (bypassing LiteLLM, which cannot forward `computer_use` tool definitions). Coordinate actions (click, scroll, type) operate on raw pixel coordinates with no bid resolution. Plan D variant injection still applies - `context.route()` intercepts HTML responses regardless of observation mode - but CUA cannot "see" semantic changes, only visual layout changes (if any).

**Smoke test verified**: CUA successfully completed ecom:23 at base variant (11 steps, 139K tokens, reward=1.0) - clicked Reviews tab via coordinates, scrolled through 12 reviews, identified correct answer. Uses ~2× tokens vs text-only (screenshots are expensive, ~1600 tokens each, 2 per step) and takes more steps (11 vs ~5) as expected.

Platform: BrowserGym with custom Python bridge (browsergym_bridge.py, 800+ lines) handling variant injection, shopping authentication, and observation extraction. Each task × variant × agent × 5 repetitions.

**Why Track A is primary**: It provides the cleanest causal test. The reviewer's core question - "how do you know failure is due to A11y, not confounds?" - is answered by experimental control. Ground-truth A11y levels eliminate measurement error in the independent variable.

#### 5.2.1 Pilot Results (Pilots 2-3b, March-April 2026)

**Pilot 2** (81 runs: 9 tasks × 3 variants × 3 reps): Established core finding. Low 37.0% vs Base 74.1% (χ2=7.50, p=0.006, Cramér's V=0.37). Identified token inflation and content invisibility pathways. Base vs High not significant (p=0.25).

**Pilot 3a** (120 runs: 6 tasks × 4 variants × 5 reps, text-only): Introduced medium-low "pseudo-compliance" variant and increased reps. Core gradient replicated: low 20.0% → medium-low 86.7% → base 90.0% → high 93.3%. Low vs base: χ2=29.4, p<0.001. Monotonic gradient confirmed. Two new operators added from Ma11y mapping (F42: link→span, F77: duplicate IDs, F55: focus blur).

**Pilot 3b** (213 runs: text-only 120 + vision-only 93): Macro-level replication confirmed: overall text-only success 71.7% vs 72.5% (Δ<1pp). Vision-only low vs base: χ2=10.02, p=0.002, Cramér's V=0.45. Identified goto() escape vulnerability (agent-triggered page reloads clearing variant patches), motivating Plan D injection mechanism.

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

**Primary statistical test**: Low vs Base: χ2=24.31, p<0.000001, Cramér's V=0.637, Fisher's exact p=0.000001.
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

\* ecom:24 low success is a vacuous truth - agent cannot access reviews, answer "no unfair pricing" happens to be correct by chance (see §5.2.3).
† reddit:67 base/high failures are context overflow (F_COF), not accessibility-caused - see §5.2.3.

**Vision-Only Results (n=120)**:

| Variant | Success | Total | Rate |
|---------|---------|-------|------|
| low | 0 | 30 | 0.0% |
| medium-low | 7 | 30 | 23.3% |
| base | 6 | 30 | 20.0% |
| high | 9 | 30 | 30.0% |
| **Overall** | **22** | **120** | **18.3%** |

Vision-only low vs base: χ2=6.67, p=0.010, Cramér's V=0.333. **Significant.**

Vision success concentrated in exactly 2 of 6 tasks: ecom:24 (10/20=50%, simple scroll+read) and reddit:67 (12/20=60%, read post titles from list). All tasks requiring multi-step navigation or widget interaction score 0/20.

**Interaction Effect (Causal Inference)**:
- Text gradient (base-low): 63.3pp
- Vision gradient (base-low): 20.0pp
- **Interaction**: 43.3pp - text-only agents are disproportionately affected, confirming the Accessibility Tree as the primary causal mechanism.
- At non-low variants (where SoM labels are intact): text-only 87.8% vs vision-only 24.4% = 63.3pp advantage, confirming the a11y tree's substantial informational superiority.

**Token Analysis**:

| Variant | Text Avg | Text Median | Vision Avg | Vision Median |
|---------|----------|-------------|------------|---------------|
| low | 172,002 | 113,743 | 50,585 | 51,621 |
| medium-low | 93,996 | 42,763 | 34,283 | 34,350 |
| base | 134,833 | 43,988 | 28,486 | 20,384 |
| high | 149,809 | 44,318 | 36,131 | 25,468 |

Text-only uses 2.55× more tokens than vision-only on average (expected: a11y tree is verbose). Low variant inflates text-only tokens by 27% vs base. Vision-only takes more steps (12.8 vs 7.4 avg) despite fewer tokens - each step is slower (screenshot rendering + SoM overlay).

**Outcome Breakdown**:

| Outcome | Text-Only | Vision-Only |
|---------|-----------|-------------|
| success | 86 | 22 |
| failure | 21 | 54 |
| timeout | 3 | 4 |
| partial_success | 10 | 40 |

Vision-only's dominant failure mode is partial_success (40/120=33%) - agents make progress but cannot complete tasks. Text-only failures are more binary.

#### 5.2.3 Pilot 4 Deep Dive Analysis

**reddit:67 Anomaly - Context Overflow, Not Accessibility**

Base/high variants show only 20% success (1/5 each) despite full accessibility. Deep dive reveals: 4/5 failures at both variants are F_COF (context overflow). The agent clicks into individual post detail pages, each loading 100+ comments → a11y tree expands to 608K tokens → LLM call fails ("LLM call failed" error).

Medium-low achieves 100% (5/5) because the degraded DOM prevents the agent from clicking into posts (links converted to StaticText), forcing it to read book titles from the forum list page - completing the task in 3 steps and 43K tokens. This is **forced strategy simplification**: the same DOM change that causes failure elsewhere (content invisibility) here acts as a beneficial constraint by eliminating a harmful affordance (deep-linking into verbose pages).

**Key numbers**: base/high failure traces average 503K-609K tokens. Medium-low success traces average 137K tokens. This is a 14× efficiency difference. The "paradox" is that less accessible DOM can improve performance when the accessible version provides an affordance trap.

**Sensitivity analysis**: Excluding reddit:67, low vs base remains significant: low 1/5 (20%) vs base 5/5 (100%), χ2=6.67, p=0.010, V=0.816.

**ecom:24 Low - Vacuous Truth**

The single success (1/5) at low variant is a false positive. The agent's answer: "No reviewers found mentioning unfair pricing - the review content is not accessible on this page." Ground truth: no reviewers mention unfair pricing. The agent gave the correct answer but for the wrong reason - it could not access reviews due to content invisibility, and the answer "no" happened to be true. All 5 traces show tablist=False, tabpanel=False, confirming Plan D is working.

**admin:4 High - LLM Reasoning Error**

The single failure (4/5=80%) at high variant: agent sorted by revenue instead of by quantity. Token count (130K) matches successful traces. Not related to ISSUE-BR-4 or skip-link accumulation. Pure F_REA (reasoning error).

**reddit:29 High - Counting Error**

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

- **Mode A** (Magento): Elements exist in DOM but with `browsergym_set_of_marks="0"` - click resolves but returns "element is not visible." Agent sees label in screenshot, clicks it, gets error, retries indefinitely.
- **Mode B** (Reddit/Postmill): Elements completely removed from interactive set - click returns "Could not find element with bid." Agent clicks non-existent bid 20+ times in a row (e.g., reddit_low_67_1_1: 25 consecutive failed clicks on bid "229").

Both modes produce 0% success because the agent cannot interact with any navigation elements under low variant.

#### 5.2.4 CUA Full Results (120/120 Cases, April 8, 2026)

CUA coordinate-based agent (Claude Sonnet 3.5, direct Bedrock Converse API, `computer_20250124` tool) completed across full design matrix. Duration: 234.1 min.

**Three-Agent Comparison Table**:

| Variant | Text-Only (a11y tree) | Vision-Only (SoM) | CUA (coordinates) |
|---------|----------------------|--------------------|--------------------|
| low | 7/30 (23.3%) | 0/30 (0.0%) | 20/30 (66.7%) |
| medium-low | 30/30 (100.0%) | 7/30 (23.3%) | 30/30 (100.0%) |
| base | 26/30 (86.7%) | 6/30 (20.0%) | 29/30 (96.7%) |
| high | 23/30 (76.7%) | 9/30 (30.0%) | 30/30 (100.0%) |
| **Overall** | **86/120 (71.7%)** | **22/120 (18.3%)** | **109/120 (90.8%)** |

CUA low vs base: χ2=9.02, p=0.0027, Cramér's V=0.388 - significant but substantially smaller than text-only (V=0.637).

**Task × Variant Matrix (CUA)**:

| Task | low | medium-low | base | high |
|------|-----|------------|------|------|
| admin:4 | 5/5 (100%) | 5/5 (100%) | 4/5 (80%) | 5/5 (100%) |
| ecom:23 | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecom:24 | 4/5 (80%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| ecom:26 | 4/5 (80%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| reddit:29 | **0/5 (0%)** | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |
| reddit:67 | 2/5 (40%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) |

**Three-Agent Causal Decomposition**:

| Pathway | Agent Comparison | Drop (pp) |
|---------|-----------------|-----------|
| **Total effect** | Text-only: base→low | 63.3 |
| **Functional + visual** | CUA: base→low | 30.0 |
| **A11y tree pathway** | Total - (Functional + visual) | **33.3** |

The 33.3pp difference is attributable to the Accessibility Tree pathway - information that text-only agents receive but CUA never sees. This "attributable fraction" method is analogous to epidemiological decomposition.

**CUA Failure Analysis (11 failures, all 30-step timeouts)**:

| Task | Low Failures | Mechanism |
|------|-------------|-----------|
| reddit:29 | 5/5 (0% success) | link→span breaks SPA navigation; CUA cannot use goto(), must click visually; Postmill's JS event delegation doesn't fire on `<span>` elements |
| reddit:67 | 3/5 (40% success) | Same link→span navigation failure |
| ecom:24 | 1/5 (80% success) | Tab panel cross-layer breakage |
| ecom:26 | 1/5 (80% success) | Tab panel cross-layer breakage |
| admin:4 base | 1/5 (80% success) | UI complexity (dropdown), not a11y-related |

**The reddit:29 inversion is the most analytically important result**: Text-only achieves 4/5 at low (using `goto()` to bypass broken links); CUA achieves 0/5 (must click visually, but link→span breaks Postmill's JS event delegation). This proves the CUA 30pp drop is driven by **functional breakage** (href removal), not visual or semantic changes.

**Cross-Layer Confound Analysis**: The low variant's 13 patches produce three impact categories:

| Category | Patches | Text-Only | CUA | SoM |
|----------|---------|-----------|-----|-----|
| **Pure semantic** | Delete alt, aria-label, lang, tabindex, heading roles | ✅ affected | ❌ unaffected | ⚠️ SoM labels may reduce |
| **Cross-layer, functional preserved** | label.remove(), thead→div | ✅ | ⚠️ visual changes | ⚠️ |
| **Functional breakage** | link→span (href removed), Shadow DOM | ✅ | ✅ navigation broken | ✅ phantom bids |

CUA's 30pp drop is attributable to category 3. The additional 33.3pp for text-only reflects categories 1+2.

**Token Consumption**:

| Variant | CUA Mean | Text-Only Mean | Ratio |
|---------|----------|----------------|-------|
| low | 366,858 | 172,002 | 2.13× |
| medium-low | 170,740 | 93,996 | 1.82× |
| base | 178,417 | 134,833 | 1.32× |
| high | 170,378 | 149,809 | 1.14× |

CUA low variant consumes 37.5% of total experiment time despite being only 25% of cases. Excluding failures, CUA low successes average ~300K tokens (1.7× base).

#### 5.2.5 Pure-Semantic-Low (PSL) Experiment (April 7, 2026)

**Motivation**: CUA's unexpected degradation under low variant revealed a confound: the low variant's DOM structural changes (link→span, label.remove(), Shadow DOM) simultaneously degrade the a11y tree, visual rendering, and interactive functionality. To isolate the a11y tree as the causal mechanism, we designed a **Pure-Semantic-Low (PSL) variant** that degrades only semantic annotations without altering DOM structure, visual rendering, or interactive functionality.

**PSL patch design** (11 patches vs low's 13):

| # | Low Variant | PSL Variant | Rationale |
|---|------------|-------------|-----------|
| 1 | `<nav>` → `<div>` | `<nav role="presentation">` | Preserve CSS (nav selector matches), remove landmark from a11y tree |
| 2 | Delete all aria-* | Delete all aria-* | Already pure-semantic ✅ |
| 3 | `label.remove()` | `aria-hidden="true"` + remove `for=` | Label text visually present, but hidden from a11y tree |
| 4 | Delete keyboard handlers | **Removed** | Pure functionality, not semantic |
| 5 | Shadow DOM wrapping | `aria-hidden="true"` | Element visible and clickable, but hidden from a11y tree |
| 6 | `<h1>` → `<div style=...>` | `<h1 role="presentation">` | Preserve heading CSS, remove heading role from a11y tree |
| 7 | Delete img alt | Delete img alt | Already pure-semantic ✅ |
| 8 | Delete tabindex | `role="presentation"` | Don't change tab order (functional), remove semantics |
| 9 | thead/th → div/td | `<table role="presentation">` | Preserve table layout, remove table semantics from a11y tree |
| 10 | Delete html lang | Delete html lang | Already pure-semantic ✅ |
| 11 | `<a>` → `<span style=...>` | `<a role="presentation">` | **Key patch**: link visually present, clickable, href works - but a11y tree shows plain text, not link |
| 12 | Duplicate IDs | Duplicate IDs | Already pure-semantic ✅ |
| 13 | onfocus blur | **Removed** | Pure functionality, not semantic |

**Core mechanism**: Three ARIA attributes (`role="presentation"`, `aria-hidden="true"`, attribute deletion) applied to degrade the a11y tree while preserving DOM structure, CSS rendering, and JavaScript behavior. Visual output: zero change. Interactive functionality: zero change. A11y tree: severe degradation (landmarks gone, headings gone, links de-semanticized, labels hidden, table structure lost).

**Result: PSL had no effect on agent performance.** 6 smoke-test cases: 5/6 success, with the single failure (reddit:67) caused by F_COF context overflow - the same failure mode observed at base/high variants, unrelated to PSL patches.

**Root cause - BrowserGym a11y tree serialization divergence**:

| Attribute | Real Screen Reader | BrowserGym Serialization |
|-----------|-------------------|--------------------------|
| `aria-hidden="true"` | Element completely invisible | Element shows as `link 'text', hidden=True` - **bid preserved, role preserved, clickable** |
| `role="presentation"` | Semantic role removed | Role **may still appear** in serialized tree |
| Missing `alt` | Image not readable | Image not readable ✅ (consistent) |
| `<a>` → `<span>` (structural) | Not a link | Not a link ✅ (consistent) |

**Key finding: BrowserGym's a11y tree serialization is more permissive than real screen readers.** It exposes `hidden=True` elements with full bids and roles, allowing agents to interact with elements that would be invisible to screen reader users. This means:

1. **The "Same Barrier" hypothesis holds at the DOM structural level** (link→span, element removal) but **diverges at the ARIA semantic level** (aria-hidden, role=presentation). Agent and screen reader experience the same barriers when DOM structure is broken, but agents receive more information than screen readers when only ARIA annotations are degraded.

2. **Current low variant's effectiveness comes from DOM structural changes, not ARIA semantic annotations.** The 13 patches in the low variant include both structural (link→span, label.remove, Shadow DOM) and semantic (delete aria-*, role changes) operations. PSL isolates the semantic-only subset and shows it has no effect - confirming that the structural changes are the active ingredient.

3. **This is a benchmark-level finding**: All BrowserGym-based agent evaluations (WebArena, VisualWebArena, WorkArena) use the same a11y tree serialization. The divergence between BrowserGym's serialization and real screen reader behavior means these benchmarks may systematically overestimate agent robustness to ARIA semantic degradation.

**Proposed follow-up - Screen-Reader-Faithful (SRF) serialization**: Modify the BrowserGym bridge to filter out `hidden=True` elements before serialization, matching real screen reader behavior. Re-run PSL under SRF serialization. If text-only agent then degrades → confirms that the divergence is the sole explanation, and the Same Barrier hypothesis holds at the ARIA level when the observation pipeline faithfully models screen reader behavior.

#### 5.2.6 Task Expansion: 6 → 13 Tasks (Claude Sonnet, April 11-12, 2026)

**Motivation**: The initial 6-task design covered 3 applications (ecommerce, admin, reddit) but only 2 tasks per app. To strengthen generalizability and statistical power, we expanded to 13 tasks across 4 applications (adding gitlab) with 7 new tasks: gitlab:132, gitlab:293, gitlab:308, admin:41, admin:94, admin:198, ecommerce:188.

**Task selection criteria**: (1) Each task uses a unique WebArena template (avoid inflating N without increasing task diversity); (2) string_match evaluation (deterministic ground truth); (3) require_reset=false (avoid state pollution between reps); (4) No date/time-dependent calculations or volatile pricing data; (5) Base variant verified before inclusion (ground truth not stale).

**Results (140 new cases: 7 tasks × 4 variants × 5 reps)**:

| Variant | Success | Total | Rate |
|---------|---------|-------|------|
| low | 18 | 35 | 51.4% |
| medium-low | 35 | 35 | 100.0% |
| base | 35 | 35 | 100.0% |
| high | 35 | 35 | 100.0% |

**Step function perfectly replicated**: low 51.4% → medium-low 100% (+48.6pp jump). Zero failures at ml/base/high across all 7 new tasks.

**Task × Variant Matrix (Expansion Tasks)**:

| Task | low | ml | base | high | Failure mechanism |
|------|-----|----|------|------|---------|
| admin:41 | 5/5 (100%) | 5/5 | 5/5 | 5/5 | Control (trivial, 1-step) |
| gitlab:132 | 5/5 (100%) | 5/5 | 5/5 | 5/5 | Control (data visible without navigation) |
| ecom:188 | 5/5 (100%) | 5/5 | 5/5 | 5/5 | Control (data visible) |
| admin:94 | 3/5 (60%) | 5/5 | 5/5 | 5/5 | Stochastic strategy variation (goto URL construction) |
| admin:198 | 0/5 (0%) | 5/5 | 5/5 | 5/5 | Structural infeasibility (KnockoutJS grid invisible) |
| gitlab:293 | 0/5 (0%) | 5/5 | 5/5 | 5/5 | Structural infeasibility (search autocomplete destroyed) |
| gitlab:308 | 0/5 (0%) | 5/5 | 5/5 | 5/5 | Structural infeasibility (Contributors chart invisible) |

**Deep dive findings for expansion tasks**:

- **gitlab:293 (0/5 low)**: Deterministic failure with near-zero variance (token std dev = 2.0 across 5 traces). Dual failure mechanism: (a) link→span removes all search result links; (b) entire ARIA autocomplete infrastructure destroyed (live region, menuitem, search landmark absent). Agent never receives "Results updated" feedback. All 5 traces follow identical 3-step pattern: click search → type query → premature termination. Base variant completes in 6 steps via autocomplete menuitem click.

- **gitlab:308 (0/5 low)**: Contributors page renders via JavaScript SVG charts that become invisible in the a11y tree under low variant. All 5 traces: agent finds repo, navigates to Contributors page, observes empty content, falls back to manual commit counting from first page of commit log. This produces recency-biased wrong answers ("Cole Bemis" or "Mike Perrotti" instead of correct "Shawn Allen"). Token inflation: 225K-514K vs 80K base (2.8×-6.4×). Auto-classifier labeled F_COF (0.95 confidence) but correct classification is F_SIF - information insufficiency, not context overflow.

- **admin:94 (3/5 low)**: Magento admin search broken under low variant. The 3 successes all discover a creative workaround: constructing direct URL `goto("...invoice_id/000000001/")`. The 2 failures loop on filter/search buttons indefinitely. This is stochastic strategy variation - same model, same observations, different sampling outcomes determine whether the LLM generates the URL construction insight. Token inflation: 8.5× for successes (182K vs 21K base).

- **admin:198 (0/5 low)**: Magento KnockoutJS data grid renders as empty LayoutTable ("We couldn't find any records" despite "308 records found") + all toolbar buttons (Filters, Search, Default View) lose bid attributes. Two-layer blockade: data invisible AND tools inoperable. Agent exhausts 30 steps cycling through refresh/filter attempts.

**Combined Claude 13-task results (Pilot 4 + Expansion, N=500)**:

| Variant | Text-Only | SoM | CUA |
|---------|-----------|-----|-----|
| low | 25/65 (38.5%) | 0/30 (0%) | 20/30 (66.7%) |
| medium-low | 65/65 (100%) | 7/30 (23.3%) | 30/30 (100%) |
| base | 61/65 (93.8%) | 6/30 (20.0%) | 29/30 (96.7%) |
| high | 58/65 (89.2%) | 9/30 (30.0%) | 30/30 (100%) |

*Note: SoM and CUA data is from original 6 tasks only (Pilot 4). Text-only combines original 6 tasks + 7 expansion tasks.*

#### 5.2.7 Cross-Model Replication: Llama 4 Maverick (260 Cases, April 13, 2026)

**Motivation**: Demonstrating that accessibility effects generalize beyond a single model family (Anthropic Claude) is critical for the paper's claims. We selected Meta's Llama 4 Maverick - an open-source model from a completely different training pipeline - accessed via AWS Bedrock.

**Design**: 13 tasks × 4 variants × 5 reps = 260 cases, text-only agent only. Duration: 242.5 minutes.

**Results**:

| Variant | Success | Total | Rate |
|---------|---------|-------|------|
| low | 24 | 65 | 36.9% |
| medium-low | 40 | 65 | 61.5% |
| base | 46 | 65 | 70.8% |
| high | 49 | 65 | 75.4% |

**2×4 Factorial Design (Model × Variant)**:

| | low | medium-low | base | high |
|---|---|---|---|---|
| **Claude Sonnet** (13 tasks) | 38.5% | 100% | 93.8% | 89.2% |
| **Llama 4 Maverick** (13 tasks) | 36.9% | 61.5% | 70.8% | 75.4% |

**Key findings**:

1. **Model-dependent dose-response profiles**: Claude shows a **step function** (low catastrophically fails, ml/base/high all near-perfect). Llama 4 shows a **gradient** (monotonic improvement from low to high). This interaction effect suggests that stronger models can compensate for L2 annotation-level degradation (Claude: ml=100%) while weaker models cannot (Llama: ml=61.5%). Both models fail under L3 structural degradation (low).

2. **🔥 Forced simplification cross-model replication (reddit:29)**: Both models show paradoxical low > base inversion. Claude: low 80% > base 40%. Llama: low 40% > base 0%. Mechanism identical across model families: base variant allows agent to follow distracting external links (imgur.com), causing navigation loss. Low variant breaks these links, constraining the search space to productive paths. This cross-model replication rules out model-specific artifacts.

3. **🔥 Model × environment interaction (admin:198)**: Claude: base 100% → high 100% (+0pp from enhancement). Llama: base 40% → high 80% (+40pp from enhancement). **Weaker models benefit more from accessibility enhancement** - the strongest evidence for the business case that accessibility investment disproportionately helps less capable agents.

4. **admin:4 model capability confound**: Llama 4 collapses across all variants (0/0/0/1) because it cannot operate Magento's `<select>` combobox - a model capability issue, not an accessibility effect. This task is flagged as a model-capability confound and analysis is reported both inclusive and exclusive of this task.

5. **ecom:24/26 non-monotonic patterns**: Llama 4 shows format mismatch (empty string vs "N/A") and understanding threshold effects. These are model-specific capability issues, not accessibility signals, and are controlled for in cross-model comparison.

#### 5.2.8 Combined Experiment Summary (N=1,040)

**Total experimental corpus**: 360 (Pilot 4: 6 tasks × 4 variants × 3 agents × 5 reps) + 140 (Expansion Claude text-only: 7 tasks × 4 variants × 5 reps) + 260 (Llama 4: 13 tasks × 4 variants × 5 reps) + 140 (Expansion SoM: 7 tasks × 4 variants × 5 reps) + 140 (Expansion CUA: 7 tasks × 4 variants × 5 reps) = **1,040 total cases across 9 experimental rounds**.

| Experiment | Cases | Breakdown |
|-----------|-------|--------|
| Pilot 4 text-only + SoM | 240 | 6 tasks × 4 variants × 5 reps × 2 agents |
| Pilot 4 CUA | 120 | 6 tasks × 4 variants × 5 reps × 1 agent |
| Expansion Claude text-only | 140 | 7 tasks × 4 variants × 5 reps |
| Expansion Llama 4 text-only | 260 | 13 tasks × 4 variants × 5 reps |
| Expansion SoM | 140 | 7 tasks × 4 variants × 5 reps |
| Expansion CUA | 140 | 7 tasks × 4 variants × 5 reps |
| **Grand Total** | **1,040** | **13 tasks × 4 agents × 4 variants × 5 reps** |

**Consistency across rounds**: The low-vs-base degradation is significant in every round: Pilot 2 p=0.006, Pilot 3a p<0.001, Pilot 3b p<0.001, Pilot 4 p<0.000001, Expansion p<0.001, Llama 4 p<0.001. Effect sizes range from Cramér's V=0.37 (Pilot 2, 81 cases) to V=0.637 (Pilot 4, 120 cases).

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

#### 5.2.9 Vision Expansion: SoM + CUA on 13 Tasks (280 Cases, April 14, 2026)

Two overnight experiment runs completed the vision-agent expansion: SoM and CUA each ran 140 cases across 7 expansion tasks (admin:41, admin:94, admin:198, ecom:188, gitlab:132, gitlab:293, gitlab:308). Combined with Pilot 4 vision data (6 original tasks), this completes the full 13-task matrix for all four agent architectures.

**CUA Expansion (116/140, 82.9%)**

Per-variant: low 51.4% → ml 97.1% → base 91.4% → high 91.4%. The low→base gap of +40.0pp is consistent with Pilot 4 CUA on the original 6 tasks (+30.0pp). All 17 low-variant failures are cross-layer functional breakage: link→span removes `href`, so clicking sidebar menu items at correct coordinates produces no navigation.

| Task | low | ml | base | high | Notes |
|------|-----|----|------|------|-------|
| ecom:188 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Control — trivial |
| admin:41 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Control |
| admin:94 | 20% (1/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Low: sidebar nav broken |
| admin:198 | 0% (0/5) | 80% (4/5) | 60% (3/5) | 40% (2/5) | **Anomaly** — UI complexity trap |
| gitlab:132 | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Clean |
| gitlab:293 | 40% (2/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) | Low: search broken |
| gitlab:308 | 0% (0/5) | 100% (5/5) | 80% (4/5) | 100% (5/5) | Low: contributors nav destroyed |

**CUA Failure Attribution (24 failures)**: 17 cross-layer functional breakage (all low), 6 UI complexity trap (admin:198: base 2, high 3, ml 1), 1 step budget exhaustion (gitlab:308 base).

**admin:198 CUA anomaly (ml 80% > base 60% > high 40%)**: The inverted pattern reveals a UI complexity confound unrelated to accessibility. Magento's Columns configuration dropdown visually overlaps with the Status filter, trapping CUA in a click loop. The high variant's ARIA enhancements add skip-links that shift element positions, and all 3 high failures show 8–9 `Page.screenshot: Timeout 3000ms exceeded` errors, wasting ~30% of the step budget. Text-only Claude gets 100% at ml/base/high because it reads the a11y tree directly without coordinate ambiguity. This demonstrates that different agent architectures face fundamentally different environmental barriers.

**SoM Expansion (38/140, 27.1%)**

Per-variant: low 8.6% (3/35) → ml 31.4% (11/35) → base 34.3% (12/35) → high 34.3% (12/35). A weak gradient (+25.7pp low→base) exists but is dominated by SoM-specific failures at all variants. At non-low variants, SoM averages only 33.3% — compared to text-only Claude's 100% and CUA's 90.5%.

| Task | low | ml | base | high | Text-only (ref) |
|------|-----|----|------|------|-----------------|
| admin:41 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% all |
| admin:94 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 20% (1/5) | 100% (non-low) |
| admin:198 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% (non-low) |
| ecom:188 | 20% (1/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% all |
| gitlab:132 | 0% (0/5) | 60% (3/5) | 60% (3/5) | 0% (0/5) | 100% all |
| gitlab:293 | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 100% (non-low) |
| gitlab:308 | 0% (0/5) | 60% (3/5) | 60% (3/5) | 60% (3/5) | 100% (non-low) |

**SoM Five Failure Modes (102 failures)**: (1) Phantom bid loop ~48% — agent clicks SoM label, gets "not found" or "not visible," retries indefinitely. Dominant in ecom:188, gitlab:308. (2) Visual data misread ~26% — agent reaches correct page but extracts wrong value from screenshot (admin:41 reads "tanks" instead of "hollister"). (3) Form interaction failure ~17% — agent identifies input visually but fill() fails on Vue.js/KnockoutJS components (gitlab:293 all variants). (4) Exploration spiral ~13% — clicks succeed but agent never converges (gitlab:132 high, admin:94). (5) Navigation failure ~13% — sidebar phantom bids block all routes (admin:198 low, admin:94 low).

**Key SoM anomalies**:
- **gitlab:293 0% ALL variants** — The clearest SoM limitation. Vue.js re-renders the search component on focus, invalidating the bid between screenshot capture and action execution. This is the "Execution Gap" (Shi et al., 2025) in its purest form — no accessibility improvement can fix this.
- **admin:41 0% ALL variants** — The task is trivially easy for text-only (1 step) but SoM visually misreads the dense Magento dashboard data table at every variant.
- **gitlab:132 high 0% (base 60%)** — Enhanced ARIA creates more SoM labels, inflating the visual action space. Agent explores breadth-first instead of using goto() URL fallback. ARIA over-annotation paradoxically hurts SoM.
- **ecom:188 low 20% > others 0%** — Forced simplification via SoM overlay density reduction (92 vs 122 elements), eliminating phantom bid targets.
- **admin:94 high 20% (others 0%)** — ARIA enhancement provides just enough structure for SoM in rare cases.

**Cross-Agent Comparison (All 4 Agents on 7 Expansion Tasks)**

| Variant | Claude-Text | Llama4-Text | Claude-SoM | Claude-CUA |
|---------|-------------|-------------|------------|------------|
| low | 51.4% | 51.4% | 8.6% | 51.4% |
| ml | 100.0% | 88.6% | 31.4% | 97.1% |
| base | 100.0% | 91.4% | 34.3% | 91.4% |
| high | 100.0% | 97.1% | 34.3% | 91.4% |

The accessibility gradient direction (low < base) is consistent across all four agent types. Gradient magnitude varies: text-only shows the largest absolute drop (+48.6pp), CUA matches Llama 4 (+40.0pp), SoM shows the smallest (+25.7pp) because its baseline is so low there is less room to fall.

**Updated Causal Decomposition (Expansion Tasks)**: Text-only low→base: 48.6pp (semantic + functional). CUA low→base: 40.0pp (functional only). Difference: ~8.6pp = pure semantic (a11y tree) pathway. Combined with Pilot 4 (33.3pp semantic + 30.0pp functional), this provides converging evidence that the low variant operates through both semantic and functional channels.

**Combined 13-Task Agent Summary (All Data)**

| Agent | low | ml | base | high | N |
|-------|-----|----|------|------|---|
| Text-only Claude | 38.5% (25/65) | 100% (65/65) | 93.8% (61/65) | 89.2% (58/65) | 260 |
| Text-only Llama 4 | 36.9% (24/65) | 61.5% (40/65) | 70.8% (46/65) | 75.4% (49/65) | 260 |
| SoM Claude | 4.6% (3/65) | 27.7% (18/65) | 27.7% (18/65) | 32.3% (21/65) | 260 |
| CUA Claude | 58.5% (38/65) | 98.5% (64/65) | 93.8% (61/65) | 95.4% (62/65) | 260 |

**Agent Ranking at Non-Low Variants**: (1) Text-only Claude 94.4%; (2) CUA Claude 95.9%; (3) Text-only Llama 4 69.2%; (4) SoM Claude 29.2%. CUA slightly outperforms text-only Claude overall due to immunity to model reasoning errors at base/high (e.g., reddit:67 context overflow). SoM is the weakest by a wide margin but still shows a gradient, confirming DOM semantic changes affect even the weakest observation modality.

**Accessibility Gradient Across All 4 Agent Types (13 Tasks Combined)**

| Agent | Low Rate | Base Rate | Δ (base−low) | Mechanism |
|-------|----------|-----------|--------------|-----------|
| Text-only Claude | 38.5% | 93.8% | **+55.3pp** | A11y tree content invisibility |
| Text-only Llama 4 | 36.9% | 70.8% | **+33.9pp** | Same + weaker model |
| CUA Claude | 58.5% | 93.8% | **+35.3pp** | Cross-layer functional breakage |
| SoM Claude | 4.6% | 27.7% | **+23.1pp** | Phantom bids + baseline weakness |

### 5.3 Track B: Real-World Survey (Ecological Validity)

**Approach**: Core sample of 50 websites across sectors (e-commerce, government, education, SaaS, social media) and geographies (US, EU, China), expandable to 200+ if the pipeline stabilizes. Sites captured via Playwright HAR recording - preserves JavaScript execution and SPA state transitions while eliminating server-side variance.

**Landscape study component**: In addition to agent task probing, Track B includes a large-scale accessibility measurement survey (200+ websites) collecting: axe-core violations by impact level, Lighthouse accessibility scores, composite accessibility scores (same metric as Track A), A11y Tree token counts, DOM structural metrics, and website metadata (category, geography, framework). This provides ecological context: given Track A's causal evidence on what accessibility levels cause agent failure, the landscape study quantifies what proportion of real-world websites fall within those risk zones.

**Task scope**: Information retrieval, navigation, form interaction on recorded paths. Multi-step workflows requiring full server-side state are reserved for Track A.

**Role**: Validates that Track A findings generalize to diverse real-world environments. Primary evidence base for Secondary RQ (WCAG feature importance via SHAP analysis).

#### 5.3.1 Ecological Validity Pilot: 34-Site Automated Survey (April 13, 2026)

**Motivation**: Reviewers will rightly ask whether Track A's programmatic DOM manipulations reflect conditions found on real websites. To directly address this, we conducted an automated survey of 34 websites using axe-core and custom detectors, mapping each of our 13 experimental patches to real-world violation prevalence.

**Method**: Playwright + axe-core headless scan across 34 sites in 6 categories: China e-commerce (6 sites: AliExpress, Bilibili, JD.com, Taobao, XJTLU, Zhihu), global e-commerce (8: Amazon, Walmart, eBay, Best Buy, Wayfair, Newegg, Costco, Target), government (5: whitehouse.gov, gov.uk, usa.gov, service-public.fr, Harvard.edu), media (5: Wikipedia, Medium, NYT, BBC, Reuters), SaaS (6: GitHub, GitLab, Notion, Figma, Vercel, Stripe), and WebArena Docker environments (4: shopping, admin, reddit, gitlab). Each site scanned at login/home page with full JavaScript execution.

**Three-Severity Framework (L1/L2/L3)**:

Our experimental patches map to three severity levels based on their observed agent impact:

| Severity | Description | Patches | Prevalence | Avg violations/site | Agent impact |
|----------|-------------|---------|------------|--------------------|--------------|
| **L1: Decorative** | Visual/metadata attributes | P1 (img alt), P10 (html lang), P6 (heading order) | 70.6% (24/34) | 11.0 | **None** (base→ml = 0pp) |
| **L2: Annotation** | ARIA labels and associations | P2 (aria-*), P3 (label), P12 (duplicate ID) | 20.6% (7/34) | 2.6 | **None** (ml→base = 0pp for Claude) |
| **L3: Structural** | DOM element type and landmarks | P7 (nav→div), P11 (a→span), P5 (h1→div), P9 (table→div) | **83.3% (28/34)** | 37.4 | **Fatal** (low = 51.4% Claude, 36.9% Llama) |

**Key insight**: The three-severity framework explains a puzzle in our Track A data. WebArena's base applications are not perfectly accessible - GitLab's explore page has zero aria-live regions, zero search landmarks, and Magento admin has 207 missing label violations. Yet Claude achieves ~100% success at base. The reason: these are L1/L2 violations, which have **zero agent impact**. Only L3 structural violations (link→span, landmark→div) cause the observed performance collapse.

**Per-Patch Prevalence (Table 3)**:

| Patch | Description | Severity | Sites with violation | Prevalence | Notable sites |
|-------|-------------|----------|---------------------|------------|---------------|
| P7 | landmark→div (missing nav/main/header) | L3 | 28/34 | **82.4%** | AliExpress (22), Bilibili (83), JD.com (19), XJTLU (10) |
| P5 | heading→div (heading hierarchy) | L3 | 21/34 | 61.8% | BBC (6), Best Buy (9), Bilibili (24) |
| P1 | img alt (missing alt text) | L1 | 13/34 | 38.2% | AliExpress (244), Taobao (114), Walmart (23) |
| P3 | label (form labels) | L2 | 7/34 | 20.6% | WebArena admin (207), XJTLU (12) |
| P2 | aria-* (ARIA attributes) | L2 | 4/34 | 11.8% | Bilibili (3), AliExpress (2) |
| P11 | link→span (non-semantic links) | L3 | 4/34 | 11.8% | JD.com (14), Bilibili (8) |
| P10 | html lang | L1 | 3/34 | 8.8% | JD.com, Bilibili, Taobao |
| P4 | keyboard handlers | - | 0/34 | 0% | Not detectable via static scan |
| P6 | duplicate IDs | L2 | 0/34 | 0% | axe-core has no dedicated rule |
| P8 | tabindex | L1 | 0/34 | 0% | Modern frameworks auto-generate unique IDs |
| P9 | table semantics | L3 | 0/34 | 0% | Semantic `<table>` rare in modern web |

**P11 (link→span) prevalence is severely underestimated**: The 11.8% figure captures only explicit `<div onclick>` or `<span onclick>` in the static DOM. JavaScript event delegation (the dominant pattern in React/Vue/Angular frameworks) attaches click handlers to parent containers, making individual elements appear as non-interactive `<div>` or `<span>` in the DOM while being functionally clickable via event bubbling. Real prevalence of non-semantic interactive elements is estimated at 40-60% based on HTTP Archive data showing `role="button"` on 53-54% of pages, often on non-semantic elements.

**P6/P8/P9 zero prevalence is expected**: P6 (duplicate IDs) - axe-core has no dedicated detection rule; P8 (tabindex) - modern frameworks auto-generate unique IDs, making tabindex duplication rare; P9 (semantic tables) - CSS grid/flexbox has replaced `<table>` for layout, and data tables with proper `<thead>`/`<th>` are increasingly uncommon.

**Site-Level Summary (Table 4)**:

| Category | Sites | Avg L3 violations | L3 prevalence | Worst offenders |
|----------|-------|-------------------|---------------|------------------|
| China e-commerce | 6 | 56.0 | 100% (6/6) | Bilibili (350 total), AliExpress (266) |
| Global e-commerce | 8 | 15.3 | 87.5% (7/8) | Walmart (23), Best Buy (18) |
| Government | 5 | 8.4 | 80.0% (4/5) | usa.gov (17), whitehouse.gov (12) |
| Media | 5 | 3.6 | 60.0% (3/5) | BBC (11), NYT (7) |
| SaaS | 6 | 2.8 | 66.7% (4/6) | Notion (8), Figma (6) |
| WebArena Docker | 4 | 52.5 | 50.0% (2/4) | admin (207 labels), reddit (3) |

**Zero-violation sites** (accessibility benchmarks): Wikipedia, GitLab, Harvard.edu, Medium, Stripe, GitHub - all well-known accessibility exemplars.

**WebArena Docker environments vs real-world comparison (Table 5)**:

| Metric | WebArena Docker (4 sites) | Real-world (30 sites) | Match? |
|--------|--------------------------|----------------------|--------|
| L1 violations present | 75% (3/4) | 70% (21/30) | ✅ |
| L2 violations present | 25% (1/4) | 20% (6/30) | ✅ |
| L3 violations present | 50% (2/4) | 86.7% (26/30) | ⚠️ WebArena *underrepresents* L3 |
| Avg total violations | 53.5 | 28.7 | WebArena slightly inflated (admin's 207 labels) |

**Ecological validity conclusion**: WebArena's base environments are L3-clean (all links are real `<a>`, all buttons real `<button>`, landmarks present), which explains why agents achieve ~100% base success despite L1/L2 imperfections. Real-world websites, however, are far more L3-hostile: 83.3% have structural violations, with Chinese platforms and e-commerce sites particularly affected. **Our low variant is not a contrived worst case but a composite of violations routinely found on high-traffic websites.** The 51.4% (Claude) and 36.9% (Llama) success rates under low variant are predictive of what agents would encounter on the ~83% of real websites with L3 structural violations.

### 5.4 Accessibility Measurement (Three-Tier)

| Tier | What It Measures | How | Coverage |
|------|-----------------|-----|----------|
| **1** | Structural compliance | axe-core + Lighthouse (headless Chromium) | ~57% of defect volume (Deque [10]); but only 13% of WCAG 2.2 AA criteria fully auto-detectable [39], and only 50.4% of blind user problems covered by WCAG [31] |
| **2** | Functional semantics (novel) | Programmatic checks: ARIA correctness (role + handler co-presence), meaningful accessible names, keyboard navigability, Shadow DOM bridging, semantic HTML ratio | Fills Tier 1 blind spots |
| **3** | Context-dependent quality | LLM-augmented evaluation + expert manual audit (10% sub-sample, inter-rater κ ≥ 0.80) | Ground truth validation |

**Independent variable operationalization**:
- **Track A**: Categorical (Low / Base / High) - ground truth, no measurement needed. *Note*: Pilot 2 revealed composite score compression (actual range 0.405-0.457 vs designed 0.00-1.00), indicating variant patches were not aggressive enough. Pilot 3 addresses this with enhanced patch scripts targeting wider score differentiation.
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
- Empty / degraded observation - agent receives minimal or empty A11y Tree due to incomplete semantic structure or slow DOM rendering of non-semantic elements, leading to blind navigation and wasted steps
- **Content invisibility** - semantic relationships broken (e.g., tabpanel ARIA associations), causing task-critical content to disappear from the A11y Tree entirely *(added from Pilot 2 trace analysis)*
- **Cross-layer content invisibility** - DOM mutations that affect both semantic AND visual rendering, making content invisible to both text-only and vision agents *(added from Pilot 3b trace analysis)*
- **SoM phantom bid** - DOM de-semanticization creates mismatch between SoM overlay labels (visible in screenshot) and actual interactive elements (absent in DOM), causing persistent click-failure loops for vision agents *(added from Pilot 3b)*
- **Structural infeasibility** - all navigation pathways to task-critical information are blocked; agent exhausts all strategies without reaching target *(operationally defined from Pilot 3b admin:4 low trace analysis)*

**Model-attributed** (control):
- LLM hallucination (fabricated UI element)
- Context overflow (lost track in long workflow)
- Reasoning error (misinterprets task)
- **Harmful affordance trap** - agent selects a valid but suboptimal interaction strategy that leads to context overflow (e.g., clicking into posts with 100+ comments instead of reading titles from list page) *(added from Pilot 3b reddit:67 analysis)*
- Unknown/unclassified (F_UNK) - failure does not match any specific detector pattern *(added from Pilot 2; replaces low-confidence default classification)*

**Platform-attributed** *(added from Pilot 2)*:
- Action serialization error - agent constructs syntactically valid action but platform parser truncates or misparses it (e.g., unbalanced parentheses in message content)

**Environmental**: Anti-bot block, network timeout

**Task feasibility annotation** *(added from Pilot 2)*: Each task × variant combination is annotated for feasibility - whether task-critical information remains accessible in the A11y Tree under that variant's manipulation. Results are reported both inclusive (all tasks) and feasible-only, distinguishing "environment makes task impossible" from "environment makes task harder."

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

**Pilot 4** (34 text-only failures, 98 vision-only failures) + **Expansion** (17 text-only failures) + **Llama 4** (101 text-only failures):

Claude text-only failures by domain and variant (13 tasks, N=260):

| Domain | Type | Count | Primary Variant |
|--------|------|-------|----------------|
| A11y | Content Invisibility | 15 | low (ecom:23/24/26, admin:198, gitlab:308) |
| A11y | Structural Infeasibility | 10 | low (admin:4, gitlab:293, gitlab:308) |
| A11y | Token Inflation (timeout) | 5 | low (admin:4, admin:94) |
| Model | Context Overflow (F_COF) | 8 | base/high (reddit:67) |
| Model | Reasoning Error (F_REA) | 7 | mixed |
| Model | Harmful Affordance Trap | 6 | base/high (reddit:67, reddit:29) |

**Key insight**: A11y-attributed failures dominate the low variant (30/40 = 75%). Model-attributed failures dominate at non-low variants (11/11 = 100%). This clean separation supports the claim that accessibility degradation introduces a mechanistically distinct failure pathway, not merely amplification of existing model weaknesses.

Llama 4 text-only failures show a different pattern (N=260, 101 failures):

| Domain | Type | Primary Variant |
|--------|------|-----------------|
| A11y | Structural Infeasibility | low (gitlab:293, gitlab:308, admin:198) |
| A11y | Content Invisibility | low (ecom:23/24/26) |
| Model | Capability Limitation | all variants (admin:4 combobox, ecom:24/26 format mismatch) |
| Model | Context Overflow | ml/base/high |

Llama 4's higher baseline failure rate (base 29.2% failure vs Claude 6.2%) means model-attributed failures are spread across all variants, making the a11y signal less clean but still significant (low 63.1% failure vs base 29.2%).

Vision-only failures (n=98) are dominated by partial_success (40/98=41%) - agents make progress but cannot complete tasks, consistent with the SoM phantom bid phenomenon preventing multi-step navigation.

**Vision-only as control condition - revised interpretation**: The SoM-based vision agent is not a "pure visual" control because SoM overlays depend on DOM interactive elements. Both agents are affected by low variant mutations, but through different mechanisms: text-only via degraded a11y tree information, vision-only via missing/phantom SoM bid labels. The meaningful comparison at non-low variants (where SoM labels are intact) shows text-only dramatically outperforms vision-only (87.8% vs 24.4%), confirming the a11y tree's substantial informational advantage. **CUA coordinate-based agent (120/120 complete, §5.2.4) provides the definitive causal decomposition: CUA drops 30.0pp (96.7%→66.7%) under low variant - entirely from functional breakage (link→span). The additional 33.3pp for text-only (63.3pp total) is attributable to the a11y tree pathway specifically. PSL experiment (§5.2.5) further confirms: pure ARIA semantic manipulation has no effect on BrowserGym agents; DOM structural changes are the active ingredient. The causal chain is: DOM structural change → simultaneously degrades a11y tree + interactive functionality → text-only fails through a11y tree pathway (33.3pp) + all agents fail through functional breakage (30.0pp). Cross-model replication (§5.2.7) demonstrates this effect generalizes beyond Claude: Llama 4 Maverick shows an even larger low-base gap (33.9pp) with a gradient rather than step function, suggesting weaker models are affected across the full accessibility spectrum.**

**Convergence with A11y-CUA** (Mohanbabu et al., CHI 2026): A11y-CUA reports CUA success dropping from 78.33% (default) to 41.67% (keyboard-only) to 28.33% (magnifier) - a comparable ~37pp degradation. Our Pilot 4 shows a 63.3pp degradation (base to low) for text-only agents; Llama 4 shows 33.9pp. While they vary the agent's input modality, we vary the environment's semantic structure - yet both demonstrate that accessibility barriers impose a substantial performance tax. Our larger effect size for Claude (63.3pp vs 37pp) is consistent with our more aggressive environmental manipulation.

### 5.6 Statistical Framework

| Analysis | Method | Purpose |
|----------|--------|---------|
| A11y ↔ agent success | CLMM (ordinal A11y) + GEE (binary success, random intercepts for LLM + website) | Primary RQ |
| Feature importance | Random Forest + SHAP on criterion-level vectors | Secondary RQ |
| Sensitivity | Three-way regression: Tier 1 only / Tier 2 only / Composite | Construct validity |
| Gap analysis | Qualitative case analysis of agent failures on high-A11y sites | Exploratory RQ |

**Construct validity defense**: Convergent validity is assessed by comparing the *direction and pattern* of effects across tracks: Track A uses categorical manipulation (Low/Base/High) while Track B uses continuous criterion-level measurement. If both show that higher accessibility associates with higher agent success - despite differing IV operationalizations - the convergence strengthens our thesis. Additionally, if Tier 2 alone predicts better than Tier 1 alone → functional semantics matter more than syntactic compliance (publishable sub-finding).

**Statistical power**: Across seven experimental rounds, the low-vs-base comparison consistently achieves significance: Pilot 2 p=0.006, Pilot 3a p<0.001, Pilot 3b p<0.001, Pilot 4 p<0.000001, Expansion p<0.001, Llama 4 p<0.001. Effect sizes range from Cramér's V=0.37 (Pilot 2) to V=0.637 (Pilot 4). Cross-model replication (Claude step function + Llama gradient) with N=760 total cases provides definitive statistical power. The Pilot 4 full design matrix (N=240) achieves Breslow-Day homogeneity p=1.000, confirming effects are consistent across tasks. 5 reps per cell sufficient for detecting large effects (>30pp); the observed 48.6pp-63.3pp low-base gaps far exceed this threshold.

**Agent framework control**: To avoid confounding A11y effects with agent-specific parsing strategies, we use WebArena's native agent architecture as the fixed framework (existing baselines available for comparison). LLM backend is modeled as a random effect in CLMM/GEE. We do not use customized agent architectures (e.g., AgentOccam's pivotal node filtering, CI4A's semantic interfaces) in the primary analysis, as their A11y Tree processing differences would introduce an additional uncontrolled variable.

---

## 6. Contributions

| Type | Contribution | Status |
|------|-------------|--------|
| **Empirical** | The first controlled evidence that A11y predicts agent success; **replicated across 7 rounds with 2 LLMs (Anthropic Claude, Meta Llama 4) and 3 agent types (N=760); Pilot 4: χ2=24.31, p<0.000001, Cramér's V=0.637; CUA: χ2=9.02, p=0.0027, V=0.388; Expansion: step function replicated across 13 tasks; Llama 4: gradient dose-response replicated; four mechanistically distinct failure pathways: token inflation, content invisibility, SoM phantom bids, cross-layer functional breakage** | Core |
| **Cross-Model Generalizability** | **Model-dependent dose-response profiles**: Claude shows step function (low catastrophic, ml+ perfect), Llama 4 shows gradient (monotonic improvement). Interaction effect: weaker models cannot compensate for L2 degradation (Llama ml=61.5% vs Claude ml=100%), but both fail under L3 structural degradation. Forced simplification (reddit:29) replicated across both model families. admin:198 reveals weaker models benefit MORE from accessibility enhancement (+40pp Llama vs +0pp Claude).** | Core |
| **Ecological Validity** | **34-site automated survey (30 external + 4 WebArena Docker) with axe-core + custom detectors. Three-severity framework: L1 decorative (70% prevalence, 0 agent impact), L2 annotation (20% prevalence, 0 agent impact), L3 structural (83.3% prevalence, fatal agent impact). Establishes that experimental manipulations reflect real-world conditions. P7 landmark→div on 82.4% of sites (avg 37 violations/site). Chinese platforms particularly affected (AliExpress 266, Bilibili 350 violations).** | Core |
| **Paradigmatic** | Environment-centric evaluation paradigm for web agents - reusable experimentation framework where any frontend property can serve as the independent variable; inverts existing agent-centric benchmarks | Core |
| **Methodological** | **Three-agent causal decomposition**: text-only (a11y tree) + SoM (DOM-dependent vision) + CUA (coordinate-based vision) quantify the independent contribution of the a11y tree pathway (33.3pp) vs functional breakage (30.0pp); Agent Failure Taxonomy; multi-tier A11y measurement; Plan D variant injection persistence (context.route + deferred patch + MutationObserver); verified: 33/33 goto traces persistent | Core |
| **Conceptual** | "Same Barrier" hypothesis - formal bridge between accessibility and AI agent research; **refined by PSL and CUA experiments: hypothesis holds at DOM structural level (L3) but diverges at ARIA semantic level (L2) due to BrowserGym serialization ≠ screen reader behavior; three-layer independence framework (DOM semantic / JS behavior / visual CSS); three-severity framework (L1/L2/L3) operationalizes the hypothesis into testable predictions; convergent with A11y-CUA (CHI 2026)** | Core |
| **Novel Finding** | **SoM phantom bids (two modes); CUA cross-layer functional breakage (link→span → 0/5 on reddit:29 despite visual invariance); forced strategy simplification (14× token efficiency, cross-model replicated); BrowserGym a11y tree serialization divergence from real screen readers; model×environment interaction (weaker models benefit more from a11y)** | Core |
| **Theoretical** | **"Overlay false affordance" - novel category in Gaver's taxonomy; duality framework: false affordances (failure) + action-space constraint (success) from single DOM change; grounded in Majumdar (2026) formal complexity results** | Core |
| **Exploratory** | Initial ACAG gap characterization; AI-Readiness Maturity Model (Level 0-3); low-functional-fix variant for further pathway isolation; SRF serialization for screen reader fidelity; **Dual-Audience Design Guidelines (evidence-backed, per Brennan Jones' recommendation); front-end developer interview study to explain why accessibility failures are so prevalent** | Future Work |

**Open artifacts**: Dataset (websites + A11y scores + agent results + failure logs), measurement pipeline (open-source), environment manipulation framework, A11y-Agent benchmark.

---

## 7. Timeline & MVP

| Phase | Period | Activities | Status |
|-------|--------|------------|--------|
| **Prep** | Mar-Apr 2026 | Literature review finalization; WebArena deployment + A11y variant creation; Tier 1+2 pipeline; pilot studies | 🟢 **Pilots 2-3b complete** - 4 rounds, 81-240 cases each, statistically significant across all (p<0.008). Platform bugs identified and fixed. Vision-only control condition validates causal pathway. |
| **Data Collection** | Apr 2026 | Track A full execution with Plan D variant injection | 🟢 **Pilot 4 complete** - 240/240 cases (text-only + SoM), p<0.000001. **CUA 120/120 complete** - 109/120 success (90.8%), low 66.7% vs base 96.7% (p=0.0027). Plan D verified. Total N=360. |
| **Task Expansion** | Apr 2026 | Expand task set from 6→13 tasks; Claude replication | 🟢 **Complete** - 7 new tasks (gitlab:132/293/308, admin:41/94/198, ecom:188). 140 cases. Step function replicated: low 51.4%, ml/base/high 100%. |
| **Cross-Model** | Apr 2026 | Multi-model replication with open-source LLM | 🟢 **Complete** - Llama 4 Maverick, 260 cases. Gradient dose-response: low 36.9% → high 75.4%. Cross-model forced simplification confirmed. |
| **Ecological Validity** | Apr 2026 | Automated accessibility survey of real-world websites | 🟢 **Pilot complete** - 34 sites scanned, L1/L2/L3 framework established. L3 prevalence 83.3%. WebArena base = L3-clean. |
| **Track B** | May-Jul 2026 | HAR recording + landscape survey (200+ sites); real-world ecological validation (parallel with SURF #2) | 🟡 **Pilot done, full survey not started** |
| **Additional experiments** | May-Jun 2026 | Expand to 20 tasks; low-functional-fix variant; SRF serialization; HTML snapshot collection | 🟡 **low-functional-fix**: planned (restore href in link→span, re-run CUA+text 60 cases). **SRF**: planned. **20 tasks**: 7 more needed. **HTML snapshots**: 8 sites × 3 pages pending. |
| **Analysis** | Jul-Aug 2026 | CLMM/GEE, SHAP, failure taxonomy coding, cross-pilot meta-analysis | 🟡 **Partially complete** - Pilot 4 + Expansion + Llama 4 analysis done, formal statistical modeling pending |
| **Writing** | Aug-Sep 2026 | Paper drafting | 🟢 **In progress** - LaTeX skeleton created, abstract written, Results data ready |
| **Submission** | Sep-Oct 2026 | CHI 2027 (full or LBW) | Pending |

**MVP (minimum publishable)**: Track A results (13 tasks × 4 variants × 2 LLMs × 3 agent types, N=760) + ecological validity pilot (34 sites) + failure taxonomy + deep dive analysis = **sufficient for CHI full paper**. Track B full survey would strengthen ecological validity further but is not required for core contribution.

**Venues**: CHI 2027 (Sep) → ASSETS 2027 (Jun) → CSCW 2027 → WWW 2027.

### 7.1 Dual-Audience Design Guidelines (New, per Brennan Jones)

Our three-agent causal decomposition naturally maps to actionable design guidelines that serve both accessibility users and AI agents simultaneously. Each guideline specifies:

- **(a)** The design rule
- **(b)** Human assistive technology impact
- **(c)** Quantified AI agent impact from our data
- **(d)** Which observation pathway is affected (a11y tree vs visual vs both)

For example: "Use semantic HTML elements over generic containers" - screen readers can navigate by element type (H/K/T keys); AI agents suffer a 63.3pp success rate drop when semantic tags are replaced with `<div>`/`<span>` (§5.2.2). Unlike WCAG's one-size-fits-all criteria, these guidelines are differentiated by audience and grounded in experimental data.

**Planned output**: 5-8 evidence-backed guidelines in the paper's Discussion section. Standalone expansion targeting W4A or ASSETS as a follow-up paper. These guidelines serve as empirical seeds for the longer-term ACAG standard proposal.

### 7.2 Front-End Developer Interview Study (New)

Our quantitative data shows *that* accessibility failures degrade AI agents, but not *why* accessibility failures are so prevalent. A semi-structured interview study with 10-15 front-end engineers would complete the causal chain:

- **Core questions**: Do you inspect final DOM output? Does your CI/CD include accessibility checks? Do you know what ARIA is? If you learned AI agents depend on your semantic markup, would it change your process?
- **Recruitment**: Leverage Alex's Amazon and SAP professional networks for participants from enterprise engineering teams.
- **Alignment with SURF #2**: Brennan's Personal Reflection project teaches user study methodology; this interview study is a natural application.
- **Planned output**: Qualitative findings integrated into the Design Guidelines paper. Provides the "why" behind the "what": our experiment shows the impact of poor accessibility; interviews explain why poor accessibility is the default.

Brennan suggested workshop-based investigation at partner companies during our March 30 meeting; this formalizes that direction.

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
| Variant injection fidelity | **RESOLVED.** Pilot 2 identified composite score compression (0.405-0.457). Pilot 3 enhanced operators. Pilot 3b revealed goto() escape vulnerability. **Plan D (context.route + deferred patch + MutationObserver) verified in Pilot 4: 33/33 goto traces show persistent degradation. ecom:23 low dropped from 80% (3b, escape) to 0% (Pilot 4, Plan D).** Three bridge bugs identified and fixed (ISSUE-BR-1: timer leak, ISSUE-BR-4: MutationObserver sentinel, ISSUE-BR-7: stderr capture). None had significant impact on Pilot 4 data (controlled token comparison: high vs base Δ < 1.3% on matched tasks). |
| Vision control confound | **RESOLVED.** CUA agent (coordinate-based, zero DOM dependency) completed 120/120 cases. Results: low 66.7% vs base 96.7% (p=0.0027, V=0.388). Three-agent causal decomposition: CUA 30pp drop (functional breakage) + additional 33.3pp for text-only (a11y tree pathway). reddit:29 low CUA=0/5 vs text-only=4/5 confirms functional breakage (link→span) is the dominant CUA failure mode. **low-functional-fix variant** planned to further isolate pathways. |
| BrowserGym serialization fidelity | **IDENTIFIED.** PSL experiment revealed that BrowserGym's a11y tree serialization diverges from real screen reader behavior: `aria-hidden="true"` elements retain bids, roles, and clickability (shown as `hidden=True` attribute) instead of being filtered out. `role="presentation"` on focusable elements may also be ignored. This means pure ARIA semantic manipulation has no effect on BrowserGym-based agents - only DOM structural changes affect agent behavior. **Mitigation**: Screen-Reader-Faithful (SRF) serialization mode planned - filter `hidden=True` elements before agent observation. If PSL + SRF degrades text-only agent → confirms Same Barrier holds at ARIA level when serialization is faithful. **Broader implication**: All BrowserGym-based benchmarks (WebArena, VisualWebArena, WorkArena) may overestimate agent robustness to ARIA semantic degradation. |
| Low variant ecological validity | **MITIGATED.** Ecological validity pilot (34 real-world sites) establishes that L3 structural violations appear on 83.3% of surveyed sites. P7 (landmark→div) on 82.4%, P5 (heading→div) on 61.8%. P11 (link→span) static prevalence is 11.8% but severely underestimated due to JS event delegation invisibility (real prevalence est. 40-60%). HTTP Archive data confirms `<div>` + `<span>` = ~40% of all HTML elements. Our low variant is a composite of violations routinely found on high-traffic websites. Three-severity framework (L1/L2/L3) explains why WebArena base (L1/L2 imperfect, L3 clean) supports ~100% success. |
| Human-agent divergence | "Same Barrier" describes structural equivalence, not identity. Over-engineering for agents (e.g., excessive hidden ARIA) may increase cognitive load for screen reader users. **Pilot 2 high variant data is consistent with this concern - enhanced ARIA did not improve agent performance and may introduce DOM bloat.** Acknowledged in Limitations; motivates ACAG as a balancing standard, not a pure superset of WCAG |
| Task feasibility confounds | **Low variant may make tasks logically impossible (content invisibility) rather than merely harder. Task feasibility annotation and dual reporting (all tasks vs feasible-only) separate these effects.** |
| Absolute claims challenged | Hedged language: "to our knowledge," "we argue that," "among the first" |

---

## 9. Methodological Evidence Bank (Deep Research, April 8, 2026)

*Supporting evidence for anticipated reviewer pushback. To be integrated into paper sections during final writing.*

### 9.1 Three-Agent Subtraction Design: Methodological Justification

The three-agent decomposition (63pp - 30pp = 33pp) is structurally identical to the epidemiological **attributable fraction** (AF). No CS/HCI paper has explicitly used AF terminology, but the subtraction logic has a 150+ year pedigree:

**Citation chain for paper:**
1. **Levin (1953)** - Original AF formula (lung cancer attributable to smoking). Columbia Mailman School reference: https://www.publichealth.columbia.edu/research/population-health-methods/adjusted-attributable-fractions
2. **Donders (1868)** via **Sartori & Umiltà (2000)** - Subtraction method: condition A - condition B = isolated cognitive process. The foundational logic of our design. https://www.researchgate.net/publication/12369885
3. **Rothman & Greenland (2008)** - *Modern Epidemiology*: excess fractions vs etiologic fractions; excess fractions as lower bounds. Textbook authority.
4. **O'Connell & Ferguson (2022)** - **Pathway-specific PAFs** using causal inference potential-outcomes framework. **Directly parallels our multi-pathway decomposition.** https://pmc.ncbi.nlm.nih.gov/articles/PMC9749703/
5. **Dai & Gifford (2024)** - Ablation Based Counterfactuals (ABC): "causal influence of data surgically removed by ablating model components." Formalizes ablation-as-counterfactual. https://arxiv.org/html/2406.07908v1
6. **Qi, Schölkopf & Jin (2024)** - SCM-based responsibility attribution in human-AI systems through counterfactual reasoning. https://arxiv.org/html/2411.03275v1
7. **RAND (2026)** - Human uplift RCTs: AI-assisted vs unassisted performance to quantify marginal AI contribution. Closest structural parallel in AI evaluation. https://www.rand.org/pubs/working_papers/WRA4869-1.html

**Suggested paper text (§4.5 or §5.9.2):**
> "Our decomposition follows the logic of the epidemiological attributable fraction (Levin 1953; Rothman & Greenland 2008), itself an instance of Donders' (1868) subtraction method for isolating causal components through controlled condition differences. By holding the environment constant while varying only the agent's observation pathway, the difference between text-only (63.3pp drop) and CUA (30.0pp drop) isolates the Accessibility Tree contribution (33.3pp)-analogous to O'Connell & Ferguson's (2022) pathway-specific population attributable fractions."

### 9.2 BrowserGym A11y Tree Fidelity: Confirmed Novel Contribution

**Literature gap confirmed:** No systematic comparison exists between BrowserGym/Playwright a11y trees and real screen reader output (JAWS/NVDA/VoiceOver).

**Key evidence:**
- **Playwright officially deprecated** `page.accessibility` API, citing "wildly different output" across platforms. https://playwright.help/python/docs/next/release-notes
- **CDP Accessibility domain** remains marked **Experimental**. https://chromedevtools.github.io/devtools-protocol/tot/Accessibility
- **Chrome maintains TWO separate a11y trees**: Blink's internal AX tree (CDP-exposed) vs BrowserAccessibility tree (OS-API-exposed, what screen readers actually query). Each platform wrapper (Cocoa/Win/Atk) translates differently. https://russmaxdesign.github.io/maxdesign/articles/two-trees.html
- **NVDA/JAWS create virtual document representations** - separate copies with single-letter navigation (H for headings, K for links) that CDP cannot capture. JAWS applies proprietary heuristics to compensate for poor markup.
- **Automated tools detect only ~20-30% of WCAG success criteria** (b13.com, essentialaccessibility.com).
- **BrowserGym ecosystem paper** (OpenReview) defines POMDP observation space with AXTree but **does not validate fidelity** against real AT. https://openreview.net/forum?id=5298fKGmv3

**Implication:** Our PSL experiment's null result + the BrowserGym serialization divergence is a **benchmark-level finding** affecting all BrowserGym-based evaluations (WebArena, VisualWebArena, WorkArena).

### 9.3 Ecological Validity: Large-Scale Audit Data

**The "div soup" is real:**
- `<div>` = **28.7%** of all HTML elements; `<div>` + `<span>` = **~40%** (HTTP Archive 2024). https://almanac.httparchive.org/en/2024/markup
- Semantic structural elements (`<nav>`, `<main>`, `<header>`, etc.) **do not appear in top 15** by frequency.
- Page complexity up 61% in 6 years (782 → 1,257 elements avg), inflated by div/span.

**Interactive element misuse:**
- `role="button"` on **53-54%** of pages, "often on non-semantic elements such as `<div>` or `<span>`." (HTTP Archive 2025). https://almanac.httparchive.org/en/2025/accessibility
- **Empty links** on **45.4%** of top 1M sites (WebAIM Million 2025). https://webaim.org/projects/million/2025
- **Empty buttons** on **29.6%** of top 1M sites.
- ~9-11% of buttons have no accessible name at all.

**ARIA paradox:**
- Pages with ARIA average **57 errors** vs **27 on non-ARIA pages** - ARIA used as band-aid, not fix.
- ARIA usage quintupled since 2019 (22 → 106 attributes/page), errors increased proportionally.

**Landmark gaps:**
- Only **42.6%** have `<main>` element/landmark. 57%+ of top sites lack this fundamental marker.

**Suggested paper text (§6.5 or §4.2):**
> "Our link→span manipulation is not a contrived laboratory artifact but reflects the dominant reality of the production web, where `<div>` and `<span>` together comprise approximately 40% of all HTML elements (HTTP Archive 2024), `role='button'` appears on 53-54% of pages often on non-semantic elements (HTTP Archive 2025), and empty links affect 45.4% of the top million websites (WebAIM Million 2025)."

### 9.4 Coordinate-Based Agent Landscape (Update Before Submission)

**OSWorld progression:**
| Model | Date | OSWorld | Key Innovation |
|-------|------|---------|----------------|
| UI-TARS | Jan 2025 | 24.6% | Native GUI agent |
| OpenAI CUA | Jan 2025 | 38.1% | GPT-4o vision + RL |
| UI-TARS-2 | Sep 2025 | 47.5% | Multi-turn RL |
| Step-GUI (8B) | Dec 2025 | 48.5% | Self-evolving step rewards |
| GUI-Owl-1.5 | Feb 2026 | **56.5%** | MRPO multi-platform RL |

**New benchmarks:** ScreenSuite (13 benchmarks unified), OSWorld-Human (human trajectories), VAGEN (proactive environment probing), WARC-Bench (archived dynamic webpages).

GUI-Owl-1.5 represents a significant milestone: at 56.5% on OSWorld, coordinate-based agents are now within range of matching text-only agent performance on well-structured websites (our Claude base = 93.8%). However, our ecological validity data suggests these agents will face the same L3 structural barriers as text-only agents when deployed on the 83.3% of real-world websites with structural violations.

**Update §2.5 before submission.**

---

## 10. Key References

### Agent Benchmarks and Evaluation
1. Zhou et al. - WebArena (CMU, 2024) [arxiv 2307.13854]
2. Deng et al. - Mind2Web (NeurIPS 2023)
3. Gao et al. - AgentOccam: +161% via A11y Tree (Amazon Science, ICLR 2025) [arxiv 2410.13825]
4. Chen et al. - CI4A: 86.3% WebArena SOTA (ByteDance) [arxiv 2601.14790]
5. Abuelsaad et al. - "An Illusion of Progress?" [arxiv 2504.01382]
6. Zhou, Hernández-Orallo et al. - ADeLe: 18 cognitive dimensions (Nature 2026) [arxiv 2503.06378]
7. He et al. - WebVoyager (ACL 2024)
8. Zheng et al. - SeeAct (OSU)

### Accessibility Standards and Measurement
9. WebAIM - Million 2025 Report (94.8% failure rate, ARIA paradox)
10. Deque - Automated testing detects 57% of A11y issues (volume-based)
11. CodeA11y - LLM-augmented A11y auditing (87.18% detection)
12. UC Berkeley & UMich - nohacks.co / CHI 2026: Agent keyboard-only experiment (78.33% → 41.67%)
13. W3C - WCAG 2.2 / WAI-ARIA 1.2
14. W3C Web ML CG - WebMCP specification (Chrome 146, Feb 2026)
15. CopilotKit - AG-UI Protocol
16. Nolan Lawson - Shadow DOM and ARIA (2022)

### Industry and Policy
17. Virtana - 75% enterprise double-digit AI failure rates (2026)
18. Patronus AI - 63% workflow failure at 1% per-step error
19. EU Directive 2019/882 - European Accessibility Act

### Environment Perturbation and Robustness
20. "Better Assumptions, Stronger Conclusions: Ordinal Regression in HCI" [arxiv 2602.18660]
21. RAND - "Quantifying AI's Economic Potential"
22. VisualWebArena [arxiv 2401.13649]
23. WorkArena [arxiv 2403.07718]
24. ARE - Adversarial web page perturbations [arxiv 2406.12814]
25. WAREX - Web agent reliability evaluation via fault injection [arxiv 2510.03285]
26. GUI-Robust - GUI anomaly robustness dataset (Yang et al., 2025) [arxiv 2506.14477]
27. D-GARA - Dynamic GUI agent robustness benchmarking (Chen et al., 2025) [arxiv 2511.16590]
28. Aegis - Agent-environment failure taxonomy + optimization (Song et al., 2025) [arxiv 2508.19504]
29. ARE - Adversarial perturbations hijack agents (2024) [arxiv 2406.12814]
30. **Ma11y** - Mutation framework for web accessibility testing (Tafreshipour et al., ISSTA 2024) [github.com/mahantaf/web-a11y-tool-analyzer]

### Observation Space and Token Efficiency
31. Power et al. - 50.4% of blind user problems in WCAG (CHI 2012) [doi 10.1145/2207676.2207736]
32. FocusAgent - Lightweight a11y tree retriever [arxiv 2510.03204]
33. Prune4Web - 25-50× element reduction [arxiv 2511.21398]
34. AgentOCR - Visual compression for web agents [arxiv 2601.04786]
35. Chung et al. - Long-context web agent benchmark (<10% success at 25K-150K tokens) [arxiv 2512.04307]

### Theoretical Frameworks
36. Gibson, J.J. - The Ecological Approach to Visual Perception (1979) - Affordance Theory
37. Han et al. - Computational rationality-based affordance for AI agents (2025) [arxiv 2501.09233]
38. Huang et al. - EnviSAgE: Environment-centric perspective for agents (2025) [arxiv 2511.09586]
39. Accessible.org - Only 13% of WCAG 2.2 AA fully auto-detectable (2025)
40. WCAG 3.0 - Graduated scoring model (Bronze/Silver/Gold), critical errors

### Cross-Browser and ARIA Research
41. Igalia - Accessible name computation divergence across browsers (2023)
42. Rego (Igalia) - Solving cross-root ARIA issues in Shadow DOM
43. W3C - AccName specification, IDREF resolution rules
44. Speech enhancement degrades ASR paradox [arxiv 2512.17562]
45. Gandor & Nalepa - JPEG compression threshold effects on object detection (Sensors 2022)
46. Shermeyer & Van Etten - Satellite imagery resolution thresholds (2018) [arxiv 1812.04098]

### Accessibility Metrics and User Studies
47. RA-WAEM - User-experience accessibility metric (W4A 2018)
48. Applause - "Accessibility is the infrastructure for AI readiness" (2025)
49. DubBot - "When AI reads like a screen reader" (2026)
50. Opus Research - "Why AI needs accessibility" (2025)
51. CHI 2026 Workshop - "Dual-audience" problem: interfaces for humans and agents [arxiv 2603.10664]
52. Screen2AX - Generating a11y trees from screenshots (MacPaw, 2025) [arxiv 2507.16704]
53. Browser Use - "Make websites accessible for AI agents" (84.7K GitHub stars)
54. Google - Natively Adaptive Interfaces (NAI) for multimodal AI agents
55. Vigo & Harper - "Accessibility-in-Use" evaluation (W4A 2013)
56. Build the Web for Agents - Position paper [arxiv 2506.10953]

### SoM Robustness, False Affordances, and Action Space Theory
57. Yang et al. - Set-of-Mark Prompting (2023) [github.com/microsoft/SoM]
58. SHARPMARK - SoM modality gap analysis (ACL ARR 2024) [openreview.net/forum?id=YQf0IcGkdn]
59. Shi et al. - "Towards Trustworthy GUI Agents" survey (2025): Execution Gap formalization [arxiv 2503.23434]
60. Gaver, W.W. - "Technology Affordances" (CHI 1991): False affordance taxonomy
61. Norman, D. - "The Design of Everyday Things" (2013): Signifiers vs affordances
62. Liu et al. - "Visual Confused Deputy" for CUAs (2026) [arxiv 2603.14707]
63. Wang et al. - A4Bench: MLLM affordance evaluation (2025) [arxiv 2506.00893]
64. Nitu & Stöckl - Agent satisficing behavior with SoM overlays (2025) [arxiv 2507.12844]
65. OpenAI - Computer-Using Agent (CUA): 58.1% WebArena [openai.com/index/computer-using-agent]
66. UI-TARS - Pure-vision GUI agent (2025) [arxiv 2501.12326]
67. MolmoWeb - Open pure-vision web agent (AI2, 2026) [the-decoder.com]
68. GUI-Actor - Coordinate-free attention grounding (2025) [arxiv 2506.03143]
69. Schwartz, B. - "The Paradox of Choice" (2004)
70. Hick, W.E. - "On the Rate of Gain of Information" (1952): Hick-Hyman Law
71. Progressive Disclosure - HCI design principle (Miller, 1956)
72. W3C COGA - Cognitive Accessibility Guidance (2020) [w3.org/TR/2020/WD-coga-usable-20201211]
73. Huang et al. - Contextual distraction ~45% degradation (2025) [arxiv 2502.01609]
74. Majumdar - Dense Ω(M) vs sparse √k action complexity (2026) [arxiv 2601.08271]
75. Nica et al. - Paradox of choice in RL (2022) [arxiv 2201.09653]
76. Plan-MCTS - Semantic plan space exploration (2026) [arxiv 2602.14083]
77. DMAST - DOM injection as two-player Markov game (UC Berkeley/DeepMind, 2026) [arxiv 2603.04364]
78. Google DeepMind - AI Agent Traps framework (2026) [securityweek.com]
79. Röder et al. - Detecting Pipeline Failures in web agents (DFKI, 2024) [arxiv 2509.14382]
