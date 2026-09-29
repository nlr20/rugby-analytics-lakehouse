# Five-season source audit

Source: [transientlunatic/Rugby-Data `json` directory](https://github.com/transientlunatic/Rugby-Data/tree/master/json). Files were fetched from the repository's `master` branch on 28 September 2026. The source files stay under ignored `data/source/`; the repository contains code and this audit, not copies of upstream data. SHA-256 below is for each downloaded raw file. The landing name uses a separate canonical JSON snapshot hash and transform version 3.

| Season | Source file | Raw SHA-256 | Fixtures | Results | Result unavailable | Landing file |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2021–22 | `celtic-2021-2022.json` | `9d3c884384dc96f288a74f91b644ca3aaa147b798b792cbd6a2e743f2200f534` | 151 | 151 | 0 | `urc-2021-22-v3-55a0432d9866.jsonl` |
| 2022–23 | `celtic-2022-2023.json` | `95e0e227b1f7f2de52b1828fad4bd21f3d7e22b51dab3ea19836b0bea32f9487` | 151 | 151 | 0 | `urc-2022-23-v3-91d91714ea59.jsonl` |
| 2023–24 | `celtic-2023-2024.json` | `b47da5b72329c381b720d97e9f056c9ea0ff64fb52511e5680648215c142b6d2` | 151 | 151 | 0 | `urc-2023-24-v3-a5b542793691.jsonl` |
| 2024–25 | `celtic-2024-2025.json` | `146ccbb17e009e403c3fdba9d544ffa69d312bac9be3c2672760b577732b04a4` | 151 | 151 | 0 | `urc-2024-25-v3-47ce925d0db9.jsonl` |
| 2025–26 | `celtic-2025-2026.json` | `566cdb7862935a98271671f9773be5860f3a5b866b28293a10f6f6fc1b504a50` | 151 | 84 | 67 | `urc-2025-26-v3-5792a28de763.jsonl` |

**Observed local run:** 755 fixture rows, 688 completed matches, 67 without source results, 31,602 player appearances, and 10,870 listed scoring events. Re-reading each of the five identical source files added zero match versions. On 29 September 2026 the Databricks folder ingestion reported the same 755/688/67 counts and one score-event discrepancy. The dbt Gold build passed all 31 tests; its tables contained 755 fixtures, 688 match facts and 1,376 team appearances.

## Known source limits

- The 2025–26 file has results through 31 January 2026. Its 67 null-score fixture dates run from 21 February through 20 June 2026. As of this audit date they are past dates, so `result_unavailable` is an honest source status; it does not mean the matches are still upcoming. Seven of these rows use `TBC` team placeholders.
- The 2023–24 source uses both `Emirates Lions` and `Lions`. Silver maps the former to `Lions` so trends use one club. Bronze preserves the original spelling.
- The 2022–23 Glasgow Warriors 35–21 Vodacom Bulls fixture dated 8 October 2022 has no listed scoring events for either side. Final-score team metrics use the published score; player-event metrics cannot recover the missing detail. The quality check reports one discrepancy. Other scored matches reconcile after penalty tries are valued at seven points, including their automatic conversion.
- There is no upstream fixture ID. Named fixtures are keyed by season, phase, round and teams. A correction to those identity fields appears as a replacement fixture in the current season snapshot; Bronze retains the earlier raw record. `TBC` rows are keyed by source position and replaced when named teams arrive.
- Lineups and scoring events support appearances, tries and recorded points. They do not measure all player performance. Team wins include playoff fixtures and are not official league standings with bonus points.

The source's `master` branch can change. Run `rugby-lakehouse prepare-landing --all-seasons` again before a backfill and compare the printed snapshot hashes with this table. A different filename means the upstream snapshot changed and should be audited before publication.
