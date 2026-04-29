"""Smoke tests + numerical consistency checks for the analysis pipeline.

Run from repo root:  python -m pytest tests/ -v
Or:                  python tests/test_consistency.py
"""
from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parent.parent

def test_panel_shape():
    p = pd.read_parquet(ROOT/"data/processed/panel.parquet")
    assert p["bhcmisid"].nunique() == 1642, "Expected 1,642 unique CHCs"
    assert (p["year"].between(2014, 2024)).all(), "Years outside 2014-2024 present"

def test_exposure_counts():
    p = pd.read_parquet(ROOT/"data/processed/panel.parquet")
    n_exp = p[p.exposed_ever==1]["bhcmisid"].nunique()
    n_un  = p[p.exposed_ever==0]["bhcmisid"].nunique()
    assert n_exp == 386, f"Expected 386 exposed CHCs, got {n_exp}"
    assert n_un  == 1256, f"Expected 1,256 never-exposed CHCs, got {n_un}"

def test_simple_atts():
    s = pd.read_csv(ROOT/"results/cs2_simple_all.csv").set_index("outcome")
    # log volume
    assert abs(float(s.loc["log_n_total","att"]) - 0.1378) < 1e-3
    # HTN control
    assert abs(float(s.loc["htn_control_pct","att"]) - 0.0197) < 1e-3
    # Childhood immunization
    assert abs(float(s.loc["imm_child","att"]) - (-0.0317)) < 1e-3

def test_multiple_testing():
    m = pd.read_csv(ROOT/"results/multiple_testing_adjusted.csv").set_index("outcome")
    # Volume + HTN survive every correction
    for col in ["p_bonf","p_holm","p_BH","p_BY","p_RW"]:
        assert float(m.loc["log_n_total",col]) < 0.05, f"Volume failed {col}"
        assert float(m.loc["htn_control_pct",col]) < 0.05, f"HTN failed {col}"
    # Immunization fails every correction
    for col in ["p_bonf","p_holm","p_BH","p_BY","p_RW"]:
        assert float(m.loc["imm_child",col]) >= 0.05, f"Imm unexpectedly survived {col}"

def test_baseline_table():
    t = pd.read_csv(ROOT/"results/table1_baseline.csv")
    # Contains exposed/never columns
    assert any("Exposed" in c for c in t.columns)

if __name__ == "__main__":
    failures = 0
    for name, fn in [(k,v) for k,v in globals().items() if k.startswith("test_")]:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failures += 1
    sys.exit(0 if failures == 0 else 1)
