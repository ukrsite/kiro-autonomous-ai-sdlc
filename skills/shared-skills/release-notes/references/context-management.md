# Context Management by Dataset Size

| Size | Strategy |
|------|----------|
| <50 | Process all at once, full details in memory |
| 50–100 | 2–3 batches of 25–50, write after each batch |
| 100–500 | Batches of 25–50, aggregated summary, notable issues only |
| 500+ | Filter by status/priority; if all: batch 25, executive summary, group by category |
