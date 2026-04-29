"""
Staggered difference-in-differences event study estimating the effect of
local rural hospital closure on community health center outcomes.

Primary estimator: Callaway and Sant'Anna (2021) ATT(g,t) via the
`differences` package, which is robust to heterogeneous treatment effects
across cohorts and to negative weighting in two-way fixed-effects
specifications (Goodman-Bacon 2021; de Chaisemartin & D'Haultfoeuille 2020).

Outcomes:
  - share_uninsured            (Table4 / HealthCenterZipCodes)
  - share_medicaid             (HealthCenterZipCodes)
  - n_total (log)              (HealthCenterZipCodes)
  - htn_control_pct            (Table7Clinicalmeasures, 2015+)
  - dm_poor_control_pct        (Table7Clinicalmeasures, 2015+)

Comparison group: never-exposed CHCs (no closure in any served zip 2014-2024).
Pre-period: up to 4 years before exposure.
Post-period: up to 4 years after exposure.
"""
from pathlib import Path
import pandas as pd
import numpy as np
from differences import ATTgt
import warnings
warnings.filterwarnings("ignore")

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
PROC = ROOT/"data/processed"
RES  = ROOT/"results"
RES.mkdir(parents=True, exist_ok=True)

OUTCOMES = {
    "share_uninsured":       "Uninsured share",
    "share_medicaid":        "Medicaid share",
    "log_n_total":           "log(Total patients)",
    "htn_control_pct":       "Hypertension control (%)",
    "dm_poor_control_pct":   "Diabetes A1c>9% (%)",
}

def prep_panel():
    p = pd.read_parquet(PROC/"panel.parquet")
    p = p[(p["year"] >= 2014) & (p["year"] <= 2024)].copy()
    # never-exposed -> first_exposure_year = 0 (convention used by differences pkg)
    p["cohort"] = p["first_exposure_year"].fillna(0).astype(int)
    p["log_n_total"] = np.log(p["n_total"].where(p["n_total"]>0))
    # winsorize shares to [0,1] and drop nonsense rows
    for c in ("share_uninsured","share_medicaid","htn_control_pct","dm_poor_control_pct"):
        p[c] = p[c].clip(lower=0, upper=1)
    return p

def run_cs(p, outcome):
    sub = p[["bhcmisid","year","cohort",outcome]].dropna(subset=[outcome]).copy()
    sub["cohort"] = sub["cohort"].replace(0, np.nan)
    sub = sub.rename(columns={"bhcmisid":"entity_id","year":"time_id","cohort":"cohort"})
    # ATTgt expects entity_id, time_id, cohort columns; never-treated have cohort=0
    att = ATTgt(data=sub.set_index(["entity_id","time_id"]),
                cohort_column="cohort")
    res = att.fit(formula=f"{outcome}", control_group="never_treated",
                  progress_bar=False)
    es = att.aggregate("event")
    return att, es

def run_simple_twfe(p, outcome):
    """Two-way FE with event-time dummies, clustered SE on CHC."""
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    sub = p[["bhcmisid","year","exposed_ever","first_exposure_year",outcome]].dropna()
    sub["et"] = sub["year"] - sub["first_exposure_year"]
    sub.loc[sub["exposed_ever"]==0, "et"] = -999  # never-treated bucket
    # bin event-time to [-4, 4]
    sub["et_bin"] = sub["et"].clip(-4, 4)
    sub["et_bin"] = sub["et_bin"].astype(int).astype(str)
    sub.loc[sub["exposed_ever"]==0, "et_bin"] = "never"
    sub = pd.get_dummies(sub, columns=["et_bin"], drop_first=False)
    # reference: et_bin = -1 (year before treatment); drop that
    ref = "et_bin_-1"
    feat_cols = [c for c in sub.columns if c.startswith("et_bin_") and c != ref and c != "et_bin_never"]
    X = sub[feat_cols].astype(float)
    X = sm.add_constant(X)
    # absorb FE manually: demean by chc and year
    y = sub[outcome].astype(float)
    y_dem = y - sub.groupby("bhcmisid")[outcome].transform("mean") \
                - sub.groupby("year")[outcome].transform("mean") + y.mean()
    Xd = X - X.groupby(sub["bhcmisid"]).transform("mean") \
            - X.groupby(sub["year"]).transform("mean") + X.mean()
    res = sm.OLS(y_dem, Xd, missing="drop").fit(cov_type="cluster",
                                                  cov_kwds={"groups": sub.loc[Xd.index,"bhcmisid"]})
    return res, feat_cols

def main():
    p = prep_panel()
    print(f"panel: {len(p):,} rows, {p['bhcmisid'].nunique():,} CHCs, "
          f"years {p['year'].min()}-{p['year'].max()}")
    print(f"exposed: {p[p['exposed_ever']==1]['bhcmisid'].nunique():,} CHCs")

    summary_rows = []
    for outcome, label in OUTCOMES.items():
        print(f"\n=== {outcome} ({label}) ===")
        try:
            att, es = run_cs(p, outcome)
            es_df = es.copy() if hasattr(es,"copy") else pd.DataFrame(es)
            print(es_df.head(20))
            es_df.to_csv(RES/f"cs_event_{outcome}.csv")
            # overall ATT (simple aggregation across post-periods)
            agg_simple = att.aggregate("simple")
            print(f"simple ATT: {agg_simple}")
        except Exception as e:
            print(f"  CS failed: {e}")

        # TWFE event-study fallback
        try:
            res, feat = run_simple_twfe(p, outcome)
            coef = res.params[feat]
            se = res.bse[feat]
            tw = pd.DataFrame({"event_time": [int(c.replace("et_bin_","")) for c in feat],
                               "coef": coef.values, "se": se.values})
            tw["ci_lo"] = tw["coef"] - 1.96*tw["se"]
            tw["ci_hi"] = tw["coef"] + 1.96*tw["se"]
            tw = tw.sort_values("event_time").reset_index(drop=True)
            print("TWFE event-study coefficients:")
            print(tw)
            tw.to_csv(RES/f"twfe_event_{outcome}.csv", index=False)
            for _,r in tw.iterrows():
                summary_rows.append({"outcome":outcome,"label":label,
                                     **r.to_dict()})
        except Exception as e:
            print(f"  TWFE failed: {e}")

    pd.DataFrame(summary_rows).to_csv(RES/"event_study_summary.csv", index=False)
    print(f"\nResults written to {RES}/")

if __name__ == "__main__":
    main()
