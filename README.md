# SteadySurvivor v6 — Builders Mech Royale

Python / Docker bot for `mechfight/1`, using only the standard library.

This is an isolated **movement timing experiment based on v1**, the highest-scoring version so far (2.27 in 48 practice matches). v2-v5 had lower practice scores.

The bot now uses `zone.shrink_end`, estimated walking speed and distance to the next zone to delay moving to the next circle while there is ample time. It retains emergency movement when the current circle edge is too close or the robot is already outside. Weapon logic and threat avoidance match v1.

## Test

```sh
python3 test_strategy.py
bash test_official.sh /path/to/mechfight-kit
bash test_docker.sh /path/to/mechfight-kit
```

`check.py` validates the protocol only, *not* game strength. The Docker test is meant to be run on your Mac.

## Submit

Commit `example_bot.py`, `Dockerfile`, the license and supporting files to the repo root, push to GitHub, then submit the public GitHub URL.
