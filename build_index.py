#!/usr/bin/env python3
"""Build stars.duckdb from stars.jsonl: embed descriptions, create HNSW index."""
import json
import sys
from pathlib import Path

import duckdb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent
JSONL = ROOT / "stars.jsonl"
DB = ROOT / "stars.duckdb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384


def load_stars():
    rows = []
    with JSONL.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            topics = d.get("topics") or []
            rows.append({
                "full_name": d["full_name"],
                "owner": d.get("owner") or "",
                "description": d.get("description") or "",
                "language": d.get("language") or "",
                "topics": topics,
                "topics_str": " ".join(topics),
                "stargazers": d.get("stargazers") or 0,
                "archived": bool(d.get("archived")),
                "fork": bool(d.get("fork")),
                "starred_at": d.get("starred_at") or "",
                "url": d.get("url") or "",
            })
    return rows


def build():
    rows = load_stars()
    print(f"loaded {len(rows)} stars", file=sys.stderr)

    model = SentenceTransformer(MODEL_NAME)
    texts = [
        f"{r['full_name']}. {r['description']}. topics: {r['topics_str']}. language: {r['language']}"
        for r in rows
    ]
    print("embedding...", file=sys.stderr)
    embs = model.encode(texts, batch_size=128, show_progress_bar=True, normalize_embeddings=True)

    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    con.execute("INSTALL vss; LOAD vss;")
    con.execute(f"""
        CREATE TABLE stars (
            full_name VARCHAR PRIMARY KEY,
            owner VARCHAR,
            description VARCHAR,
            language VARCHAR,
            topics VARCHAR[],
            stargazers INTEGER,
            archived BOOLEAN,
            fork BOOLEAN,
            starred_at VARCHAR,
            url VARCHAR,
            embedding FLOAT[{DIM}]
        )
    """)
    con.executemany(
        """INSERT INTO stars VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                r["full_name"], r["owner"], r["description"], r["language"],
                r["topics"], r["stargazers"], r["archived"], r["fork"],
                r["starred_at"], r["url"], list(map(float, e)),
            )
            for r, e in zip(rows, embs)
        ],
    )
    con.execute("SET hnsw_enable_experimental_persistence = true;")
    con.execute("CREATE INDEX stars_hnsw ON stars USING HNSW (embedding) WITH (metric='cosine');")
    con.close()
    print(f"wrote {DB}", file=sys.stderr)


if __name__ == "__main__":
    build()
