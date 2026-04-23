"""Incremental sync of GitHub stars into stars.jsonl.

Pages `GET /user/starred` newest-first with the star+json media type so each
entry carries `starred_at`. Short-circuits once a page contains only repos
whose (full_name, starred_at) pair is already known. Also detects unstars
by comparing the full set returned against the existing file when run with
--full (otherwise unstars are reconciled during a weekly full sweep).

Writes stars.jsonl sorted by starred_at desc (matches current format).
Exits non-zero only on API failure; a no-op sync is a success.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
STARS = ROOT / "stars.jsonl"
UPDATED = ROOT / "updated_at.json"

PER_PAGE = 100
MEDIA = "application/vnd.github.star+json"


def gh_page(page: int) -> list[dict]:
    r = subprocess.run(
        ["gh", "api", "-H", f"Accept: {MEDIA}",
         f"/user/starred?per_page={PER_PAGE}&page={page}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"gh api /user/starred page={page} failed: {r.stderr}")
    return json.loads(r.stdout)


def normalize(entry: dict) -> dict:
    """Match the existing stars.jsonl schema."""
    repo = entry["repo"]
    return {
        "archived": repo.get("archived", False),
        "description": repo.get("description"),
        "fork": repo.get("fork", False),
        "full_name": repo["full_name"],
        "language": repo.get("language"),
        "owner": repo["owner"]["login"],
        "stargazers": repo.get("stargazers_count", 0),
        "starred_at": entry["starred_at"],
        "topics": repo.get("topics") or [],
        "url": repo["html_url"],
    }


def load_existing() -> dict[str, dict]:
    if not STARS.exists():
        return {}
    out: dict[str, dict] = {}
    for line in STARS.open():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[r["full_name"]] = r
    return out


def write_stars(by_name: dict[str, dict]) -> None:
    # Sort newest first by starred_at (matches current ordering).
    rows = sorted(by_name.values(),
                  key=lambda r: r.get("starred_at", ""), reverse=True)
    with STARS.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":"),
                               ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="Walk all pages (detects unstars and metadata drift).")
    ap.add_argument("--max-pages", type=int, default=200,
                    help="Safety cap on pages fetched.")
    args = ap.parse_args()

    existing = load_existing()
    print(f"Existing: {len(existing)} repos")

    seen_full: set[str] = set()
    added: list[str] = []
    updated: list[str] = []
    page = 1

    while page <= args.max_pages:
        entries = gh_page(page)
        if not entries:
            break

        page_new = 0
        for e in entries:
            r = normalize(e)
            fn = r["full_name"]
            seen_full.add(fn)
            prior = existing.get(fn)
            if prior is None:
                existing[fn] = r
                added.append(fn)
                page_new += 1
            elif (prior.get("starred_at") != r["starred_at"]
                  or prior.get("stargazers") != r["stargazers"]
                  or prior.get("description") != r["description"]
                  or prior.get("archived") != r["archived"]
                  or set(prior.get("topics") or []) != set(r["topics"])):
                existing[fn] = r
                updated.append(fn)

        print(f"  page {page}: {len(entries)} entries, {page_new} new")

        # Incremental mode: stop once we hit a full page with nothing new.
        if not args.full and page_new == 0:
            break
        if len(entries) < PER_PAGE:
            break
        page += 1

    removed: list[str] = []
    if args.full:
        removed = [fn for fn in list(existing) if fn not in seen_full]
        for fn in removed:
            del existing[fn]

    write_stars(existing)

    # Prune updated_at.json to match current set.
    if UPDATED.exists():
        try:
            up = json.loads(UPDATED.read_text())
            before = len(up)
            up = {k: v for k, v in up.items() if k in existing}
            if len(up) != before:
                UPDATED.write_text(json.dumps(up))
                print(f"Pruned updated_at.json: {before} -> {len(up)}")
        except json.JSONDecodeError:
            pass

    print(f"Sync done. added={len(added)} updated={len(updated)} "
          f"removed={len(removed)} total={len(existing)}")
    # Emit a machine-readable summary for the workflow step.
    summary = ROOT / "sync_summary.json"
    summary.write_text(json.dumps({
        "added": added, "updated": updated, "removed": removed,
        "total": len(existing),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
