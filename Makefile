# Research project Makefile
# Usage: make verify-numbers

.PHONY: verify-numbers export-data run-stats all

# Verify all data points against key-numbers.md
verify-numbers:
	python -X utf8 analysis/verify_all_data_points.py

# Re-export combined CSV from raw traces
export-data:
	python -X utf8 analysis/export_combined_data.py

# Run full statistical analysis
run-stats:
	python -X utf8 analysis/run_statistics.py

# Full pipeline: export → verify → stats
all: export-data verify-numbers run-stats
