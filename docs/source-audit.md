# Source and scoring audit

Audited on 28 September 2026 against the 2024–25 United Rugby Championship snapshot used by the local pipeline.

## Provenance and reuse

- Publisher: community-maintained [Rugby-Data repository](https://github.com/transientlunatic/Rugby-Data); this is not an official URC feed.
- File: [`json/celtic-2024-2025.json`](https://github.com/transientlunatic/Rugby-Data/blob/c2de981ddcbcf2362fdc5719eefa6d9172740850/json/celtic-2024-2025.json). The latest commit touching this file when checked was [`c2de981`](https://github.com/transientlunatic/Rugby-Data/commit/c2de981ddcbcf2362fdc5719eefa6d9172740850). The file at that commit and at `master` contained the same 151 JSON match records when checked.
- Observed local snapshot: 151 match records; SHA-256 of canonical JSON (sorted keys, compact separators, UTF-8) `47ce925d0db931ff366dde76299a71c4ce2a66030886b18488fc1243327c82eb`.
- Ingestion: `rugby-lakehouse sync` downloads the file from GitHub at `master`. `rugby-lakehouse sync --source-ref c2de981ddcbcf2362fdc5719eefa6d9172740850` fetches the fixed revision. `--input` accepts a local copy. The pipeline does not scrape the URC website.
- Reuse status: the upstream repository had no root licence file or README licence declaration, and GitHub reported no detected licence when checked. Public visibility does not establish permission to redistribute the dataset. This repository does not commit the upstream JSON or generated Bronze/Silver data. Confirm reuse terms with the maintainer or use a clearly licensed source before redistributing raw records or derived datasets.

The fingerprint can be reproduced from the pinned upstream revision with:

```python
import hashlib
from rugby_lakehouse.source import read_matches
from rugby_lakehouse.transform import canonical_json

matches = read_matches(source_ref="c2de981ddcbcf2362fdc5719eefa6d9172740850")
canonical = canonical_json(matches)
print(hashlib.sha256(canonical.encode("utf-8")).hexdigest())
```

## Scoring investigation

The original quality check summed each source scoring event's `value` and found 16 fixtures where one team's event total was two points below its final score. Every affected team had exactly one `Penalty Try` event with `value: 5`; no other team had a mismatch. [World Rugby Law 8](https://passport.world.rugby/laws-of-the-game/laws-by-number/8-scoring) awards seven points for a penalty try, with no conversion attempt. The local Silver transform now records seven points for that event, while Bronze retains the unchanged source record.

| Date | Affected team | Source event gap | Penalty tries |
| --- | --- | ---: | ---: |
| 2024-09-28 | Ospreys | 2 | 1 |
| 2024-10-05 | Leinster Rugby | 2 | 1 |
| 2024-10-12 | Cardiff Rugby | 2 | 1 |
| 2024-10-18 | Ulster Rugby | 2 | 1 |
| 2024-10-26 | Leinster Rugby | 2 | 1 |
| 2024-11-30 | DHL Stormers | 2 | 1 |
| 2024-12-21 | Hollywoodbets Sharks | 2 | 1 |
| 2024-12-28 | Glasgow Warriors | 2 | 1 |
| 2025-01-25 | Munster Rugby | 2 | 1 |
| 2025-03-22 | Vodacom Bulls | 2 | 1 |
| 2025-03-29 | Scarlets | 2 | 1 |
| 2025-03-29 | Benetton Rugby | 2 | 1 |
| 2025-04-19 | Cardiff Rugby | 2 | 1 |
| 2025-04-19 | Leinster Rugby | 2 | 1 |
| 2025-04-25 | Cardiff Rugby | 2 | 1 |
| 2025-05-16 | Ulster Rugby | 2 | 1 |

After applying transform version 2 to the same 151-match snapshot, the local quality report returned `fixtures_with_score_event_discrepancy: 0`. A second run changed zero matches. This reconciles listed scoring events with final scores in this snapshot; it does not independently verify every match or player detail against an official record.
