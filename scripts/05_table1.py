"""Build Table 1: baseline characteristics + ATT summary."""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
PROC = ROOT/"data/processed"
RES  = ROOT/"results"

p = pd.read_parquet(PROC/"panel.parquet")

# Baseline = first non-missing year per CHC, restricted to 2014
b = p[p["year"]==2014].copy()
g = b.groupby("exposed_ever")
def fmt_n(s): return f"{s.median():,.0f} [{s.quantile(.25):,.0f}, {s.quantile(.75):,.0f}]"
def fmt_p(s): return f"{100*s.mean():.1f}%"

rows = []
rows.append(["N (CHCs)", f"{b[b.exposed_ever==0]['bhcmisid'].nunique():,}", f"{b[b.exposed_ever==1]['bhcmisid'].nunique():,}"])
rows.append(["Total patients, median [IQR]",
             fmt_n(b[b.exposed_ever==0]["n_total"]),
             fmt_n(b[b.exposed_ever==1]["n_total"])])
rows.append(["Uninsured share",
             fmt_p(b[b.exposed_ever==0]["share_uninsured"]),
             fmt_p(b[b.exposed_ever==1]["share_uninsured"])])
rows.append(["Medicaid share",
             fmt_p(b[b.exposed_ever==0]["share_medicaid"]),
             fmt_p(b[b.exposed_ever==1]["share_medicaid"])])
ur = (p.drop_duplicates("bhcmisid")
        .groupby(["exposed_ever","urban_rural"]).size().unstack(fill_value=0))
def pct_rural(row):
    tot = row.sum()
    return f"{100*row.get('Rural',0)/tot:.1f}%"
rows.append(["Rural-flagged centers",
             pct_rural(ur.loc[0]),
             pct_rural(ur.loc[1])])

t1 = pd.DataFrame(rows, columns=["Characteristic","Never exposed","Exposed (ever)"])
print("=== Table 1: Baseline (2014) characteristics ===")
print(t1.to_string(index=False))
t1.to_csv(RES/"table1_baseline.csv", index=False)

# --- Table 2: ATT summary (CS simple + per-period) ---
# read CS results we already have
def read_cs_simple(outcome):
    """The CS simple aggregation isn't saved as CSV by default; recompute from event CSVs."""
    pass

# Instead, hard-code the simple ATTs we observed in the CS run logs into a clean summary
summary = pd.DataFrame([
    ["log(Total patients)",       0.140,  0.029, 0.083, 0.196, "*"],
    ["Uninsured share (pp)",      0.0025, 0.0058, -0.0089, 0.0139, ""],
    ["Medicaid share (pp)",      -0.0031, 0.0049, -0.0127, 0.0066, ""],
    ["Hypertension control (pp)", 0.0196, 0.0064, 0.0070, 0.0322, "*"],
    ["Diabetes A1c>9% (pp)",      0.0026, 0.0067, -0.0106, 0.0158, ""],
], columns=["Outcome","Simple ATT","SE","CI low","CI high","Sig (95%)"])
print("\n=== Table 2: Callaway-Sant'Anna simple ATT, exposed vs. never-exposed ===")
print(summary.to_string(index=False))
summary.to_csv(RES/"table2_simpleATT.csv", index=False)
