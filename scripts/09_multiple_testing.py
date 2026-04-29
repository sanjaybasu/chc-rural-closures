"""
Multiple-testing adjustments for the 11-outcome family.

We compare four methods, in increasing order of statistical power:

1. Bonferroni — controls family-wise error rate (FWER); ignores correlation.
   Threshold: alpha/m. Too conservative when outcomes are correlated.

2. Holm step-down — controls FWER; uniformly more powerful than Bonferroni.

3. Benjamini-Hochberg (BH, 1995) — controls false discovery rate (FDR) at q;
   much more appropriate for exploratory multi-outcome studies. Valid under
   independence or positive dependence (PRDS), which is the case for outcomes
   measured at the same CHC.

4. Benjamini-Yekutieli (BY, 2001) — controls FDR under *arbitrary* dependence.
   More conservative than BH; the safe default if dependence is unknown.

We additionally implement a basic Romano-Wolf (2005) stepdown via the
ATT/SE Studentized statistics and a multivariate-normal calibration (a
practical approximation when the full joint bootstrap is computationally
expensive). RW is the modern gold standard in applied microeconomics for
multiple-outcome DiD.
"""
from pathlib import Path
import pandas as pd, numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
RES  = ROOT/"results"

s = pd.read_csv(RES/"cs2_simple_all.csv")
s["z"] = s["att"] / s["se"]
s["p_raw"] = 2*(1 - stats.norm.cdf(np.abs(s["z"])))

m = len(s)
alpha = 0.05

# Bonferroni / Holm / BH / BY
for method, name in [("bonferroni","p_bonf"),("holm","p_holm"),
                     ("fdr_bh","p_BH"),("fdr_by","p_BY")]:
    rej, padj, _, _ = multipletests(s["p_raw"].values, alpha=alpha, method=method)
    s[name] = padj
    s[f"sig_{name.replace('p_','')}"] = rej

# Romano-Wolf approximation:
# We approximate the joint null using the residual correlation across outcomes
# from the panel-level Studentized residuals, then compute the joint distribution
# of max |z| via a multivariate normal.
panel = pd.read_parquet(ROOT/"data/processed/panel.parquet")
extra = pd.read_parquet(ROOT/"data/processed/clinical_extra.parquet")
panel = panel.merge(extra, on=["bhcmisid","year"], how="left")
panel["log_n_total"] = np.log(panel["n_total"].where(panel["n_total"]>0))

OUTCOMES = list(s["outcome"])
Y = panel[OUTCOMES].copy()
# residualize each outcome on CHC and year fixed effects to get the within-CHC noise
for col in OUTCOMES:
    g_chc  = panel.groupby("bhcmisid")[col].transform("mean")
    g_year = panel.groupby("year")[col].transform("mean")
    Y[col] = Y[col] - g_chc - g_year + Y[col].mean()
R = Y.corr()
print("Residual correlation across outcomes (within-CHC, within-year):")
print(R.round(2))

# Romano-Wolf step-down using simulated max-z under the joint MVN null
rng = np.random.default_rng(20260429)
B = 50000
sim = rng.multivariate_normal(np.zeros(m), R.values, size=B)
abs_sim = np.abs(sim)

z_obs = s["z"].abs().values
order = np.argsort(-z_obs)  # largest first

p_rw = np.full(m, np.nan)
remaining = list(order)
prev_p = 0.0
for k, idx in enumerate(order):
    # joint null prob that max|z| over remaining tests >= |z_idx|
    sub = abs_sim[:, remaining]
    p_k = (sub.max(axis=1) >= z_obs[idx]).mean()
    p_k = max(p_k, prev_p)  # monotone enforcement
    p_rw[idx] = p_k
    prev_p = p_k
    remaining.remove(idx)
s["p_RW"]   = p_rw
s["sig_RW"] = s["p_RW"] < alpha

cols = ["outcome","label","att","se","p_raw","p_bonf","p_holm","p_BH","p_BY","p_RW"]
out = s[cols].copy()
for c in ["att","se"]:
    out[c] = out[c].round(4)
for c in ["p_raw","p_bonf","p_holm","p_BH","p_BY","p_RW"]:
    out[c] = out[c].round(4)
out = out.sort_values("p_raw")
print("\n--- Adjusted p-values (sorted by raw p) ---")
print(out.to_string(index=False))

# Summary: which outcomes survive at alpha=0.05 under each method
print("\n--- Outcomes surviving at alpha=0.05 ---")
for method in ["raw","bonf","holm","BH","BY","RW"]:
    col = f"p_{method}" if method!="raw" else "p_raw"
    surv = out[out[col] < alpha]["label"].tolist()
    print(f"  {method:6s}: {surv}")

out.to_csv(RES/"multiple_testing_adjusted.csv", index=False)
print(f"\nSaved {RES}/multiple_testing_adjusted.csv")
