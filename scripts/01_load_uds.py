"""
Load HRSA UDS public Excel files (2014-2024, consistent schema) and produce
analysis-ready parquet tables.

Inputs:  /Users/sanjaybasu/waymark-local/data/uds/h80-YYYY.xlsx (grantees)
                                                lal-YYYY.xlsx (look-alikes)
Outputs: data/processed/info.parquet     (CHC x year identifiers)
         data/processed/zips.parquet     (CHC x year x zip with patient mix)
         data/processed/clinical.parquet (CHC x year HTN/DM aggregates)

Design: 2014+ schema is uniform. Earlier years use different sheet names and
column conventions; we exclude them to keep the panel clean. We pull both
H80 grantees and Look-Alikes (LAL) since both report UDS and are part of the
Health Center Program.
"""
from pathlib import Path
import pandas as pd
import re

UDS_DIR = Path("/Users/sanjaybasu/waymark-local/data/uds")
OUT_DIR = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures/data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = range(2014, 2025)  # 2014-2024 inclusive (consistent schema)

def norm(s):
    """Normalize column name: strip spaces, lowercase."""
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s)).lower()

def safe_num(x):
    """Convert UDS suppression markers ('--', '-', '*', '') to NaN."""
    if x is None or (isinstance(x, str) and x.strip() in ("--", "-", "*", "")):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def load_one_year(path: Path, year: int, source: str):
    """Return three dataframes: info, zips, clinical for one file."""
    print(f"  loading {path.name} ({source} {year})")
    xl = pd.ExcelFile(path, engine="openpyxl")

    # --- HealthCenterInfo ---
    info = pd.read_excel(xl, "HealthCenterInfo", dtype=str)
    info.columns = [norm(c) for c in info.columns]
    info = info.rename(columns={
        "bhcmisid": "bhcmisid",
        "grantnumber": "grant_number",
        "reportingyear": "year",
        "healthcentername": "name",
        "healthcentercity": "city",
        "healthcenterstate": "state",
        "healthcenterzipcode": "zip5",
        "urbanruralflag": "urban_rural",
    })
    keep = ["bhcmisid","grant_number","year","name","city","state","zip5","urban_rural"]
    info = info[[c for c in keep if c in info.columns]].copy()
    info["year"] = year
    info["source"] = source
    info["zip5"] = info["zip5"].astype(str).str.zfill(5).str[:5]

    # --- HealthCenterZipCodes ---
    zips = pd.read_excel(xl, "HealthCenterZipCodes", dtype=str)
    zips.columns = [norm(c) for c in zips.columns]
    rename_map = {
        "bhcmisid": "bhcmisid",
        "reportingyear": "year",
        "zipcode": "service_zip",
        "zipcodetype": "zip_type",
        "none_uninsuredpatients": "n_uninsured",
        "medicaid_chip_otherpublicpatients": "n_medicaid",
        "medicarepatients": "n_medicare",
        "privateinsurancepatients": "n_private",
        "privatepatients": "n_private",
        "totalnumberofpatients": "n_total",
    }
    zips = zips.rename(columns=rename_map)
    keep = ["bhcmisid","year","service_zip","zip_type",
            "n_uninsured","n_medicaid","n_medicare","n_private","n_total"]
    zips = zips[[c for c in keep if c in zips.columns]].copy()
    zips["year"] = year
    for c in ("n_uninsured","n_medicaid","n_medicare","n_private","n_total"):
        if c in zips.columns:
            zips[c] = zips[c].map(safe_num)
    zips["service_zip"] = zips["service_zip"].astype(str).str.zfill(5).str[:5]

    # --- Table7Clinicalmeasures (aggregated to CHC level) ---
    cli = pd.read_excel(xl, "Table7Clinicalmeasures", dtype=str)
    cli.columns = [norm(c) for c in cli.columns]
    # Column names contain 'totalhypertensivepatients', 'totalestimated#patientswithcontrolledbloodpressure',
    # 'totalpatientswithdiabetes', 'estimatednumberofpatientswithhba1c>9%'
    # These vary slightly across years; pattern-match.
    def find(col_pat):
        for c in cli.columns:
            if all(p in c for p in col_pat):
                return c
        return None
    c_id    = find(["bhcmisid"])
    c_htn_n = find(["totalhypertensive"])
    c_htn_c = find(["controlledblood"])
    c_dm_n  = find(["totalpatients","diabet"])
    c_dm_h  = find(["hba1c>9"])
    needed = [c_id, c_htn_n, c_htn_c, c_dm_n, c_dm_h]
    if any(c is None for c in needed):
        print(f"    WARN missing clinical cols in {path.name}: {needed}")
        clin = pd.DataFrame(columns=["bhcmisid","year","htn_n","htn_controlled",
                                     "dm_n","dm_a1c_gt9"])
    else:
        sub = cli[[c_id, c_htn_n, c_htn_c, c_dm_n, c_dm_h]].copy()
        sub.columns = ["bhcmisid","htn_n","htn_controlled","dm_n","dm_a1c_gt9"]
        for c in ("htn_n","htn_controlled","dm_n","dm_a1c_gt9"):
            sub[c] = sub[c].map(safe_num)
        # rows are stratified by race/ethnicity; sum across to get center totals
        clin = (sub.groupby("bhcmisid", as_index=False)
                   .agg({"htn_n":"sum","htn_controlled":"sum",
                         "dm_n":"sum","dm_a1c_gt9":"sum"}))
        clin["year"] = year
    return info, zips, clin

def main():
    info_all, zip_all, clin_all = [], [], []
    for yr in YEARS:
        for tag in ("h80", "lal"):
            p = UDS_DIR / f"{tag}-{yr}.xlsx"
            if not p.exists():
                continue
            i, z, c = load_one_year(p, yr, tag)
            info_all.append(i); zip_all.append(z); clin_all.append(c)
    info = pd.concat(info_all, ignore_index=True)
    zips = pd.concat(zip_all, ignore_index=True)
    clin = pd.concat(clin_all, ignore_index=True)
    info.to_parquet(OUT_DIR/"info.parquet", index=False)
    zips.to_parquet(OUT_DIR/"zips.parquet", index=False)
    clin.to_parquet(OUT_DIR/"clinical.parquet", index=False)
    print(f"\nWrote info  rows={len(info):,}  centers={info['bhcmisid'].nunique():,}")
    print(f"Wrote zips  rows={len(zips):,}")
    print(f"Wrote clin  rows={len(clin):,}")

if __name__ == "__main__":
    main()
