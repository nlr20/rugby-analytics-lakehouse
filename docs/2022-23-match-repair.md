# Glasgow Warriors 35–21 Vodacom Bulls match repair

The 8 October 2022 fixture in the [community 2022–23 JSON](https://github.com/transientlunatic/Rugby-Data/blob/master/json/celtic-2022-2023.json) has the final score but empty lineups and scoring-event lists for both teams. This caused the one 56-point event/final-score gap in the initial five-season load. The user's [all.rugby match page](https://all.rugby/match/18126/urc-2022-2023/glasgow-bulls) screenshot independently showed the five Glasgow tries and five conversions, three Bulls tries and three conversions, and yellow cards for George Horne and Elrigh Louw.

The [same InCrowd Sports match feed](https://github.com/transientlunatic/Rugby-Data/blob/master/AUTOMATION.md) used by the community project has match ID `271799` for this fixture. Its detailed response includes 23 players on each side, substitutions, card events, and all 16 scoring events. The score events total Glasgow 35 and Bulls 21. We use the feed's event timestamps for a reproducible repair. They differ from the screenshot in a few places: George Horne's last conversion is 48′ in the feed versus 47′ on all.rugby; Janko Swanepoel's try is 79′ versus 75′; Morné Steyn's conversion is 80′ versus 76′; and the two yellow cards are 55′ versus 54′. The player attribution and match score agree. The analytics' match-period buckets are unchanged by these differences.

Run from the repository root:

```powershell
$env:PYTHONPATH='src'
python -m rugby_lakehouse.match_repair --season 2022-23 --api-match-id 271799 --input data/source/celtic-2022-2023.json --output data/source/celtic-2022-2023-repaired.json
python -m rugby_lakehouse.cli prepare-landing --season 2022-23 --input data/source/celtic-2022-2023-repaired.json
```

The original source file is preserved. The repair changes only source index 29 of 151, leaves its normalized fixture key unchanged, and produces 23 lineup records per team and 16 scoring events. Every 2022–23 fixture then has event points equal to its final score. The corrected source SHA-256 is `2b30a82d61506061c5a15368f943003ef114b11f8b282250273f73b5c0a484b9`. The new ignored landing file is `data/landing/urc-2022-23-v3-89dbeb30c26e.jsonl`.

On 1 October 2026, the new landing file was uploaded to `/Volumes/workspace/rugby_analytics/landing/urc-2022-23-v3-89dbeb30c26e.jsonl` and processed by the folder ingestion notebook as the latest 2022–23 snapshot. The notebook reported 755 current completed matches and zero score discrepancies. The subsequent dbt build completed nine models and 46 tests successfully. A refreshed local website export reports 11,951 scoring events and an event/final-score gap of zero across all five seasons. This repair is technical evidence, not a determination of redistribution rights; generated data remains Git-ignored.
