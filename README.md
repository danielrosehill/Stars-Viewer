# Star-Export-0426

Snapshot of Daniel Rosehill's GitHub stars on 2026-04-20, with a local semantic search index built on DuckDB + VSS.

## Contents

- `stars.jsonl` — 4,949 starred repos (full metadata incl. stargazer counts at fetch time)
- `build_index.py` — embed descriptions (MiniLM-L6-v2) and write `stars.duckdb` with an HNSW index
- `search.py` — natural-language search CLI
- `stars.duckdb` — generated; not committed if large (see `.gitignore`)

## Usage

```bash
pip install -r requirements.txt
python build_index.py          # one-off, ~1 min on CPU
python search.py "mcp servers for home automation" --k 10
python search.py "static site generators" --lang Go
```

## Direct SQL

```bash
duckdb stars.duckdb
```

```sql
LOAD vss;
-- filter by topic + semantic
SELECT full_name, stargazers
FROM stars
WHERE list_contains(topics, 'llm')
ORDER BY stargazers DESC
LIMIT 20;
```
