# Integration instructions

This archive is an additive extension for Atalebe/dm_mass_loss_accretion_history. It is not a standalone full manuscript repository and is not an executable installer.

Before copying, verify the external archive SHA256 and every member in provenance/legacy_payload_manifest.json, reject absolute/parent-traversal/symlink members, and require the destination checkout to be clean at its verified paper-only remote. No existing file may be overwritten. Extract into a new staging directory first.

After explicit inspection and additive copying, update the root MANIFEST.json, source-map coverage statuses and documentation. Run the combined integrity/unit/replay gates in a clean copy. Record a release-logbook entry only after they pass, then commit and verify the push to this paper repository only. Preserve a local commit on push failure; do not rerun science to repair synchronization.

Neither extraction nor the presence of these files establishes public readiness. Licensing, redistribution, public visibility and an archival DOI remain separate owner-controlled actions.
