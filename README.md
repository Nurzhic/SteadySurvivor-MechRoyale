# SteadySurvivor v3 — survival-first Mech Royale bot

Experimental third submission for Builders Buildathon / Mech Royale (`mechfight/1`). Python 3.13, standard library only. It is intentionally based on **v1 (practice score 2.27)** rather than v2 (score 2.00). The official conformance checker does **not** simulate matches and cannot validate gameplay strength.

## Changes versus v1

- Retains v1's lightweight, direct navigation and earlier zone boost logic; removes v2's expensive map pathfinder and automatic zone-edge patrol.
- Chooses official upgrade IDs exactly, prioritizing movement speed, efficient boost, and immediate durability.
- Evades the source of recent unseen enemy damage using the `damaged.bearing` event.
- Scans 360 degrees while idle and reacts to nearby weapon sounds.
- Avoids starting an immobilizing laser charge while fleeing multiple attackers at low health.
- Checks vertical distance before taking a weapon from another floor.

**No claim of a higher score until a new 48-match submission.** Practice seeds are fixed, making it useful to compare new versions with the earlier two results.

## Run locally (place the kit alongside this directory)

```bash
python3 smoke_test.py
python3 test_strategy.py
bash test_official.sh
bash test_docker.sh
```

After passing all tests, replace the bot file in your existing public GitHub repository, commit/push, and submit again. Keep the old tagged versions; the organizers retain the best practice score and let you choose a different submission at cutoff. Do not push the kit's `arena/` data into your repo. Dockerfile at repository root is required.

MIT license.
