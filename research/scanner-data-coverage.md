# Scanner Data Coverage Analysis

## Research Report — February 2026

## Summary

The memory files were written **independently from the scanner JSON data**. The result is major coverage gaps — the scanner has structural breadth the memory lacks, and the memory has narrative depth the scanner lacks. They are complementary, not redundant.

## Coverage Matrix

| Scanner Data Category | Total Items | In Memory | Coverage | Gap Severity |
|---|---|---|---|---|
| Capability names (unique) | 102 | 91 | 89% | LOW |
| Capability definitions with schemas | 175 entries | ~40 detailed | 23% | HIGH |
| Service graph edges | 231 | ~20 narrative | 9% | HIGH |
| DynamoDB tables | 24 | 17 | 71% | MEDIUM |
| SQL schemas | 57 | 0 | 0% | HIGH |
| SQS queues | 33 | ~11 | 33% | MEDIUM |
| S3/R2 buckets | 29 | ~10 | 34% | MEDIUM |
| Products | 15 | 0 | 0% | MEDIUM |
| Downstream consumers | 9 | 0 | 0% | MEDIUM |
| Per-repo infra (repos covered) | 32 repos | 8 repos | 25% | HIGH |
| HTTP routes | ~100 | ~5 | 5% | LOW-MEDIUM |
| Service env vars/URLs | ~200+ | 0 | 0% | MEDIUM |

## Top 3 Gaps

1. **Go service infrastructure entirely missing** — Piri (121 items), Guppy (19 items), Storoku (135 items), Indexing-service (8 items) = 283 items at 0% coverage
2. **Service connection map** — 231 edges at 9% coverage. No structured lookup for "what calls this service?"
3. **SQL schemas** — 57 tables at 0% coverage. Go services use SQLite/Postgres, completely invisible to knowledge base.

## Recommendation

- **MCP server (B2)** for structured queries — "what infra does Piri use?"
- **Memory backfill (A5)** for narrative context — "why does Piri use DynamoDB for metadata but SQLite for blob indexes?"
- **Three-tier architecture**: Markdown (concepts) + MCP (structured lookup) + Grep (actual code)

## Research Sources

- Scanner JSON structure analysis (direct inspection)
- Memory file cross-reference (all memory/**/*.md files)
- MCP best practices research (Nx, Sourcegraph, arXiv 2601.08773, Speakeasy, Anthropic)
- See also: `research/enforcement-mechanisms.md` for related findings
