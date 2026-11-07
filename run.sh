#!/usr/bin/env bash
# Contract: ./run.sh <SIM_URL> runs until the scenario finishes.
set -euo pipefail
SIM_URL="${1:?usage: ./run.sh <SIM_URL>}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec "${PYTHON:-python}" -m controller run --url "$SIM_URL"
