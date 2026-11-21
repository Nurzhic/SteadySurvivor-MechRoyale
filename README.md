# SteadySurvivor v2 — Mech Royale

An autonomous `mechfight/1` bot for the [Builders Buildathon Mech Royale track](https://www.joinbuilders.org/buildathon/tracks/builders).

## Status

- **v1 practice score:** 2.27 across 48 matches (reported by the team, 2026-11-21).
- **v2 practice score:** not measured yet. The v2 changes are experimental; an increase is **not guaranteed**.
- **v2 technical conformance:** PASS on 300/300 observations using the organizer's official `check/check.py` with a mounted map, tested in a local Python environment. Test your own Docker image before submission.

## Changes in v2

- Reads the official campus `world.json` from `hello.map.dir` and builds an approximate ground-level grid of solid buildings.
- Time-sliced A* route finding: searches in small batches over multiple decisions to avoid exceeding the 50 ms tick budget.
- Keeps retreat destinations stable briefly to avoid oscillating paths.
- Scans the complete 360° over time when no enemy is visible; reacts to damage direction even if a foe is out of view.
- Uses actual organizer upgrade IDs to prioritize survivability (`nanites`, `armor`, `plating`, `servos`).
- Adjusted boost use and pickup vertical range checking.

### Limitations

The nav grid is an approximation: height, rooftops, bridges, terrain slopes, dynamic collisions and obscure routes are not fully simulated. The official kit does not include a full match simulator; `check.py` validates the protocol and timing, *not win rate*. Real placement improvements must be measured by new practice submissions.

## Local testing

Keep `mechfight-kit/` and this repository directory next to one another:

```bash
python3 smoke_test.py
bash test_official.sh
bash test_docker.sh
python3 test_strategy.py
```

`test_docker.sh` uses `--platform linux/amd64`, `--cpus 1`, `--memory 512m`, `--network none`, a read-only filesystem, an unprivileged user, and a read-only map mount. On Apple Silicon, Docker Desktop may emulate AMD64, which is why this check matters.

## Submitting

Push this repository to GitHub and submit the public repository URL on the Mech Royale page. Check the result before deciding whether to keep v2. The package is stdlib-only Python 3.13, single `example_bot.py` + a top-level `Dockerfile`. The project is MIT-licensed.
