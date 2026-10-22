# Frozen manuscript checkpoint before v176

## Files to use

Upload `DM_Overleaf_Compilation_20261022.zip` directly as a new Overleaf project. Select XeLaTeX and `main.tex`; select `supplementary.tex` to compile the supplement. See its README for the complete instructions.

`canonical_paper/` preserves every one of the 101 manuscript artefacts from source commit `c46f207dad827ad44d4af2aa8958b6dba81a76dd`, byte-for-byte: both reference PDFs, four main TeX files, 24 table fragments, eight figures in PDF/PNG/SVG, 38 numerical summary files and eight figure-data files (plus the existing figure licence notice).

The article is the exact 22-page PDF published as manuscript V1, DOI `10.5281/zenodo.23530614`. The supplement contains 11 pages. The separately frozen analysis/software archive is v1.0.0, DOI `10.5281/zenodo.23529740`; its tag remains at `11da155816d72342ce162ecdd7e07d9f492ce072`. The manuscript and software DOIs are not interchangeable.

`verification/` holds source hashes, public record snapshots and clean compilation checks. `reference/` holds licensing, citation and analysis-coverage documents. `tools/` preserves the package-construction code. `MANIFEST.json` hashes each checkpoint payload; use an externally supplied ZIP SHA256 to authenticate this whole file. Do not treat a newly rewritten manifest as proof of authenticity.

## Reproduction boundary

Both documents were compiled twice from a fresh extraction using the existing isolated Tectonic 0.17.0 installation. The results reproduce the reference PDFs byte-for-byte; all 33 rendered pages match. No actual hosted Overleaf session is claimed. The only Overleaf-source adaptation is the relative figure-directory path in two documents. The bibliography remains in references.tex, not an invented .bib conversion. No science, figure or table generation was rerun.

All manuscript-level artefacts are included. Large raw simulation inputs, every historical draft and the full numerical code/data archive are not duplicated into this document checkpoint; they remain in their separately preserved locations and the cited analysis DOI. The 32-asset reproduction map retains the exact numerical reproduction boundaries. No font files are distributed.

## Handoff to the main workflow

The manuscript checkpoint is fixed at the source and hashes above. The original scientific checkout remains at `06d5ed3437cf3e082b741c31a7a4c78962ff276c` with 18 one-use reservations preserved. This is a document-preparation milestone, not a scientific milestone and not execution of v176. Resume the main workflow only through its existing governing checks; do not treat paper publication as new data-admission or simulation authority.

ABA26-001 remains scientifically open: global joint-search permutations and fixed-parameter spatial references do not establish joint spatial/search calibration. ABA26-002 remains scientifically open: complete-case weighting does not identify the formation-incomplete population's conditional association. Their manuscript reporting is completed and preserved.

The published PDF affiliation and public record affiliation differ; this checkpoint records rather than silently reconciles them. Online description/keyword observations are metadata matters, not a reason to alter the frozen PDF. No new GitHub Release, Zenodo version or publication upload is part of this checkpoint.

Original scripts are MIT; other author-owned material is CC BY 4.0. Third-party provider rights remain separate.
