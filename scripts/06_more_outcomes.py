"""
Extract additional clinical quality measures from Table6BClinicalmeasures
(2015-2024) and add them to the analysis panel. Six measures with stable
column names across years: childhood immunization, cervical cancer screening,
adult BMI/follow-up, tobacco assessment+intervention, colorectal cancer
screening, depression screening+follow-up.
"""
from pathlib import Path
import pandas as pd, re

UDS_DIR = Path("/Users/sanjaybasu/waymark-local/data/uds")
PROC = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures/data/processed")

YEARS = range(2015, 2025)

# (output_col, list-of-keyword-tokens that must all appear in the column name)
MEASURES = [
    ("imm_child",   ["immun"]),
    ("pap_screen",  ["pap"]),
    ("bmi_adult",   ["adults","bmi","follow-up"]),
    ("tobacco",     ["tobacco","intervention"]),
    ("crc_screen",  ["colorectal"]),
    ("depr_screen", ["depression","followup"]),
]

def norm(s): return re.sub(r"[\s\-_]+","",str(s)).lower()

def safe_num(x):
    if x is None or (isinstance(x,str) and x.strip() in ("","--","-","*")): return None
    try: return float(x)
    except: return None

def find_col(headers, tokens):
    norm_tokens = [t.replace("-","").lower() for t in tokens]
    for i,h in enumerate(headers):
        nh = norm(h)
        if nh.startswith("%") and all(t in nh for t in norm_tokens):
            return i
    return None

def load(year, tag):
    p = UDS_DIR/f"{tag}-{year}.xlsx"
    if not p.exists(): return None
    df = pd.read_excel(p, "Table6BClinicalmeasures", dtype=str)
    headers = list(df.columns)
    out = {"bhcmisid": df.iloc[:,0].astype(str).values}
    for col, tokens in MEASURES:
        idx = find_col(headers, tokens)
        if idx is None:
            out[col] = [None]*len(df)
            print(f"    {year} {tag}: missing {col}")
        else:
            out[col] = df.iloc[:,idx].map(safe_num).values
    o = pd.DataFrame(out); o["year"]=year
    return o

def main():
    rows = []
    for y in YEARS:
        for t in ("h80","lal"):
            d = load(y, t)
            if d is not None: rows.append(d)
    df = pd.concat(rows, ignore_index=True)
    # values are reported as percentages (0-100); normalize to [0,1]
    for col,_ in MEASURES:
        df[col] = df[col].astype(float)/100.0
        df.loc[df[col]>1, col] = None  # trash values
        df.loc[df[col]<0, col] = None
    df.to_parquet(PROC/"clinical_extra.parquet", index=False)
    print(f"\nwrote {len(df):,} rows; non-null counts:")
    print(df[[c for c,_ in MEASURES]].notna().sum())
    print("\nmedians:")
    print(df[[c for c,_ in MEASURES]].median())

if __name__ == "__main__":
    main()
