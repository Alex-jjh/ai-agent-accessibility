# Failure Taxonomy Comparison: Ours vs Aegis

Reference: Aegis — https://arxiv.org/abs/2508.19504

## Aegis 6 Failure Modes → Our 11-Type Taxonomy

| Aegis Failure Mode | Description | Our Equivalent | Our Code | Notes |
|---|---|---|---|---|
| **Perception Failure** | Agent fails to correctly perceive/interpret UI elements | Element Not Found (F_ENF) + Wrong Element Actuation (F_WEA) | F_ENF, F_WEA | We split perception into two subtypes: element missing from a11y tree vs element found but wrong one actuated |
| **Reasoning Failure** | Agent makes incorrect logical decisions about actions | Reasoning Error (F_REA) | F_REA | Direct match |
| **Grounding Failure** | Agent cannot map high-level intent to specific UI actions | Hallucination (F_HAL) | F_HAL | Our "hallucination" covers cases where agent references non-existent elements or fabricates action targets |
| **Memory Failure** | Agent loses track of context/state across steps | Context Overflow (F_COF) | F_COF | We frame this as token context overflow rather than abstract "memory" — more mechanistically precise |
| **Execution Failure** | Action technically fails (click doesn't register, etc.) | Network Timeout (F_NET) + Anti-bot Block (F_ABB) | F_NET, F_ABB | We split execution failures by root cause: network vs anti-bot |
| **Environment Failure** | Environment itself is broken/unreachable | Network Timeout (F_NET) | F_NET | Overlaps with our environmental domain |

## Our Types NOT in Aegis (Novel Contributions)

| Our Type | Code | Domain | Why Novel |
|---|---|---|---|
| **Keyboard Trap** | F_KBT | accessibility | Agent gets stuck in keyboard navigation loop. Specific to a11y-degraded environments. No equivalent in Aegis because they don't study accessibility variants. |
| **Pseudo-Compliance Trap** | F_PCT | accessibility | ARIA attributes present but semantically wrong (e.g., aria-label="asdf"). Agent trusts the a11y tree but gets misleading information. Unique to our mutation-based approach. |
| **Shadow DOM Invisible** | F_SDI | accessibility | Interactive elements hidden inside closed Shadow DOM boundaries. Agent's a11y tree simply doesn't contain these elements. Novel web platform failure mode. |
| **Task Ambiguity** | F_AMB | task | Task specification is inherently ambiguous — agent's interpretation differs from evaluator's. Aegis doesn't separate task-level issues from agent-level issues. |
| **Unclassified** | F_UNK | unclassified | Catch-all for cases where no detector matches with sufficient confidence. Flagged for manual review. |

## Summary

- Aegis: 6 failure modes (agent-centric, environment-agnostic)
- Ours: 12 failure types across 5 domains (accessibility-aware, environment-centric)
- Overlap: 5 of Aegis's 6 modes map to our types (some split into finer categories)
- Novel: 5 types unique to our taxonomy, 3 of which are accessibility-specific
- Key difference: Aegis treats the environment as fixed; we systematically vary it via mutation operators and classify failures that arise specifically from accessibility degradation.

## For Paper Discussion Section

> Our failure taxonomy extends Aegis's [ref] 6 agent-environment interaction
> failure modes with 5 additional types specific to accessibility-degraded
> environments. While Aegis treats perception, reasoning, grounding, memory,
> execution, and environment failures as properties of the agent-environment
> dyad, our taxonomy introduces an accessibility domain with 5 failure types
> (F_ENF, F_WEA, F_KBT, F_PCT, F_SDI) that arise specifically when the
> web environment's accessibility properties are degraded via mutation
> operators. The pseudo-compliance trap (F_PCT) and Shadow DOM invisibility
> (F_SDI) are particularly novel — they represent failure modes that only
> manifest when agents rely on the accessibility tree as their primary
> observation channel, and the tree itself has been corrupted.
