# SteadySurvivor v4 — dual-fire experiment

This candidate branches from the **v1 bot that scored 2.27**, not from v2 or v3.

## One combat change
When the bot selects a laser or lightning attack, it now ALSO fires the arm gun,
provided its own ballistic aim agrees with the selected torso aim, the target is in
gun range, the weapon is loaded and the torso is aligned. Laser charging/release is
unchanged; mortar trajectories never trigger secondary gun fire.

**Unchanged from v1:** movement, threat repulsion, looting decisions, upgrade
ranking, target selection, gun aiming, laser charging, boosting, obstacle recovery.

This is a controlled experiment. Passing check.py shows protocol conformance,
NOT improved game performance. Scored matches are needed to compare with v1.

## Test
Requires the official `mechfight-kit` extracted next to this folder.

```sh
python3 test_strategy.py
python3 smoke_test.py
bash test_official.sh
bash test_docker.sh
```

## Submission
Push the changed `example_bot.py` and `test_strategy.py` to the existing GitHub
repository, then re-submit. Keep a tag/commit for the v1 2.27 baseline and
compare results. The event ranks your best score, but the scorer rebuilds your
selected commit for finals. You need to retain the ability to restore your best.

Mechfight/1 protocol, 50 ms per action, arm64 Mac Docker tested by participant.
MIT license.
