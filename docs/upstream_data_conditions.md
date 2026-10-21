# Upstream data and distribution scope

Checked 21 October 2026 for this paper-specific archive. This is a documented source and distribution review, not a legal opinion or a new grant of rights over provider material.

## IllustrisTNG

The project identifies TNG100 and its dark-matter-only counterpart, halo catalogues and merger trees as publicly released. Its data service requires an account for upstream access. The public documentation requests Nelson et al. (2019) and the five TNG100/300 introductory papers; the manuscript includes them. The checked pages do not assign an SPDX licence to the underlying simulation data, so none is invented here. The repository distributes selected numerical inputs and analysis-derived products, not raw TNG HDF5 snapshots or a mirror of the simulation archive. Provider attribution and conditions remain separate from the author's MIT/CC BY grants.

Sources:
- https://www.tng-project.org/data/
- https://www.tng-project.org/data/docs/background/#sec4
- https://arxiv.org/abs/1812.05609

## BolshoiP and CosmoSim

The official CosmoSim BolshoiP metadata page labels its dataset CC0 1.0 and identifies schema DOI 10.17876/cosmosim/bolshoip. It also supplies the data/project and computing acknowledgements and citation requests. These are retained in the manuscript. That statement is attributed to the named CosmoSim dataset, not automatically to every independently hosted raw-tree copy. The repository includes selected tree-derived quantities and author-generated analyses; it does not redistribute the multi-gigabyte Consistent Trees files. Klypin et al., Rodriguez-Puebla et al. and the halo/tree-method references remain in the article.

Source: https://www.cosmosim.org/metadata/bolshoip/

## What is and is not licensed by the author

Original software is MIT. Other author-owned selection, arrangement, annotations, manuscript and analytical products are CC BY 4.0 to the extent such rights exist. Factual values and public-domain elements are not made proprietary by inclusion here. Third-party terms remain in force. Neither the release nor its DOI certifies ownership of underlying simulation products or supplies permission missing from a provider contract.

No API key, account credential, service reservation, private-development Git history, raw HDF5 snapshot, upstream raw-tree file, or installed third-party package is included. Test fixtures embedded in software are covered as original code; simulation-derived catalogues are not called synthetic fixtures. The public reproduction map separates supplied arrays from upstream reconstruction.
