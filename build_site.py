"""Build a categorized GitHub Pages minisite from stars.jsonl.

Rule-based classifier: each repo can match multiple categories (overlap allowed).
Output: docs/index.html + docs/c/<slug>.html + docs/all.html
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
STARS = ROOT / "stars.jsonl"
OUT = ROOT / "docs"

# (title, slug, topic_matches, keyword_regex)
# A repo joins a category if ANY topic is in topic_matches OR keyword_regex
# matches name/description/topics concatenation.
CATEGORIES: list[tuple[str, str, set[str], str]] = [
    ("MCP (Model Context Protocol)", "mcp",
        {"mcp", "mcp-server", "mcp-client", "model-context-protocol", "mcp-servers"},
        r"\bmcp\b|model.context.protocol"),
    ("Claude & Claude Code", "claude",
        {"claude", "claude-code", "anthropic", "claude-desktop", "claude-skills", "skills"},
        r"\bclaude\b|anthropic"),
    ("AI Agents & Agentic", "agents",
        {"agent", "agents", "ai-agent", "ai-agents", "agentic-ai", "agentic",
         "multi-agent", "autonomous-agents"},
        r"\bagent(s|ic)?\b|autogen|crewai|langgraph"),
    ("LLMs & Generative AI", "llm",
        {"llm", "llms", "large-language-models", "generative-ai", "gpt", "gpt-4",
         "chatgpt", "openai", "gemini", "deepseek", "llama", "ollama", "codex",
         "chatbot", "prompt-engineering", "llmops"},
        r"\bllm\b|\bgpt\b|gemini|deepseek|\bllama\b|ollama|chatgpt|openai"),
    ("RAG & Vector Search", "rag",
        {"rag", "retrieval-augmented-generation", "vector-database", "vector-search",
         "embeddings", "semantic-search"},
        r"\brag\b|vector.database|embeddings|semantic.search|pinecone|weaviate|qdrant|chroma"),
    ("Speech, Audio & TTS", "speech",
        {"whisper", "speech-to-text", "speech-recognition", "tts", "text-to-speech",
         "stt", "asr", "audio", "voice", "transcription"},
        r"whisper|speech.to.text|text.to.speech|\btts\b|\bstt\b|transcri|audio"),
    ("Home Automation & Smart Home", "home-automation",
        {"home-assistant", "homeassistant", "zigbee", "zwave", "z-wave", "smarthome",
         "smart-home", "esphome", "hacs", "matter", "mqtt"},
        r"home.?assistant|\bhass\b|zigbee|smart.home|esphome|\bhacs\b"),
    ("Self-Hosted & Homelab", "self-hosted",
        {"self-hosted", "selfhosted", "homelab", "docker-compose", "proxmox",
         "truenas", "unraid", "nas"},
        r"self.hosted|homelab|proxmox|truenas|unraid"),
    ("DevOps, Docker & Kubernetes", "devops",
        {"docker", "kubernetes", "k8s", "devops", "terraform", "ansible", "helm",
         "ci-cd", "github-actions"},
        r"\bdocker\b|kubernetes|\bk8s\b|terraform|ansible|\bhelm\b"),
    ("Developer Tools & CLI", "dev-tools",
        {"cli", "developer-tools", "devtools", "terminal", "tui", "shell",
         "command-line"},
        r"\bcli\b|command.line|\btui\b|terminal"),
    ("Automation & Workflow", "automation",
        {"automation", "workflow", "n8n", "zapier", "workflow-automation",
         "task-automation", "rpa"},
        r"automation|workflow|\bn8n\b|zapier"),
    ("Data, Databases & Analytics", "data",
        {"database", "postgresql", "mysql", "sqlite", "duckdb", "mongodb", "redis",
         "analytics", "data-science", "etl", "data-engineering"},
        r"database|postgres|\bsql\b|duckdb|mongodb|\bredis\b|analytics|data.science"),
    ("Machine Learning & Deep Learning", "ml",
        {"machine-learning", "deep-learning", "pytorch", "tensorflow", "jax",
         "neural-network", "nlp", "computer-vision"},
        r"machine.learning|deep.learning|pytorch|tensorflow|neural|\bnlp\b|computer.vision"),
    ("Frontend & Web", "frontend",
        {"react", "nextjs", "next-js", "vue", "svelte", "tailwindcss", "astro",
         "nuxt", "frontend", "web", "ui", "css"},
        r"\breact\b|next\.?js|\bvue\b|svelte|tailwind|\bastro\b|\bnuxt\b"),
    ("Security, Privacy & OSINT", "security",
        {"security", "privacy", "osint", "cybersecurity", "infosec", "pentesting",
         "hacking", "encryption"},
        r"security|privacy|\bosint\b|pentest|cyber|encryption|hacking"),
    ("Writing, Docs & Markdown", "writing",
        {"markdown", "documentation", "obsidian", "notes", "note-taking", "writing",
         "static-site-generator", "blog"},
        r"markdown|obsidian|note.taking|documentation|static.site"),
    ("Video & Media", "media",
        {"video", "video-editing", "ffmpeg", "image", "image-generation",
         "stable-diffusion", "comfyui", "media"},
        r"\bvideo\b|ffmpeg|stable.diffusion|comfyui|image.generation"),
    ("Awesome Lists & Curated", "awesome",
        {"awesome", "awesome-list", "awesome-lists", "curated-list", "resources"},
        r"^awesome[-\s]|awesome.list"),
    ("Productivity", "productivity",
        {"productivity", "dashboard", "todo", "tasks", "time-tracking",
         "knowledge-management"},
        r"productivity|dashboard|\btodo\b|time.tracking"),
    ("Mobile (Android / iOS)", "mobile",
        {"android", "ios", "flutter", "react-native", "kotlin-multiplatform",
         "mobile"},
        r"\bandroid\b|\bios\b|\bflutter\b|react.native"),
]


def classify(repo: dict) -> list[str]:
    topics = {t.lower() for t in repo.get("topics") or []}
    name = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()
    haystack = f"{name} {desc} {' '.join(topics)}"
    out: list[str] = []
    for _, slug, topic_set, kw_re in CATEGORIES:
        if topics & topic_set or re.search(kw_re, haystack):
            out.append(slug)
    return out


CSS = """
:root{
  --bg:#0d1117; --fg:#e6edf3; --muted:#8b949e; --link:#58a6ff;
  --card:#161b22; --border:#30363d; --accent:#f78166;
}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",
  Helvetica,Arial,sans-serif;background:var(--bg);color:var(--fg)}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}
.container{max-width:1100px;margin:0 auto;padding:32px 20px}
header{border-bottom:1px solid var(--border);padding-bottom:16px;margin-bottom:24px}
h1{margin:0 0 8px;font-size:28px}
h2{margin:32px 0 12px;font-size:20px;border-bottom:1px solid var(--border);
  padding-bottom:6px}
.sub{color:var(--muted);font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
  gap:12px}
.cat{background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:14px 16px}
.cat a.title{font-weight:600;font-size:15px;color:var(--fg)}
.cat .count{color:var(--muted);font-size:13px;margin-top:4px}
.repo{background:var(--card);border:1px solid var(--border);border-radius:6px;
  padding:12px 14px;margin-bottom:8px}
.repo .name{font-weight:600}
.repo .desc{color:var(--muted);font-size:14px;margin-top:4px}
.repo .meta{color:var(--muted);font-size:12px;margin-top:6px}
.pill{display:inline-block;background:#21262d;color:#c9d1d9;border-radius:10px;
  padding:1px 8px;font-size:11px;margin-right:4px}
nav.breadcrumb{margin-bottom:16px;font-size:14px;color:var(--muted)}
.search{width:100%;padding:8px 12px;background:var(--card);border:1px solid var(--border);
  border-radius:6px;color:var(--fg);font-size:14px;margin-bottom:12px}
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--border);
  color:var(--muted);font-size:13px}
"""

PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{css_path}">
</head><body>
<div class="container">
{breadcrumb}
<header><h1>{h1}</h1><div class="sub">{sub}</div></header>
{body}
<footer>Generated from <code>stars.jsonl</code> — {total} starred repos
across {ncats} categories. Repos may appear in multiple categories.</footer>
</div>
{script}
</body></html>"""


def esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def repo_html(r: dict) -> str:
    topics = r.get("topics") or []
    pills = "".join(
        f'<span class="pill">{esc(t)}</span>' for t in topics[:6]
    )
    desc = esc(r.get("description") or "")
    lang = esc(r.get("language") or "")
    stars = r.get("stargazers") or 0
    return (
        f'<div class="repo" data-search="{esc(r["full_name"].lower())} {esc((r.get("description") or "").lower())}">'
        f'<div class="name"><a href="{esc(r["url"])}">{esc(r["full_name"])}</a></div>'
        f'<div class="desc">{desc}</div>'
        f'<div class="meta">★ {stars:,}'
        f'{" · " + lang if lang else ""}'
        f'{" · " + pills if pills else ""}</div>'
        f'</div>'
    )


SEARCH_JS = """<script>
const q=document.getElementById('q');
if(q){q.addEventListener('input',()=>{
  const v=q.value.toLowerCase();
  document.querySelectorAll('.repo').forEach(el=>{
    el.style.display = el.dataset.search.includes(v) ? '' : 'none';
  });
});}
</script>"""


def main() -> None:
    repos = [json.loads(l) for l in STARS.open()]
    repos.sort(key=lambda r: -(r.get("stargazers") or 0))

    buckets: dict[str, list[dict]] = defaultdict(list)
    uncategorized: list[dict] = []
    for r in repos:
        cats = classify(r)
        if cats:
            for c in cats:
                buckets[c].append(r)
        else:
            uncategorized.append(r)

    OUT.mkdir(exist_ok=True)
    (OUT / "c").mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS)

    # Index page
    cat_cards = []
    for title, slug, *_ in CATEGORIES:
        n = len(buckets.get(slug, []))
        if n == 0:
            continue
        cat_cards.append(
            f'<div class="cat"><a class="title" href="c/{slug}.html">{esc(title)}</a>'
            f'<div class="count">{n} repos</div></div>'
        )
    if uncategorized:
        cat_cards.append(
            f'<div class="cat"><a class="title" href="c/uncategorized.html">Uncategorized</a>'
            f'<div class="count">{len(uncategorized)} repos</div></div>'
        )
    cat_cards.append(
        f'<div class="cat"><a class="title" href="all.html">All starred repos</a>'
        f'<div class="count">{len(repos)} repos</div></div>'
    )

    index_body = (
        '<p>Browse Daniel Rosehill\'s GitHub stars, grouped into overlapping clusters. '
        'Each repo may appear in multiple categories.</p>'
        f'<div class="grid">{"".join(cat_cards)}</div>'
    )
    (OUT / "index.html").write_text(PAGE.format(
        title="Starred Repos — Daniel Rosehill",
        css_path="style.css",
        breadcrumb="",
        h1="Starred Repos",
        sub=f"{len(repos):,} repos · {sum(1 for _,s,*_ in CATEGORIES if buckets.get(s))} categories",
        body=index_body,
        total=len(repos),
        ncats=sum(1 for _, s, *_ in CATEGORIES if buckets.get(s)),
        script="",
    ))

    # Category pages
    def write_cat(title: str, slug: str, items: list[dict]) -> None:
        body = (
            '<input id="q" class="search" placeholder="Filter within this category…">'
            + "".join(repo_html(r) for r in items)
        )
        (OUT / "c" / f"{slug}.html").write_text(PAGE.format(
            title=f"{title} — Starred Repos",
            css_path="../style.css",
            breadcrumb='<nav class="breadcrumb"><a href="../index.html">← All categories</a></nav>',
            h1=title,
            sub=f"{len(items):,} repos, sorted by stars",
            body=body,
            total=len(repos),
            ncats=len(CATEGORIES),
            script=SEARCH_JS,
        ))

    for title, slug, *_ in CATEGORIES:
        items = buckets.get(slug, [])
        if items:
            write_cat(title, slug, items)
    if uncategorized:
        write_cat("Uncategorized", "uncategorized", uncategorized)

    # All-repos page
    all_body = (
        '<input id="q" class="search" placeholder="Filter all repos…">'
        + "".join(repo_html(r) for r in repos)
    )
    (OUT / "all.html").write_text(PAGE.format(
        title="All Starred Repos",
        css_path="style.css",
        breadcrumb='<nav class="breadcrumb"><a href="index.html">← All categories</a></nav>',
        h1="All Starred Repos",
        sub=f"{len(repos):,} repos, sorted by stars",
        body=all_body,
        total=len(repos),
        ncats=len(CATEGORIES),
        script=SEARCH_JS,
    ))

    # Summary
    print(f"Built site with {len(repos)} repos")
    for title, slug, *_ in CATEGORIES:
        n = len(buckets.get(slug, []))
        if n:
            print(f"  {n:5}  {title}")
    print(f"  {len(uncategorized):5}  Uncategorized")


if __name__ == "__main__":
    main()
