#!/usr/bin/env python3
"""Semantic search over stars.duckdb. Usage: ./search.py "query" [--lang Python] [--k 20]"""
import argparse
from pathlib import Path

import duckdb
from sentence_transformers import SentenceTransformer

DB = Path(__file__).parent / "stars.duckdb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--lang", help="filter by primary language")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--include-archived", action="store_true")
    args = ap.parse_args()

    q = " ".join(args.query)
    model = SentenceTransformer(MODEL_NAME)
    qv = list(map(float, model.encode(q, normalize_embeddings=True)))

    con = duckdb.connect(str(DB), read_only=True)
    con.execute("LOAD vss;")
    where = [] if args.include_archived else ["archived = false"]
    if args.lang:
        where.append(f"language = '{args.lang}'")
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
        SELECT full_name, stargazers, language, description,
               array_cosine_distance(embedding, ?::FLOAT[384]) AS dist
        FROM stars
        {where_clause}
        ORDER BY dist ASC
        LIMIT {args.k}
    """
    rows = con.execute(sql, [qv]).fetchall()
    for full_name, stars, lang, desc, dist in rows:
        sim = 1 - dist
        print(f"[{sim:.3f}] {full_name}  ({stars}★, {lang or '-'})")
        if desc:
            print(f"        {desc[:140]}")


if __name__ == "__main__":
    main()
