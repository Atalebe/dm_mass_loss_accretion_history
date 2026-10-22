# Mass-loss dependence of accretion-history correlations

Paper-specific analysis materials for **Mass-loss dependence of accretion-history correlations in dark-matter halo velocity structure**, by Stephen Atalebe.

This is a standalone repository with a new Git history. It is not a mirror of the ongoing simulation-development repository and does not contain that repository's history, environment, service credentials, job reservations, or unrelated work.

## Status

**Version 1.0.0 is publicly archived on Zenodo:** [10.5281/zenodo.23529740](https://doi.org/10.5281/zenodo.23529740). Cite that version-specific DOI for the exact analysis snapshot. The [all-versions DOI](https://doi.org/10.5281/zenodo.23529739) resolves to the version collection.

The immutable `v1.0.0` tag points to commit `11da155816d72342ce162ecdd7e07d9f492ce072`. All 793 archived files were downloaded and verified. The current main-branch article includes DOI-only Data Availability and manuscript-header amendments made after the deposit; the archived tag and numerical results are unchanged. The supplement is byte-identical. See `provenance/zenodo_release_receipt.json` and `provenance/availability_update_verification.json`.

The current article also carries the author-reserved **manuscript DOI `10.5281/zenodo.23530614`** on its first page and in its PDF metadata. This is separate from the analysis DOI above. The manuscript upload is in preparation; reservation is not verification of publication. Only bibliographic text is added, all scientific prose and other pages are unchanged, and the supplement is unchanged. See `provenance/manuscript_doi_update_verification.json`.

Original software and executable workflows are MIT; other author-owned material is CC BY 4.0. The generic Other (Open) catalogue entry on Zenodo represents this mixed collection; the description and `LICENSE.md` specify each material's grant. Third-party conditions remain separate. Reproduction boundaries are in `docs/reproduction_scope.md` and the 32-asset map. The two scientific inference/population findings remain open.

## Frozen manuscript / Overleaf checkpoint

The manuscript is published as V1 at DOI **10.5281/zenodo.23530614**, separate from the analysis DOI above. The exact 22-page PDF was downloaded from the published record and verified.

`checkpoints/manuscript_pre_v176_20261022/` contains a compact Overleaf project ZIP and a full document-preservation ZIP. The latter includes all 101 paper artefacts, published/reference PDFs, summary and figure data, licensing and source/build checks. The source identity is `c46f207dad827ad44d4af2aa8958b6dba81a76dd`. Select XeLaTeX and `main.tex` or `supplementary.tex`; no simulation runtime or private files are needed. Both documents rebuild byte-identically under the checked isolated Tectonic engine. Actual hosted Overleaf execution is not claimed.

The bundles are committed for preservation; the Actions artifact is only a convenient transfer copy, not the sole archive. No v176 execution or new public release is performed by this checkpoint.

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
bash run_all_no_exit.sh
```

The combined launcher verifies package and companion hashes, audit/coverage metadata and deterministic tests, then runs both the main loss-design/spatial pipeline and the recovered earlier-analysis pipeline. It uses a new timestamped directory under `outputs/`. Successful completion is stated in `COMPLETION.json`; a failed child produces a diagnostic receipt and no completion entry. The outer launcher intentionally keeps the calling shell open: **its zero shell return must not be mistaken for numerical success**.

For automation, use the direct command and its nonzero-on-failure exit status:

```bash
python -B tools/verify_integrity.py
python -B tools/reproduce_all.py --output /absolute/path/to/a/new/reproduction
```

The default run checks the saved summaries and recalculates three selected draws per original stream. The full replay evaluates the 30,000 main loss-design permutations, 18,000 recovered formation/threshold permutations and 360,000 saved minima in the separate 10,000-draw cross-checks:

```bash
bash run_all_no_exit.sh --full-nulls
```

The main 48,000 draws retain all 26 candidate values (1,248,000 in total). The second implementation saved a joint minimum per draw, not every candidate-wise null value. Its 10,000-draw experiments are not pooled with the 1,000-draw experiments into a new probability.

The narrower `run_reproduce_no_exit.sh` and `run_legacy_no_exit.sh` remain available. The companion's original replay environment is in `requirements-legacy-replay.txt`; replay was also checked under the research-PC versions in `requirements.txt`, without installing or changing scientific packages.

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

**Original code and executable scripts: MIT. Everything else the author owns: CC BY 4.0.** The latter includes the manuscript and supplementary text, documentation, figures, tables, metadata, synthetic reference datasets and original analytical outputs. See `LICENSE.md` for attribution and the default non-code rule, and `docs/licensing.json` for the machine-readable scope.

Upstream TNG/BolshoiP products and other third-party material retain their existing rights, conditions and notices. The CC BY grant applies only to rights the author holds in original non-code contributions; it does not relicense provider-owned content. The licensing choice does not itself complete the separate redistribution review or create a DOI. See `docs/RIGHTS_AND_RELEASE.md`.

AI assistance is disclosed in the manuscript. Additional numerical reproduction does not represent independent human peer review.
