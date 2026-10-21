#!/usr/bin/env bash
# Metadata/unit checks only; no scientific fit, permutation, commit or release.
if (
    trap - ERR 2>/dev/null || true
    set +e; set +u; set +E; set +x
    set +o pipefail 2>/dev/null || true
    R="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 2
    export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    cd "$R" || exit 2
    PY="${PYTHON:-python3}"
    "$PY" -B tools/verify_integrity.py || exit 2
    "$PY" -B tools/verify_legacy_import.py || exit 2
    "$PY" -B tools/verify_release_coverage.py || exit 2
    "$PY" -B tools/verify_licensing.py || exit 2
    "$PY" -B -m unittest discover -s tests -v || exit 2
); then printf '%s\n' 'LICENSING_CHILD_STATUS=0'
else printf '%s\n' 'LICENSING_CHILD_STATUS=2; HOLD: no success logbook or commit.'; fi
printf '%s\n' 'CALLER_TERMINAL_PRESERVED=true'
