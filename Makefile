# Research project Makefile
# Usage: make verify-numbers

PYTHON ?= python3

.PHONY: verify-numbers export-data run-stats setup all

# First-time setup: create venv and install dependencies
setup:
	$(PYTHON) -m venv analysis/.venv
	analysis/.venv/bin/pip install -r analysis/requirements.txt
	@echo "Setup complete. Activate with: source analysis/.venv/bin/activate"

# Verify all data points against key-numbers.md
verify-numbers:
	$(PYTHON) -X utf8 analysis/verify_all_data_points.py

# Re-export combined CSV from raw traces
export-data:
	$(PYTHON) -X utf8 analysis/export_combined_data.py

# Run full statistical analysis
run-stats:
	$(PYTHON) -X utf8 analysis/run_statistics.py

# Full pipeline: export → verify → stats
all: export-data verify-numbers run-stats
