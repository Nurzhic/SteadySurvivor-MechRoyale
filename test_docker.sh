#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
KIT="${1:-../mechfight-kit}"
if [ ! -f "$KIT/check/check.py" ] || [ ! -d "$KIT/arena" ]; then
  echo "Kit not found at: $KIT" >&2
  echo "Usage: bash test_docker.sh /path/to/mechfight-kit" >&2
  exit 1
fi
if ! command -v docker >/dev/null; then
  echo "Docker command not found. Install and start Docker Desktop." >&2
  exit 1
fi
MAPDIR="$(cd "$KIT/arena" && pwd)"
docker build --platform linux/amd64 -t steady-survivor:submission .
python3 "$KIT/check/check.py" --map-dir /arena -- \
  docker run --rm -i --platform linux/amd64 \
  --network none --cpus 1 --memory 512m --read-only \
  --tmpfs /tmp:rw,size=64m --user 65534:65534 \
  -v "$MAPDIR:/arena:ro" steady-survivor:submission
