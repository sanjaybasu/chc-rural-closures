"""Figures with full outcome set: forest plot of simple ATTs + multi-panel event study."""
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib.pyplot as plt

ROOT = Path("/Users/sanjaybasu/waymark-local/notebooks/chc-rural-closures")
RES  = ROOT/"results"
FIG  = ROOT/"figures"

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,
                     "axes.spines.top":False,"axes.spines.right":False})

LABEL_ORDER = [
    ("log_n_total",         "log(Total patients)"),
    ("share_uninsured",     "Uninsured share"),
    ("share_medicaid",      "Medicaid share"),
    ("htn_control_pct",     "Hypertension control"),
    ("dm_poor_control_pct", "Diabetes A1c>9% (poor)"),
    ("imm_child",           "Childhood immunization"),
    ("pap_screen",          "Cervical cancer screening"),
    ("crc_screen",          "Colorectal cancer screening"),
    ("bmi_adult",           "Adult BMI follow-up"),
    ("tobacco",             "Tobacco assess+intervention"),
    ("depr_screen",         "Depression screen+follow-up"),
]

# Forest plot: simple ATTs
def forest():
    s = pd.read_csv(RES/"cs2_simple_all.csv")
    s = s.set_index("outcome").loc[[k for k,_ in LABEL_ORDER]].reset_index()
    s["label"] = [lab for _,lab in LABEL_ORDER]
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    y = np.arange(len(s))[::-1]
    sig = s["sig"].astype(str).str.strip()=="*"
    colors = ["#1f4e79" if x else "#888888" for x in sig]
    for yi,(att,lo,hi,c) in enumerate(zip(s["att"], s["ci_lo"], s["ci_hi"], colors)):
        ax.plot([lo,hi], [y[yi],y[yi]], color=c, lw=1.5)
        ax.plot([lo,lo], [y[yi]-0.15,y[yi]+0.15], color=c, lw=1.2)
        ax.plot([hi,hi], [y[yi]-0.15,y[yi]+0.15], color=c, lw=1.2)
        ax.scatter(att, y[yi], s=45, color=c, zorder=5, edgecolor="black", lw=0.5)
    ax.axvline(0, color="black", lw=0.7)
    ax.set_yticks(y); ax.set_yticklabels(s["label"])
    ax.set_xlabel("Callaway–Sant'Anna simple ATT  (log units for volume; pp for shares & %)")
    ax.set_title("Effect of local rural hospital closure on CHC outcomes\n"
                 "(exposed vs. never-exposed, 2014–2024)", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIG/"figure1_forest.png", dpi=200, bbox_inches="tight")
    plt.savefig(FIG/"figure1_forest.pdf", bbox_inches="tight")
    print("saved fig2")

def event_panels():
    fig, axes = plt.subplots(4, 3, figsize=(11.5, 12))
    axes = axes.flatten()
    for i,(out,label) in enumerate(LABEL_ORDER):
        path = RES/f"cs2_event_{out}.csv"
        if not path.exists():
            axes[i].axis("off"); continue
        d = pd.read_csv(path)
        d = d[(d["rel"]>=-5) & (d["rel"]<=8)].dropna(subset=["att"])
        ax = axes[i]
        sig_mask = (d["sig"].astype(str).str.strip()=="*")
        ax.errorbar(d["rel"], d["att"], yerr=[d["att"]-d["ci_lo"], d["ci_hi"]-d["att"]],
                    fmt="o", color="#1f4e79", capsize=2.5, lw=1.2, ms=4)
        ax.scatter(d.loc[sig_mask,"rel"], d.loc[sig_mask,"att"],
                   color="#c00000", zorder=5, s=22)
        ax.axhline(0, color="black", lw=0.5)
        ax.axvline(-0.5, color="red", lw=0.6, ls="--", alpha=0.6)
        ax.set_title(label, fontsize=9)
        ax.set_xlabel("Years from closure", fontsize=8)
    for j in range(len(LABEL_ORDER), len(axes)):
        axes[j].axis("off")
    fig.suptitle("Event-study estimates (Callaway–Sant'Anna ATT) for 11 CHC outcomes",
                 fontsize=11, fontweight="bold", y=0.995)
    plt.tight_layout()
    plt.savefig(FIG/"figure2_event_panels.png", dpi=200, bbox_inches="tight")
    plt.savefig(FIG/"figure2_event_panels.pdf", bbox_inches="tight")
    print("saved fig3")

if __name__ == "__main__":
    forest()
    event_panels()
