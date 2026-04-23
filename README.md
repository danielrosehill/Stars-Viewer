# Stars-Viewer

Self-updating categorised browser for Daniel Rosehill's GitHub stars.
Nightly: pull new stars → diff against `stars.jsonl` → rebuild the static
site in `docs/`. GitHub Pages serves from `docs/`.

## Pipeline

| Script | Purpose |
| --- | --- |
| `sync_stars.py` | Incremental pull of `/user/starred`. Short-circuits when a page contains nothing new. `--full` reconciles unstars + metadata drift. |
| `fetch_updated.py` | GraphQL batch fetch of `pushedAt` for repos missing from `updated_at.json`. Resumable. |
| `build_site.py` | Regex-based categoriser → static site at `docs/`. |
| `build_index.py` / `search.py` | Optional: DuckDB + VSS semantic search over descriptions. |

## Automation

`.github/workflows/sync.yml` runs daily at 06:00 UTC:

1. `sync_stars.py` (incremental; full sweep on Sundays)
2. `fetch_updated.py` (only touches newly added repos)
3. `build_site.py` (rebuilds `docs/`)
4. Commits `stars.jsonl`, `updated_at.json`, `docs/`, `sync_summary.json`

Requires repo secret **`STARS_PAT`** — fine-grained PAT with read access to
the user's starred repos (the default `GITHUB_TOKEN` cannot read another
user's stars).

Manual run: `gh workflow run sync.yml` (optionally `-f full=true`).

## Local use

```bash
pip install -r requirements.txt
python sync_stars.py          # or --full
python fetch_updated.py
python build_site.py
```

## Categories

Regex + topic matching across ~30 buckets grouped into 8 top-level sections
(AI & LLMs, Speech & Media, Data, Developer, Security & Privacy, Home &
Infra, Workflow & Productivity, Curated). New stars are classified on every
site rebuild — no manual tagging. Taxonomy lives inline in `build_site.py`.

## Semantic search (optional)

```bash
python build_index.py          # ~1 min on CPU
python search.py "mcp servers for home automation" --k 10
```
