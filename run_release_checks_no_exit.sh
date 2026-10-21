#!/usr/bin/env bash
# No tag, commit or network mutation; those are separate explicitly authorized actions.
if (
    trap - ERR 2>/dev/null || true
    set +e; set +u; set +E; set +x
    set +o pipefail 2>/dev/null || true
    R="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 2
    export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    cd "$R" || exit 2
    PY="${PYTHON:-python3}"
    "$PY" -B tools/verify_archival_release.py || exit 2
    "$PY" -B -m unittest discover -s tests -v || exit 2
); then printf '%s\n' 'RELEASE_CHECK_CHILD_STATUS=0'
else printf '%s\n' 'RELEASE_CHECK_CHILD_STATUS=2; HOLD_NO_PUBLICATION'; fi
printf '%s\n' 'CALLER_TERMINAL_PRESERVED=true'
