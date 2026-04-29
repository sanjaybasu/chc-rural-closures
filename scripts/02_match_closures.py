"""
Match UNC Sheps Center rural hospital closures to UDS health centers via
zip-code service-area overlap, then build the analysis panel.

Treatment definition (preferred specification):
  A CHC is "exposed" in calendar year t if a rural hospital located in a
  ZIP code that the CHC reported serving at any point during 2014-2024
  closed (complete or converted) in year t. Treatment cohort = first
  exposure year for each CHC. Never-treated CHCs are the comparison group.

Sensitivity definition (sec):
  Restrict treatment to *complete* closures (excluding converted closures).

Outputs:
  data/processed/closures_matched.parquet   (CHC-level: first_exposure_year)
  data/processed/panel.parquet              (CHC x year analysis panel)
"""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
PROC = ROOT/"data/processed"

def main():
    info = pd.read_parquet(PROC/"info.parquet")
    zips = pd.read_parquet(PROC/"zips.parquet")
    clin = pd.read_parquet(PROC/"clinical.parquet")

    # --- closures ---
    cl = pd.read_excel(ROOT/"data/raw/sheps_closures.xlsx", dtype=str)
    cl.columns = [c.strip().replace("\n"," ").lower()
                       .replace(" ","_").replace("/","_")
                       .replace("(","").replace(")","").replace(";","")
                  for c in cl.columns]
    # locate the complete/converted column (name varies)
    comp_col = [c for c in cl.columns if "complete" in c and "converted" in c][0]
    cl["closure_year"] = pd.to_numeric(cl["closure_year"], errors="coerce")
    cl["zip5"] = cl["zip"].astype(str).str.zfill(5).str[:5]
    cl["complete"] = pd.to_numeric(cl[comp_col], errors="coerce") == 0
    print(f"closures total: {len(cl)}, with valid year: {cl['closure_year'].notna().sum()}, "
          f"complete: {cl['complete'].sum()}")
    print(f"closure year range: {int(cl['closure_year'].min())}-{int(cl['closure_year'].max())}")

    # --- service area: union of all served zip codes per CHC over the panel ---
    svc = (zips[["bhcmisid","service_zip"]].drop_duplicates()
                                            .dropna())
    print(f"service-area pairs (CHC, zip): {len(svc):,}")

    # --- match: for each CHC, find earliest closure_year among hospitals in served zips ---
    cl_panel = cl[["zip5","closure_year","complete"]].dropna(subset=["zip5","closure_year"])
    cl_panel = cl_panel[(cl_panel["closure_year"] >= 2014) & (cl_panel["closure_year"] <= 2024)]

    matched = svc.merge(cl_panel, left_on="service_zip", right_on="zip5", how="inner")
    print(f"matched CHC-closure rows: {len(matched):,} "
          f"({matched['bhcmisid'].nunique():,} unique CHCs exposed at some point)")

    first_exp = (matched.groupby("bhcmisid")
                        .agg(first_exposure_year=("closure_year","min"),
                             n_closures_in_area=("closure_year","count"),
                             any_complete=("complete","max"))
                        .reset_index())
    first_exp.to_parquet(PROC/"closures_matched.parquet", index=False)

    # --- center-level cross-section attributes (most recent) ---
    info_latest = (info.sort_values("year")
                       .groupby("bhcmisid").tail(1)
                       [["bhcmisid","name","city","state","zip5","urban_rural"]])

    # --- year-level CHC outcomes ---
    yr_zip = (zips.groupby(["bhcmisid","year"], as_index=False)
                  .agg(n_total=("n_total","sum"),
                       n_uninsured=("n_uninsured","sum"),
                       n_medicaid=("n_medicaid","sum")))
    yr_zip["share_uninsured"] = yr_zip["n_uninsured"] / yr_zip["n_total"]
    yr_zip["share_medicaid"]  = yr_zip["n_medicaid"]  / yr_zip["n_total"]

    cl_yr = clin.copy()
    cl_yr["htn_control_pct"] = (cl_yr["htn_controlled"] / cl_yr["htn_n"]).where(cl_yr["htn_n"]>0)
    cl_yr["dm_poor_control_pct"] = (cl_yr["dm_a1c_gt9"] / cl_yr["dm_n"]).where(cl_yr["dm_n"]>0)

    panel = (yr_zip.merge(cl_yr[["bhcmisid","year","htn_n","htn_controlled",
                                  "dm_n","dm_a1c_gt9","htn_control_pct","dm_poor_control_pct"]],
                          on=["bhcmisid","year"], how="left")
                   .merge(info_latest, on="bhcmisid", how="left")
                   .merge(first_exp, on="bhcmisid", how="left"))
    panel["exposed_ever"] = panel["first_exposure_year"].notna().astype(int)
    panel["event_time"]   = panel["year"] - panel["first_exposure_year"]
    panel["post"]         = ((panel["event_time"] >= 0) & panel["exposed_ever"].astype(bool)).astype(int)

    panel.to_parquet(PROC/"panel.parquet", index=False)

    # quick summary
    print("\n--- panel summary ---")
    print(f"CHC-years total: {len(panel):,}")
    print(f"unique CHCs:     {panel['bhcmisid'].nunique():,}")
    print(f"exposed CHCs:    {panel.loc[panel['exposed_ever']==1,'bhcmisid'].nunique():,}")
    print(f"exposure cohorts (first_exposure_year):")
    print(panel.dropna(subset=['first_exposure_year'])
                .drop_duplicates('bhcmisid')['first_exposure_year']
                .value_counts().sort_index())
    print("\noutcome means by exposure status (panel-wide):")
    print(panel.groupby('exposed_ever')[['n_total','share_uninsured','share_medicaid',
                                          'htn_control_pct','dm_poor_control_pct']].mean())

if __name__ == "__main__":
    main()
