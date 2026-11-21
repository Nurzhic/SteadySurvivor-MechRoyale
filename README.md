# SteadySurvivor — Mech Royale bot

A survival-first autonomous bot for the Builders Buildathon **Mech Royale** track. It implements the `mechfight/1` newline-delimited JSON protocol in **Python 3.13 standard library only** (no pip dependencies).

## Features

- Rotates and aims toward enemies, lead-targets gun shots.
- Selects gun, laser, mortar, or lightning by range and circumstances.
- Flees nearby threats and incoming projectiles.
- Heads inside the current/next safe zone.
- Collects power cubes, weapons, and uncontested supply drops.
- Shoots crates and NPCs opportunistically.
- Chooses upgrades, reloads, uses boosts, and attempts to escape obstacles.
- Includes fast stdin/stdout transport to discard queued stale observations.

**Status:** local smoke-tested against synthetic messages only. Run the official kit's `check/check.py` and the Docker sandbox check before submitting; a passing local smoke test is NOT a passing official check or a competitive rating.

## Setup

1. Download the organizer's `mechfight-kit.tar.gz` from https://www.joinbuilders.org/buildathon/tracks/builders and extract it.
2. Keep `Dockerfile`, `example_bot.py`, and `README.md` at the **root** of your public GitHub repo.
3. For local conformance checks, copy the kit's `check/` and `arena/` directories alongside `example_bot.py`. Do NOT push these big directories to GitHub.
4. From the repository root, run:

```sh
python3 check/check.py -- python3 -u example_bot.py
docker build --platform linux/amd64 -t steady-survivor .
python3 check/check.py --map-dir /arena -- docker run --rm -i --platform linux/amd64 --network none --cpus 1 --memory 512m --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "$PWD/arena:/arena:ro" steady-survivor
```

For a newer version of the official kit, use its README commands if they differ.

5. If both checks pass, push the repository **publicly** to GitHub (under the 20 MB limit) and submit its URL on the track page. Do not submit the archive; submit the repository URL.

## Notes

- All strategy decisions use only observations (and no internet connection).
- `stdout` is strictly for protocol JSON; errors go to `stderr`.
- The image runs as uid 65534 (no root) and does not require filesystem writes.
- Strategy is intentionally modest and needs actual game testing to assess placement score.

## License

MIT
