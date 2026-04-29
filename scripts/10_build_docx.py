"""
Assemble the JHCPU submission DOCX from the manuscript markdown,
with Tables 1, 2, and 3 rendered from CSVs and Figures 1-3 embedded.

Output: manuscript/manuscript_jhcpu.docx
"""
from pathlib import Path
import pandas as pd
import subprocess, re

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
MS_MD = ROOT/"manuscript/manuscript.md"
RES = ROOT/"results"
FIG = ROOT/"figures"
OUT_MD = ROOT/"manuscript/manuscript_jhcpu_assembled.md"
OUT_DOCX = ROOT/"manuscript/manuscript_jhcpu.docx"

# --- build markdown tables from CSVs ---
def md_table(df, title):
    cols = list(df.columns)
    head = "| " + " | ".join(cols) + " |"
    sep  = "| " + " | ".join(["---"]*len(cols)) + " |"
    rows = ["| " + " | ".join(str(x) for x in r) + " |" for r in df.values]
    return f"**{title}**\n\n" + "\n".join([head, sep] + rows) + "\n"

t1 = pd.read_csv(RES/"table1_baseline.csv")
t1_md = md_table(t1, "Table 1. Baseline (2014) characteristics of CHCs by closure exposure")

t2_src = pd.read_csv(RES/"cs2_simple_all.csv")
LABEL_ORDER = [
    ("log_n_total", "log(Total patients)"),
    ("share_uninsured", "Uninsured share (pp)"),
    ("share_medicaid", "Medicaid share (pp)"),
    ("htn_control_pct", "Hypertension control (pp)"),
    ("dm_poor_control_pct", "Diabetes A1c>9% (pp)"),
    ("imm_child", "Childhood immunization (pp)"),
    ("pap_screen", "Cervical cancer screening (pp)"),
    ("crc_screen", "Colorectal cancer screening (pp)"),
    ("bmi_adult", "Adult BMI follow-up (pp)"),
    ("tobacco", "Tobacco assess+intervention (pp)"),
    ("depr_screen", "Depression screen+follow-up (pp)"),
]
t2_src = t2_src.set_index("outcome").loc[[k for k,_ in LABEL_ORDER]].reset_index()
def fmt_att(row, scale=1.0):
    v = float(row["att"])*scale
    lo = float(row["ci_lo"])*scale
    hi = float(row["ci_hi"])*scale
    return f"{v:+.3f}", f"{lo:+.3f} to {hi:+.3f}"
rows = []
for (k,label), (_,r) in zip(LABEL_ORDER, t2_src.iterrows()):
    scale = 1.0 if k=="log_n_total" else 100.0
    att, ci = fmt_att(r, scale)
    rows.append([label, att, ci])
t2 = pd.DataFrame(rows, columns=["Outcome","Simple ATT","95% CI"])
t2_md = md_table(t2, "Table 2. Callaway–Sant'Anna simple ATT estimates, exposed vs. never-exposed CHCs (n=1,642 CHCs; 386 exposed, 1,256 never-exposed; 116 closures 2014–2024). For log(Total patients), values are log units; for all other outcomes, percentage points (pp).")

t3_src = pd.read_csv(RES/"multiple_testing_adjusted.csv")
order_map = {k:i for i,(k,_) in enumerate(LABEL_ORDER)}
t3_src["sort"] = t3_src["outcome"].map(order_map)
t3_src = t3_src.sort_values("sort")
t3 = t3_src[["label","p_raw","p_bonf","p_holm","p_BH","p_BY","p_RW"]].copy()
t3.columns = ["Outcome","Raw p","Bonferroni","Holm","BH (FDR)","BY (FDR)","Romano-Wolf"]
for c in t3.columns[1:]:
    t3[c] = t3[c].apply(lambda x: f"{float(x):.4f}" if float(x)>=0.0001 else "<.0001")
t3_md = md_table(t3, "Table 3. Multiple-testing–adjusted p-values across 11 pre-specified outcomes.")

# --- assemble final markdown ---
ms = MS_MD.read_text()

# inject tables in place of the placeholder block at end
fig_block = """
## Figures and Tables

**Figure 1.** Forest plot of Callaway–Sant'Anna simple ATTs across all 11 pre-specified outcomes, exposed vs. never-exposed CHCs, 2014–2024. Blue intervals indicate statistical significance at 5% (raw p<0.05); intervals are 95% confidence intervals.

![Figure 1](../figures/fig2_forest_all_outcomes.png)

**Figure 2.** Event-study Callaway–Sant'Anna ATT estimates by relative period for all 11 outcomes. Red filled circles indicate event-time-specific 95% pointwise confidence bands excluding zero. Reference period: year before exposure.

![Figure 2](../figures/fig3_event_panels.png)

"""
# remove the old placeholder
ms_clean = re.sub(r"## Figures and Tables.*$", "", ms, flags=re.DOTALL).rstrip()

assembled = ms_clean + "\n\n---\n\n" + fig_block + "\n" + t1_md + "\n" + t2_md + "\n" + t3_md + "\n"

OUT_MD.write_text(assembled)
print(f"wrote {OUT_MD}")

# --- pandoc ---
cmd = ["pandoc", str(OUT_MD), "-o", str(OUT_DOCX),
       "--from=markdown", "--to=docx",
       "--resource-path", str(ROOT),
       "--metadata", "title=Rural Hospital Closures and CHC Capacity"]
res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("pandoc stderr:", res.stderr)
print(f"wrote {OUT_DOCX}  ({OUT_DOCX.stat().st_size:,} bytes)")
