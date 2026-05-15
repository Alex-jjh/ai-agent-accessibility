# Research project Makefile
#
# Common entry points:
#   make verify-all         — run every stage verifier in sequence (V&V)
#   make audit-<phase>      — run one stage verifier
#   make export-data        — re-build results/combined-experiment.csv
#   make run-stats          — full descriptive statistics (composite phase)
#   make all                — export → verify-all → run-stats
#   make setup              — first-time venv + deps
#
# Per-stage doc: docs/by-stage/<phase>.md

PYTHON ?= python3.11

.PHONY: setup all
.PHONY: verify-all verify-numbers
.PHONY: audit-composite audit-mode-a audit-c2 audit-dom audit-smoker audit-stage3 audit-stage4b audit-paper audit-archival
.PHONY: export-data run-stats

# ── First-time setup ─────────────────────────────────────────────
setup:
	$(PYTHON) -m venv analysis/.venv
	analysis/.venv/bin/pip install -r analysis/requirements.txt
	@echo "Setup complete. Activate with: source analysis/.venv/bin/activate"

# ── Per-stage verifiers (each independently runnable) ─────────────
audit-composite:
	$(PYTHON) -m analysis.stages.phase1_composite

audit-mode-a:
	$(PYTHON) -m analysis.stages.phase2_mode_a

audit-c2:
	$(PYTHON) -m analysis.stages.phase3_c2

audit-dom:
	$(PYTHON) -m analysis.stages.phase4_dom_signatures

audit-smoker:
	$(PYTHON) -m analysis.stages.phase5_smoker

audit-stage3:
	$(PYTHON) -m analysis.stages.phase6_stage3

audit-stage4b:
	$(PYTHON) -m analysis.stages.phase6_stage4b

# ── Cross-cutting audits ──────────────────────────────────────────
audit-paper:
	$(PYTHON) analysis/paper_consistency_audit.py

audit-archival:
	bash scripts/maintenance/check-archival-state.sh

# ── Aggregate verifier (one-button V&V) ───────────────────────────
verify-all:
	$(PYTHON) -m analysis.verify_all

# Legacy alias — composite phase only (kept for backwards compat)
verify-numbers:
	$(PYTHON) -X utf8 analysis/verify_all_data_points.py

# ── Data export and statistics ────────────────────────────────────
export-data:
	$(PYTHON) -X utf8 analysis/export_combined_data.py

run-stats:
	$(PYTHON) -X utf8 analysis/run_statistics.py

# ── Convenience: full pipeline ────────────────────────────────────
all: export-data verify-all run-stats

# ── Pre-submission gate ───────────────────────────────────────────
# Run before paper PDF rebuild for camera-ready or rebuttal.
# Outputs paper-supplementary/ for reviewers.
.PHONY: pre-submit
pre-submit: verify-all audit-paper audit-archival
	@echo
	@echo "── building paper-supplementary/ ──"
	@bash scripts/maintenance/build-supplementary.sh
	@echo
	@echo "✅ Pre-submission gate passed."
	@echo "   Paper PDF rebuild + figure inventory are manual user steps."
	@echo "   See docs/by-stage/pre-submission-checklist.md."
