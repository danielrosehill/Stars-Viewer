# Stars-Viewer

Self-updating categorised browser for Daniel Rosehill's GitHub stars.
Weekly: pull new stars → diff against `stars.jsonl` → rebuild the static
site in `docs/`. GitHub Pages serves from `docs/`.

## Pipeline

| Script | Purpose |
| --- | --- |
| `sync_stars.py` | Incremental pull of `/user/starred`. Short-circuits when a page contains nothing new. `--full` reconciles unstars + metadata drift. |
| `fetch_updated.py` | GraphQL batch fetch of `pushedAt` for repos missing from `updated_at.json`. Resumable. |
| `build_site.py` | Regex-based categoriser → static site at `docs/`. |
| `build_index.py` / `search.py` | Optional: DuckDB + VSS semantic search over descriptions. |

## Automation

`.github/workflows/sync.yml` runs weekly, Sunday 03:00 UTC (moved from daily on
2026-11-07 to cut Actions use; scheduled runs have been starting about 7h late):

1. `sync_stars.py --full` (manual runs are incremental unless `-f full=true`)
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

about 30 buckets grouped into 9 top-level sections (AI & LLMs, Speech & Media,
Data, Developer, Security & Privacy, Home & Infra, Workflow & Productivity, Israel,
Curated).

- `llm_categories.json` (`full_name` → slug): one LLM-assigned category per repo.
  Takes priority at build time. Written by skill `categorize-stars` in the private
  `gh-stars-manager` plugin, run on demand from a laptop, never in Actions.
- Regex + topic matching in `build_site.py`: fallback for stars not yet in that
  file, so a star can sit in several buckets until it is categorised.
- `taxonomy.json`: the fixed list offered to the model (slug, title, group,
  description). Keep its slugs in step with `CATEGORIES` in `build_site.py`.

## Semantic search (optional)

```bash
python build_index.py          # ~1 min on CPU
python search.py "mcp servers for home automation" --k 10
```
