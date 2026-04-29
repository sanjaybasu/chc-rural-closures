.PHONY: all clean check test
PY := python

all: results/cs2_simple_all.csv results/multiple_testing_adjusted.csv \
     figures/fig2_forest_all_outcomes.pdf figures/fig3_event_panels.pdf

data/processed/info.parquet: scripts/01_load_uds.py
	$(PY) scripts/01_load_uds.py

data/processed/panel.parquet: scripts/02_match_closures.py data/processed/info.parquet
	$(PY) scripts/02_match_closures.py

results/cs_event_log_n_total.csv: scripts/03_event_study.py data/processed/panel.parquet
	$(PY) scripts/03_event_study.py

figures/fig1_event_study.pdf: scripts/04_figures.py results/cs_event_log_n_total.csv
	$(PY) scripts/04_figures.py

results/table1_baseline.csv: scripts/05_table1.py data/processed/panel.parquet
	$(PY) scripts/05_table1.py

data/processed/clinical_extra.parquet: scripts/06_more_outcomes.py
	$(PY) scripts/06_more_outcomes.py

results/cs2_simple_all.csv: scripts/07_event_study_full.py data/processed/panel.parquet data/processed/clinical_extra.parquet
	$(PY) scripts/07_event_study_full.py

figures/fig2_forest_all_outcomes.pdf figures/fig3_event_panels.pdf: scripts/08_figures_full.py results/cs2_simple_all.csv
	$(PY) scripts/08_figures_full.py

results/multiple_testing_adjusted.csv: scripts/09_multiple_testing.py results/cs2_simple_all.csv
	$(PY) scripts/09_multiple_testing.py

test:
	$(PY) -m pytest tests/ -v

check:
	$(PY) tests/test_consistency.py

clean:
	rm -f data/processed/*.parquet results/*.csv figures/*.png figures/*.pdf
