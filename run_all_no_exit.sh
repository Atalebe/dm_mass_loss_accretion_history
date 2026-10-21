#!/usr/bin/env bash
# Inspect the child receipt: this interactive wrapper preserves the calling shell on failure.
if (
    trap - ERR 2>/dev/null || true
    set +e; set +u; set +E; set +x
    set +o pipefail 2>/dev/null || true
    ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 2
    export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    cd "$ROOT" || exit 2
    mkdir -p outputs || exit 2
    "${PYTHON:-python3}" -B tools/reproduce_all.py --output "outputs/combined_$(date -u +%Y%m%dT%H%M%SZ)_$$" "$@" || exit 2
); then printf '%s\n' 'COMBINED_CHILD_STATUS=0; inspect COMPLETION.json.'
else printf '%s\n' 'COMBINED_CHILD_STATUS=2; HOLD: no success logbook or Git action.'; fi
printf '%s\n' 'CALLER_TERMINAL_PRESERVED=true'
