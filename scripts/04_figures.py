"""
Generate event-study plots and a summary forest plot from CS results.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
RES  = ROOT/"results"
FIG  = ROOT/"figures"
FIG.mkdir(parents=True, exist_ok=True)

OUTCOMES = {
    "share_uninsured":     ("Uninsured share",          "pp"),
    "share_medicaid":      ("Medicaid share",           "pp"),
    "log_n_total":         ("log(Total patients)",      "log units"),
    "htn_control_pct":     ("Hypertension control",     "pp"),
    "dm_poor_control_pct": ("Diabetes A1c>9% (poor)",   "pp"),
}

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,
                     "axes.spines.top":False,"axes.spines.right":False})

def parse_cs(path):
    """CS CSV has 3 header rows then data starting at row 4 with relative_period as first col."""
    df = pd.read_csv(path, skiprows=4, header=None,
                     names=["rel","att","se","lo","hi","sig"])
    df["rel"] = pd.to_numeric(df["rel"], errors="coerce")
    for c in ("att","se","lo","hi"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["rel","att"])

def event_plot(ax, df_cs, df_twfe, title, units):
    # CS
    if df_cs is not None and len(df_cs):
        d = df_cs.dropna(subset=["att"])
        d = d[(d["rel"]>=-5) & (d["rel"]<=8)]
        ax.errorbar(d["rel"], d["att"], yerr=[d["att"]-d["lo"], d["hi"]-d["att"]],
                    fmt="o", color="#1f4e79", capsize=2.5, lw=1.2, ms=4,
                    label="Callaway–Sant'Anna")
    # TWFE
    if df_twfe is not None and len(df_twfe):
        d = df_twfe.dropna(subset=["coef"])
        d = d[(d["event_time"]>=-5) & (d["event_time"]<=8)]
        ax.errorbar(d["event_time"]+0.18, d["coef"], yerr=1.96*d["se"],
                    fmt="s", color="#999999", capsize=2.5, lw=1.0, ms=3.5,
                    alpha=0.65, label="TWFE")
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(-0.5, color="red", lw=0.6, ls="--", alpha=0.6)
    ax.set_xlabel("Years relative to first exposure")
    ax.set_ylabel(f"ATT ({units})")
    ax.set_title(title, fontsize=10)
    ax.legend(loc="best", fontsize=7, frameon=False)

def main():
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.5))
    axes = axes.flatten()
    for i,(out,(label,units)) in enumerate(OUTCOMES.items()):
        ax = axes[i]
        cs_path = RES/f"cs_event_{out}.csv"
        tw_path = RES/f"twfe_event_{out}.csv"
        df_cs = parse_cs(cs_path) if cs_path.exists() else None
        df_tw = pd.read_csv(tw_path) if tw_path.exists() else None
        event_plot(ax, df_cs, df_tw, label, units)
    axes[-1].axis("off")
    fig.suptitle("Event-study estimates: rural hospital closure exposure on CHC outcomes",
                 fontsize=11, fontweight="bold", y=0.99)
    plt.tight_layout()
    out = FIG/"fig1_event_study.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.savefig(FIG/"fig1_event_study.pdf", bbox_inches="tight")
    print("saved", out)

if __name__ == "__main__":
    main()
