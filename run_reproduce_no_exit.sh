#!/usr/bin/env bash
# The direct Python commands carry failure status; this interactive wrapper preserves the caller.
if (
    trap - ERR 2>/dev/null || true
    set +e; set +u; set +E; set +x
    set +o pipefail 2>/dev/null || true
    R="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 2
    export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    PY="${PYTHON:-python3}"
    cd "$R" || exit 2
    "$PY" -B tools/verify_integrity.py || exit 2
    "$PY" -B tools/verify_release_coverage.py || exit 2
    "$PY" -B -m unittest discover -s tests -v || exit 2
    mkdir -p outputs || exit 2
    OUT="outputs/reproduction_$(date -u +%Y%m%dT%H%M%SZ)_$$"
    "$PY" -B tools/reproduce.py --output "$OUT" "$@" || exit 2
); then
    printf '%s\n' 'REPRODUCTION_CHILD_STATUS=0; inspect COMPLETION.json for scope.'
else
    printf '%s\n' 'REPRODUCTION_CHILD_STATUS=2; HOLD: no success logbook or Git action.'
fi
printf '%s\n' 'CALLER_TERMINAL_PRESERVED=true'
