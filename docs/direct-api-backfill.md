# Completing the 2025–26 source snapshot

The community [2025–26 JSON](https://github.com/transientlunatic/Rugby-Data/blob/master/json/celtic-2025-2026.json) stopped changing on 3 February 2026. It contains 151 fixtures but only 84 results, ending 31 January 2026. Its other 67 fixtures have null scores, even though the season is complete.

The community project's [automation notes](https://github.com/transientlunatic/Rugby-Data/blob/master/AUTOMATION.md) identify the InCrowd Sports rugby feed (URC competition `1068`, provider `rugbyviz`). On 1 October 2026, a direct read of that feed returned 151 result-status fixtures for season `202501`. The extractor in this repository reads the season index and each match's detail response, then writes a local JSON file in the source format already accepted by our pipeline. The extractor is our own code; it does not copy the community project's implementation.

## Reproduce locally

From the repository root:

```powershell
$env:PYTHONPATH='src'
python -m rugby_lakehouse.incrowd_source --season 2025-26
python -m rugby_lakehouse.cli prepare-landing --season 2025-26 --input data/source/celtic-2025-2026-api.json
python -m rugby_lakehouse.cli sync --season 2025-26 --input data/source/celtic-2025-2026-api.json
```

The first command caches individual match-detail responses under ignored `data/api-cache/2025-26/` so an interrupted fetch can resume. Use `--refresh-cache` when checking for later source corrections. The output JSON, cache, and generated landing JSONL all remain under Git-ignored `data/`.

## Observed reconciliation

The 1 October 2026 extraction produced `data/source/celtic-2025-2026-api.json`, SHA-256 `5e4c3d1094a02aa41b015ef0b18a433cfb338307a3cd25b16248c9eee6777d68`:

| Check | Result |
| --- | ---: |
| Unique API match IDs and normalized fixture keys | 151 each |
| Completed results / missing scores | 151 / 0 |
| Teams after canonicalising sponsor names | 16 |
| Player appearances | 6,946 |
| Listed scoring events | 2,318 |
| Matches whose listed scoring points differ from the final score | 0 |
| Previously scored fixtures matched to the old snapshot | 84 / 84 |
| Score changes among those 84 fixtures | 0 |
| Second local sync, changed match versions | 0 |

The normalized landing file is `data/landing/urc-2025-26-v3-99bac3bd84e1.jsonl`. On 1 October 2026 it was uploaded to the Databricks landing Volume. The folder ingestion reported 755 current fixtures, 755 completed matches, no unavailable results, and the one already documented 2022–23 score-event discrepancy. The subsequent dbt build passed all nine models and 46 tests. The local site JSON export was refreshed: its manifest reports 755 completed matches and zero unavailable results.

The feed uses both `Lions` and `Fidelity SecureDrive Lions` in this season. The local transform maps the sponsor name to the canonical `Lions`, preserving cross-season team identity. Bronze keeps the original feed name.

## Data use

This verifies technical completeness, not public redistribution rights. Keep the extracted data and derived site files private until the data provider's reuse terms are confirmed or a licensed source is used. Attribute the feed accurately in project documentation; do not call the community JSON the source of the new result records.
