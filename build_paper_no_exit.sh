#!/usr/bin/env bash
if (
    trap - ERR 2>/dev/null || true
    set +e; set +u; set +E; set +x
    set +o pipefail 2>/dev/null || true
    R="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 2
    export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
    cd "$R" || exit 2
    "${PYTHON:-python3}" -B tools/build_paper.py || exit 2
); then printf '%s\n' 'BUILD_CHILD_STATUS=0'; else printf '%s\n' 'BUILD_CHILD_STATUS=2; HOLD'; fi
printf '%s\n' 'CALLER_TERMINAL_PRESERVED=true'
