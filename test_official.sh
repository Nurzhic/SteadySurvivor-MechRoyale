#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
KIT="${1:-../mechfight-kit}"
if [ ! -f "$KIT/check/check.py" ]; then
  echo "Kit not found at: $KIT" >&2
  echo "Usage: bash test_official.sh /path/to/mechfight-kit" >&2
  exit 1
fi
python3 "$KIT/check/check.py" -- python3 -u example_bot.py
