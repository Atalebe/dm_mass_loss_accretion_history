#!/usr/bin/env bash
if (
    trap - ERR 2>/dev/null || true
    set +e; set +u; set +E; set +x
    set +o pipefail 2>/dev/null || true
    ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 2
    export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    cd "$ROOT" || exit 2
    PY="${PYTHON:-python3}"
    "$PY" -B tools/verify_legacy_materials.py || exit 2
    "$PY" -B -m unittest discover -s tests -p test_legacy_materials.py -v || exit 2
    mkdir -p outputs || exit 2
    "$PY" -B tools/replay_legacy.py --output "outputs/legacy_$(date -u +%Y%m%dT%H%M%SZ)_$$" "$@" || exit 2
); then printf '%s\n' 'LEGACY_CHILD_STATUS=0; inspect COMPLETION.json for scope.'
else printf '%s\n' 'LEGACY_CHILD_STATUS=2; HOLD: no success entry or commit.'; fi
printf '%s\n' 'CALLER_TERMINAL_PRESERVED=true'
