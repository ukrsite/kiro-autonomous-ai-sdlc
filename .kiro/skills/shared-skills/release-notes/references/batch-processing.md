# Batch Processing for Large Datasets

## Strategy by Size

| Size | Action |
|------|--------|
| <50 | Process all at once |
| 50–100 | 2–3 batches of 25–50, write after each |
| 100–500 | Batches of 25–50, aggregated summary, notable issues only |
| 500+ | Filter by status/priority; batch 25, executive summary |

## Steps

1. Calculate batches: `total_issues / batch_size` (e.g. 10–20 issues per batch)
2. For each batch: generate business_value yourself (inline); do NOT use subagents or delegate — no prompt-business-value agent exists
3. Show progress: "Processed batch N/M (X issues)"
4. Merge batches into release_notes_data.json, then write

## Large Dataset Output (100+ issues)

- Executive summary
- Key categories (group similar issues)
- Business value by category, not per-issue
- Top 10–20 notable issues
- Optional: detailed appendix
