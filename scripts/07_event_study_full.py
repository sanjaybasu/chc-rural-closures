"""
Run Callaway-Sant'Anna staggered DiD on the FULL outcome set:
volume + payer mix + 8 clinical quality measures (HTN, DM, plus 6 from
Table6BClinicalmeasures). Save tidy results for figures and tables.
"""
from pathlib import Path
import pandas as pd, numpy as np, warnings
from differences import ATTgt
warnings.filterwarnings("ignore")

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
PROC = ROOT/"data/processed"
RES  = ROOT/"results"

OUTCOMES = {
    # volume + payer mix (from zips.parquet via panel)
    "log_n_total":         "log(Total patients)",
    "share_uninsured":     "Uninsured share",
    "share_medicaid":      "Medicaid share",
    # clinical (from clinical.parquet)
    "htn_control_pct":     "Hypertension control",
    "dm_poor_control_pct": "Diabetes A1c>9% (poor)",
    # clinical (from clinical_extra.parquet)
    "imm_child":           "Childhood immunization",
    "pap_screen":          "Cervical cancer screening",
    "bmi_adult":           "Adult BMI follow-up",
    "tobacco":             "Tobacco assessment+intervention",
    "crc_screen":          "Colorectal cancer screening",
    "depr_screen":         "Depression screen+follow-up",
}

def build_panel():
    p = pd.read_parquet(PROC/"panel.parquet")
    extra = pd.read_parquet(PROC/"clinical_extra.parquet")
    extra["year"] = extra["year"].astype(int)
    p["year"] = p["year"].astype(int)
    p = p.merge(extra, on=["bhcmisid","year"], how="left")
    p["log_n_total"] = np.log(p["n_total"].where(p["n_total"]>0))
    p["cohort"] = p["first_exposure_year"].fillna(0).astype(int)
    p["cohort"] = p["cohort"].replace(0, np.nan)
    return p

def fit_cs(p, outcome):
    sub = p[["bhcmisid","year","cohort",outcome]].dropna(subset=[outcome]).copy()
    sub = sub.rename(columns={"bhcmisid":"entity_id","year":"time_id"})
    att = ATTgt(data=sub.set_index(["entity_id","time_id"]),
                cohort_column="cohort")
    att.fit(formula=outcome, control_group="never_treated", progress_bar=False)
    es = att.aggregate("event")
    simple = att.aggregate("simple")
    return att, es, simple

def to_tidy(es, outcome, label):
    """Flatten the multi-index event aggregation into a tidy DF."""
    df = es.copy()
    df.columns = ["att","se","ci_lo","ci_hi","sig"]
    df = df.reset_index().rename(columns={df.index.name:"rel"})
    if "rel" not in df.columns:
        df = df.rename(columns={df.columns[0]:"rel"})
    df["outcome"] = outcome; df["label"] = label
    df["rel"] = pd.to_numeric(df["rel"], errors="coerce")
    return df

def main():
    p = build_panel()
    print(f"panel: {len(p):,} CHC-yrs  centers={p['bhcmisid'].nunique():,}")

    all_es = []
    simple_rows = []
    for out, label in OUTCOMES.items():
        try:
            _, es, simple = fit_cs(p, out)
            tidy = to_tidy(es, out, label)
            tidy.to_csv(RES/f"cs2_event_{out}.csv", index=False)
            all_es.append(tidy)
            sdf = simple.copy()
            sdf.columns = ["att","se","ci_lo","ci_hi","sig"]
            sdf["outcome"]=out; sdf["label"]=label
            simple_rows.append(sdf)
            print(f"  {out:25s} ATT={float(sdf['att'].iloc[0]):+.4f} "
                  f"[{float(sdf['ci_lo'].iloc[0]):+.4f}, {float(sdf['ci_hi'].iloc[0]):+.4f}] "
                  f"{'*' if str(sdf['sig'].iloc[0]).strip()=='*' else ''}")
        except Exception as e:
            print(f"  {out}: FAILED {e}")

    pd.concat(all_es, ignore_index=True).to_csv(RES/"cs2_event_all.csv", index=False)
    pd.concat(simple_rows, ignore_index=True).to_csv(RES/"cs2_simple_all.csv", index=False)
    print(f"\nwrote results to {RES}/cs2_*.csv")

if __name__ == "__main__":
    main()
