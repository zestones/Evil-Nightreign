# Ground truth — in-game measurements bank

Every calibration constant in the engine is anchored to REAL in-game measurements stored here. Anchor tests (`tests/`) read these files and fail loudly if a formula drifts. This bank is versioned: it is OUR data (player measurements), never game assets.

## Format

One JSON file per measured mechanic:

```json
{
  "mechanic": "attack_rating",
  "notes": "how/where it was measured",
  "measured_on": "YYYY-MM-DD",
  "regulation_md5": "<md5 of inputs/regulation.bin at measurement time>",
  "measurements": [ { ...mechanic-specific fields..., "value": <number> } ]
}
```

`regulation_md5` ties a measurement to a game patch. If the game updates and the md5 changes, re-validate the affected measurements before trusting them.

## Files

- `attack_rating.json` — in-game AR readings (Duchess weapons, levels 1-15). Anchors `AR_FACTOR = 0.596` (`tests/test_attack_rating.py`).

## Adding measurements

Follow the calibration checklist (docs/, phase E of ROADMAP.md). Each new constant (e.g. `SPELL_FACTOR`) must land here with its protocol notes before the engine treats it as calibrated.
