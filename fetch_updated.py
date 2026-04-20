"""Fetch pushed_at (last updated) for every repo in stars.jsonl via GraphQL.

Batches 100 repos per request using aliased queries. Writes updated_at.json
mapping full_name -> pushed_at ISO string. Resumable: skips already-fetched.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
STARS = ROOT / "stars.jsonl"
OUT = ROOT / "updated_at.json"

BATCH = 100


def gql(query: str) -> dict:
    r = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"gh api failed: {r.stderr}")
    return json.loads(r.stdout)


def build_query(batch: list[tuple[str, str]]) -> str:
    parts = []
    for i, (owner, name) in enumerate(batch):
        # Alias i, escape quotes defensively
        owner_s = owner.replace('"', '\\"')
        name_s = name.replace('"', '\\"')
        parts.append(
            f'r{i}: repository(owner: "{owner_s}", name: "{name_s}") '
            f'{{ nameWithOwner pushedAt }}'
        )
    return "query{\n" + "\n".join(parts) + "\n}"


def main() -> None:
    repos = [json.loads(l) for l in STARS.open()]
    existing: dict[str, str] = {}
    if OUT.exists():
        existing = json.loads(OUT.read_text())

    todo: list[tuple[str, str, str]] = []
    for r in repos:
        fn = r["full_name"]
        if fn in existing:
            continue
        owner, _, name = fn.partition("/")
        todo.append((fn, owner, name))

    print(f"Total: {len(repos)}, already fetched: {len(existing)}, "
          f"to fetch: {len(todo)}")

    for start in range(0, len(todo), BATCH):
        chunk = todo[start:start + BATCH]
        pairs = [(o, n) for _, o, n in chunk]
        try:
            data = gql(build_query(pairs))
        except SystemExit as e:
            print(f"Batch {start} failed, retrying one-by-one: {e}",
                  file=sys.stderr)
            for fn, owner, name in chunk:
                try:
                    d = gql(build_query([(owner, name)]))
                    node = (d.get("data") or {}).get("r0")
                    if node and node.get("pushedAt"):
                        existing[fn] = node["pushedAt"]
                except Exception:
                    pass
            OUT.write_text(json.dumps(existing))
            continue

        d = data.get("data") or {}
        for i, (fn, _, _) in enumerate(chunk):
            node = d.get(f"r{i}")
            if node and node.get("pushedAt"):
                existing[fn] = node["pushedAt"]
            # else: repo deleted/renamed; leave unset

        if (start // BATCH) % 5 == 0:
            OUT.write_text(json.dumps(existing))
            print(f"  progress: {len(existing)}/{len(repos)}")

    OUT.write_text(json.dumps(existing))
    print(f"Done. {len(existing)} repos have pushed_at.")


if __name__ == "__main__":
    main()
