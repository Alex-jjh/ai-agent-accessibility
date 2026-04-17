# Paper Writing Decisions Log

Consolidated from review discussions (April 14, 2026).

## Contributions (Final 4)

1. **First controlled causal evidence** that web accessibility predicts AI agent task success
   (N=1,040, Cochran-Armitage Z=6.635, p<0.000001)
2. **Three-agent causal decomposition** quantifying semantic vs functional pathways
   (text-only 55.4pp - CUA 35.4pp = 20.0pp pure semantic contribution)
3. **Cross-model generalizability** across closed (Claude) and open (Llama 4) models
   (both p<0.001, effect direction consistent)
4. **L1/L2/L3 severity framework + ecological validity** from 34-site audit
   (83.3% of real sites have L3 structural violations matching our low variant)

Demoted to Results subsections (not top-level contributions):
- Failure taxonomy (phantom bids, forced simplification) → Results §4.3
- Environment-centric paradigm → Method narrative, not standalone contribution
- Duality framework, BrowserGym divergence, ACAG → follow-up papers

## Paper Narrative Structure

- **Lead**: Same Barrier hypothesis + environment-centric paradigm (conceptual framing)
- **Core Results**: 13-task × 4-variant × 2-model results + three-agent causal decomposition
  (causal decomposition is a RESULT, not a method — present in Results with CUA vs text-only figure)
- **Method**: Experiment design + task selection protocol + statistical plan
- **Validation**: Ecological validity + L1/L2/L3 framework
- **Discussion**: Developer guidelines + forced simplification + asymmetric effect + limitations

## Key Framing Decisions

### Causal Decomposition Numbers (full 13-task data)
- Text-only low→base: +55.4pp (semantic + functional)
- CUA low→base: +35.4pp (functional only)
- Difference: ~20.0pp = pure A11y Tree semantic pathway
- NOTE: These numbers differ from expansion-only estimates (48.6pp/40.0pp)
  because full 13-task data includes Pilot 4 tasks with different base rates
- Cochran-Armitage Z=6.635, p<0.000001 (text-only Claude, 13 tasks)

### Base ≈ High (Asymmetric Effect)
- Claude 13-task: base 93.8% vs high 89.2% (4.6pp, admin:4 reasoning error)
- Llama 4: base 70.8% vs high 75.4% (high > base, normal direction)
- Framing: "Asymmetric dose-response — degradation hurts significantly, enhancement
  provides marginal gain. This is consistent with a floor effect: once accessibility
  is sufficient, additional enhancement has diminishing returns."
- Footnote in Results table: "Pilot 4 (6 tasks) showed base > high due to context
  overflow on reddit:67; 13-task aggregate shows base ≈ high."

### SoM Downweighted
- SoM 27.1% baseline too low for meaningful gradient analysis
- Main narrative: text-only vs CUA (causal decomposition)
- SoM: supplementary evidence in failure mode analysis subsection
- Phantom bid finding still reported but not as primary evidence

### Multiple Comparisons Strategy
- Primary endpoint: Cochran-Armitage on text-only Claude — NO correction (pre-specified)
- Secondary: Bonferroni-corrected where applicable
- Stated in Method: "Primary and secondary endpoints defined prior to statistical analysis"

### Low Variant Conflation
- Acknowledged in Limitations: "Low variant applies 13 patches simultaneously;
  CUA comparison isolates semantic contribution; patch-level ablation reserved
  for future work"
- NOT running low-functional-fix variant before submission — save for revision

### Statistical Reporting
- Unit of analysis: aggregate level (across tasks × reps) for all statistical claims
- Individual task×variant patterns: qualitative illustration only, not statistical evidence
- 5 reps × binary = only 6 possible values per cell — explicitly stated in Method

## Action Items (Ordered)

1. ✅ combined-experiment.csv (N=1,040, 26 columns) — DONE
2. ✅ run_statistics.py (6-level analysis) — DONE
3. 🔲 Task Selection Protocol subsection + flowchart — THIS WEEK
4. 🔲 LaTeX skeleton with section structure — THIS WEEKEND
5. 🔲 Results section from stats CSV — NEXT WEEK
6. ⏭️ low-functional-fix variant — REVISION STAGE
7. ⏭️ Track B 100+ sites — SKIP (34 sufficient for CHI)


## Review Round 3 Insights (2026-04-14, from colleague)

### Composition Effect as Publishable Finding
The semantic pathway magnitude depends on task composition:
- Tasks with primarily semantic degradation (Pilot 4): 33.3pp
- Tasks with functional breakage (Expansion): 8.6pp
- Weighted average (all 13): 20.0pp

Paper should frame this as a nuanced finding, not a weakness:
"The magnitude of the semantic pathway depends on the task's primary
failure mode. Tasks where low variant degrades mainly through semantic
loss show larger semantic pathways (~33pp), while tasks with structural
functional breakage show smaller semantic pathways (~9pp). The 20pp
estimate represents a weighted average across realistic task composition."

### Asymmetric Effect as Secondary Finding
"Accessibility affects agents asymmetrically: degradation from base causes
substantial performance loss (-55pp at low), while enhancement above base
produces marginal gain (<5pp). This suggests well-designed baselines
approach a ceiling for agent utility."

### SoM "Hidden DOM Dependencies" Discussion Paragraph
"A common assumption is that vision-only agents bypass DOM dependencies.
Our SoM results refute this. Set-of-Mark labeling pipelines rely on DOM
structure to identify interactive elements. When DOM semantics degrade,
SoM produces phantom labels on non-interactive elements, leading to
4.6% success at low variant despite unchanged visual rendering."

### Verification Infrastructure
- verify_all_data_points.py: run before any paper number update
- key-numbers.md: single source of truth, all paper numbers reference this
- Makefile `verify-numbers` target: CI-style verification
- Correction log in key-numbers.md tracks all number changes with root cause
