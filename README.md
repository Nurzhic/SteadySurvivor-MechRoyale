# SteadySurvivor v5 — reactive damage response

A single-strategy experiment from **v1 (score 2.27)**. Does NOT inherit v2–v4 changes.

## What changed

When a `damaged` event supplies a real-world bearing, v5 remembers it for 2 seconds, sidesteps away while moving away from the source, boosts if energy permits, and faces the threat when no visible target is available. It postpones loot pursuit during this brief evasive period. High-priority evacuation from the shrinking zone is retained.

This may help against attacks from outside the field of view, but it **has not been proven to improve the 48-game match score**. The original v1 should remain available for rollback.

## Tests

`python3 test_strategy.py` — synthetic behavioral assertions, not simulated matches.

`bash test_official.sh ../mechfight-kit` — official protocol check. Run from this directory.

`bash test_docker.sh ../mechfight-kit` — local Docker platform check (requires Docker Desktop).

Buildathon submission uses this repository's root-level `Dockerfile` and `example_bot.py`.
