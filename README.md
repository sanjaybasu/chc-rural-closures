# Rural Hospital Closures and CHC Capacity (2014–2024)

[![Reproducibility](https://img.shields.io/badge/reproducibility-fully%20automated-brightgreen)](#reproducing-the-analysis)
[![Data](https://img.shields.io/badge/data-public-blue)](#data-sources)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Reproducible analysis code for a Brief Communication submitted to the
*Journal of Health Care for the Poor and Underserved* NACHC Special
Supplement on Policy Impact and Innovations in Community Health Centers.

> **Headline:** Across 1,642 community health centers (CHCs) and 116 rural
> hospital closures (2014–2024), exposed CHCs absorbed +13.8% more patients
> (95% CI +8.1% to +19.5%) without erosion of payer mix or measured quality.
> Hypertension control improved by 1.97 percentage points (95% CI +0.71
> to +3.24). Both findings survive Bonferroni, Holm, Benjamini-Hochberg,
> Benjamini-Yekutieli, and Romano-Wolf multiple-testing corrections across
> 11 pre-specified outcomes.

## Repository contents

```
chc-rural-closures/
├── scripts/             Analysis pipeline (numbered 01-09; run in order)
├── data/
│   ├── raw/             Sheps Center closure registry (committed); UDS files (gitignored, see below)
│   └── processed/       Generated parquets (gitignored)
├── results/             CSV outputs of every script
├── figures/             PNG + PDF figures
├── tests/               Smoke tests
├── manuscript/          Manuscript markdown, title page, cover letter
├── Makefile             One-command pipeline
├── requirements.txt     Pinned Python deps
├── environment.yml      Conda environment (alternative)
└── CITATION.cff
```

## Reproducing the analysis

### Prerequisites
- Python ≥3.11 (developed on 3.12)
- ~2 GB RAM, ~5 minutes runtime on a modern laptop

### One-time data setup

The HRSA Uniform Data System (UDS) public files are not redistributed here
because the official source (HRSA Bureau of Primary Health Care Electronic
Reading Room) is the canonical, citable distribution. To reproduce:

1. Download UDS Health Center Program awardee (`H80`) and Look-Alike (`LAL`)
   files for years 2014–2024 from the HRSA Electronic Reading Room
   (https://www.hrsa.gov/foia/electronic-reading).
2. Place all 22 XLSX files in `data/uds/` with naming convention
   `h80-YYYY.xlsx` and `lal-YYYY.xlsx`.
3. The Sheps Center closure registry (`data/raw/sheps_closures.xlsx`) is
   committed for convenience. Original source:
   https://www.shepscenter.unc.edu/programs-projects/rural-health/rural-hospital-closures/

### Run the pipeline

```bash
# Install
pip install -r requirements.txt

# Or with conda
conda env create -f environment.yml && conda activate chc-rural

# Reproduce everything
make all
```

The `make all` target chains 9 numbered scripts. Each script is independent
and consumes parquet outputs from prior steps.

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `01_load_uds.py` | Parse UDS XLSX → tidy parquet (HealthCenterInfo, ZipCodes, Clinical) |
| 2 | `02_match_closures.py` | Match closures to CHC service-area ZIPs; build CHC×year panel |
| 3 | `03_event_study.py` | Initial 5-outcome Callaway–Sant'Anna + TWFE event studies |
| 4 | `04_figures.py` | Figure 1 (5-outcome event study) |
| 5 | `05_table1.py` | Baseline characteristics, simple-ATT summary |
| 6 | `06_more_outcomes.py` | Extract 6 additional clinical measures from Table 6B |
| 7 | `07_event_study_full.py` | 11-outcome Callaway–Sant'Anna event study |
| 8 | `08_figures_full.py` | Figure 2 (forest plot), Figure 3 (event panels) |
| 9 | `09_multiple_testing.py` | Bonferroni / Holm / BH / BY / Romano-Wolf adjustments |

## Data sources

| Source | Description | Access |
|--------|-------------|--------|
| HRSA UDS | Health Center Program annual reports, 2014–2024 | https://www.hrsa.gov/foia/electronic-reading |
| UNC Sheps Center | Rural Hospital Closures registry (1990–present) | https://www.shepscenter.unc.edu/programs-projects/rural-health/rural-hospital-closures/ |

## Methods (statistical)

- **Estimator:** Callaway and Sant'Anna (2021) ATT(g,t), implemented in the
  Python `differences` package
- **Comparison group:** Never-treated CHCs (no closure in any served ZIP, 2014–2024)
- **Multiple testing:** Bonferroni, Holm, Benjamini-Hochberg (BH),
  Benjamini-Yekutieli (BY), and Romano-Wolf stepdown — implemented in
  `09_multiple_testing.py` using `statsmodels.stats.multitest` plus a
  custom multivariate-normal calibration of Romano-Wolf joint distribution.
- **Robustness:** Specifications restricting to complete (non-converted)
  closures and to "not-yet-treated" comparison group yield qualitatively
  identical conclusions.

## Results summary

| Outcome | CS Simple ATT | 95% CI | Raw p | BH-FDR p | Romano-Wolf p |
|---------|--------------:|-------:|------:|---------:|--------------:|
| log(Total patients) | **+0.138** | +0.081, +0.195 | <.0001 | <.001 | <.0001 |
| Hypertension control (pp) | **+1.97** | +0.71, +3.24 | .002 | .012 | .022 |
| Childhood immunization (pp) | −3.17 | −5.95, −0.39 | .025 | .092 | .195 |
| Adult BMI follow-up (pp) | +2.65 | −0.10, +5.40 | .059 | .161 | .359 |
| Tobacco intervention (pp) | +1.37 | −0.82, +3.55 | .220 | .483 | .794 |
| Diabetes A1c>9% (pp) | +0.60 | −0.77, +1.96 | .392 | .615 | .927 |
| Colorectal cancer screening (pp) | +0.91 | −1.13, +2.95 | .381 | .615 | .927 |
| Depression screening (pp) | −1.09 | −4.05, +1.86 | .468 | .643 | .927 |
| Medicaid share (pp) | −0.31 | −1.27, +0.66 | .529 | .647 | .927 |
| Cervical cancer screening (pp) | −0.50 | −2.31, +1.31 | .588 | .647 | .927 |
| Uninsured share (pp) | +0.24 | −0.90, +1.38 | .676 | .676 | .927 |

n = 1,642 unique CHCs (386 exposed, 1,256 never-exposed); 116 rural hospital
closures 2014–2024.

## Citation

```bibtex
@article{basu2026chc,
  title={Rural Hospital Closures and Community Health Center Capacity:
         A Center-Level Event Study of Patient Volume, Payer Mix,
         and Quality, 2014--2024},
  author={Basu, Sanjay},
  journal={Journal of Health Care for the Poor and Underserved (in submission)},
  year={2026}
}
```

## License

MIT (see [LICENSE](LICENSE)).

## Contact

Sanjay Basu, MD, PhD — sanjay.basu@ucsf.edu
