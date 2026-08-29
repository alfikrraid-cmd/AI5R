# Known Risks

Standing risks worth a new investigation remembering before it starts.
Not a bug tracker — remove/update an entry once it's no longer true.

<!-- Format:
## <short title>
Risk: ...
Where it bites: ...
Noted: YYYY-MM-DD
-->

## Documentation can describe orphaned/unwired features
Risk: This repo's code comments and MWO reports are unusually detailed and
can describe a component or field as "already computed"/"already live"
when it was later orphaned by a redesign or was always a null placeholder.
Where it bites: Any "X not appearing" task — always verify actual
render/wiring (see `ai5r-observability`), never trust the comment alone.
Noted: 2026-08-29

## Production checkout can diverge from origin
Risk: The production VPS working tree has held uncommitted files and its
local HEAD has been observed to differ from `origin/release/ltsa-v1-rc1`.
Where it bites: Don't assume the deployed commit matches the latest branch
tip in GitHub, or vice versa — verify both independently before reasoning
about "what's live."
Noted: 2026-08-29
