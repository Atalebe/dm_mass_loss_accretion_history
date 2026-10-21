# Mass-loss dependence of accretion-history correlations

Paper-specific analysis materials for **Mass-loss dependence of accretion-history correlations in dark-matter halo velocity structure**, by Stephen Atalebe.

This is a standalone repository with a new Git history. It is not a mirror of the ongoing simulation-development repository and does not contain that repository's history, environment, service credentials, job reservations, or unrelated work.

## Status

This first snapshot is a **release-preparation candidate**, not a published archival release. The repository remains private until the owner approves public visibility and licensing. There is no analysis DOI yet. The manuscript is the checked v12 rendering; its scientific content is unchanged. See `docs/release_status.json`, `docs/reproduction_scope.md` and the complete `docs/reproducibility_map.md` for the precise coverage and remaining work. The branch-specific audit follow-up records completed reporting actions without closing the two scientific limitations. Earlier resampling and spline materials have been recovered and verified in a separate companion, whose import is still pending.

## Start here

- `paper/Mass_Loss_Accretion_History.pdf`: article.
- `paper/Supplementary_Material.pdf`: supplementary material.
- `paper/manuscript/`: editable LaTeX and tables.
- `paper/data/`: full-precision reported summaries.
- `analysis_data/`: per-object catalogue and matrix inputs, all 30 loss-design search outputs, and spatial coordinates and deletion records.
- `src/`: numerical routines, isolated from acquisition and development machinery.
- `tools/reproduce.py`: portable numerical reproduction from included inputs.
- `tests/`: deterministic numerical and failure-path tests.

## Reproduce without accessing the development repository

Use a separate Python environment. The versions in `requirements.txt` are those measured for the checked research-PC runtime (Python 3.13.9). Installing them in a new environment is an explicit user operation; none of the scripts installs packages automatically.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
bash run_reproduce_no_exit.sh
```

The combined launcher verifies the package hashes, runs deterministic tests, refits the included observed models, reconstructs the spatial and mass-bin sensitivities, and checks the saved search distributions. It uses a new timestamped directory under `outputs/`. Successful completion is stated in `COMPLETION.json`; a failed child produces a diagnostic receipt and no completion entry. The outer launcher intentionally keeps the calling shell open: **its zero shell return must not be mistaken for numerical success**.

For automation, use the direct command and its nonzero-on-failure exit status:

```bash
python -B tools/verify_integrity.py
python -B tools/reproduce.py --output /absolute/path/to/a/new/reproduction
```

The default run checks every saved-null minimum and exceedance count and directly recalculates three selected permutations per design. To recalculate all 30,000 saved permutations (780,000 candidate statistics), retaining their original PCG64 streams:

```bash
bash run_reproduce_no_exit.sh --full-nulls
```

This is replay of the original samples and streams, not a new confirmation, fresh simulation, or new permutation budget. Platform and numerical-library differences are reported and comparisons use fixed numerical tolerances; raw PDF or floating-point byte identity across different platforms is not promised.

## Build the paper

An installed Tectonic or XeLaTeX compiler is needed only for document compilation:

```bash
bash build_paper_no_exit.sh
```

Set `TEX_COMPILER` to an executable path when it is not on PATH. The build takes place in a new directory, disables shell escape, and leaves the included PDFs and scientific inputs unchanged. TeX support-file downloads by Tectonic may require network access; numerical reproduction is offline.

## Scientific scope

The results concern contemporaneous, population-dependent accretion-history correlations. Continuous and flexible recorded-loss controls substantially attenuate the original increments. Global residual-permutation probabilities require unverified exchangeability; nominal spatial Student-t references are fixed-parameter and pointwise. Within-box regional agreement is not independent cosmological replication. No dynamical-memory law or predictive closure is established here.

## Data, attribution and licence

The upstream TNG and BolshoiP products retain their providers' terms and acknowledgement requirements. Raw multi-gigabyte BolshoiP trees and TNG HDF5 products are not included. This candidate contains selected derived inputs and preserved numerical results; public redistribution review and an owner-selected licence remain required. No open-source or Creative Commons licence is assigned by this preparation. See `docs/RIGHTS_AND_RELEASE.md`.

AI assistance is disclosed in the manuscript. Additional numerical reproduction does not represent independent human peer review.
