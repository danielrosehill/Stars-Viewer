"""Build a categorized GitHub Pages minisite from stars.jsonl + updated_at.json.

Rule-based classifier: each repo can match multiple categories (overlap allowed).
Output: docs/index.html (A-Z category grid), docs/c/<slug>.html (per-category
pages with client-side sort by name / stars / updated), docs/all.html.
Top nav bar on every page. Light mode.
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
STARS = ROOT / "stars.jsonl"
UPDATED = ROOT / "updated_at.json"
OUT = ROOT / "docs"

# (title, slug, topic_matches, keyword_regex)
CATEGORIES: list[tuple[str, str, set[str], str]] = [
    ("AI Agents & Agentic", "agents",
        {"agent", "agents", "ai-agent", "ai-agents", "agentic-ai", "agentic",
         "multi-agent", "autonomous-agents"},
        r"\bagent(s|ic)?\b|autogen|crewai|langgraph"),
    ("Analytics & Data Science", "analytics",
        {"analytics", "data-science", "data-engineering", "etl", "data-visualization",
         "bi", "business-intelligence", "dashboards"},
        r"analytics|data.science|data.engineering|\betl\b|business.intelligence"),
    ("Audio (general)", "audio",
        {"audio", "audio-processing", "dsp", "sound", "music"},
        r"\baudio\b|audio.processing|\bdsp\b"),
    ("Automation & Workflow", "automation",
        {"automation", "workflow", "n8n", "zapier", "workflow-automation",
         "task-automation", "rpa"},
        r"automation|workflow|\bn8n\b|zapier"),
    ("Awesome Lists & Curated", "awesome",
        {"awesome", "awesome-list", "awesome-lists", "curated-list", "resources"},
        r"^awesome[-\s]|awesome.list"),
    ("CLI & Terminal", "cli",
        {"cli", "terminal", "tui", "shell", "command-line", "console",
         "bash", "zsh"},
        r"\bcli\b|command.line|\btui\b|\bterminal\b|\bshell\b"),
    ("Claude & Claude Code", "claude",
        {"claude", "claude-code", "anthropic", "claude-desktop", "claude-skills",
         "skills"},
        r"\bclaude\b|anthropic"),
    ("Developer Tools", "dev-tools",
        {"developer-tools", "devtools", "productivity-tools", "ide", "vscode",
         "debugger", "linter", "formatter", "build-tools"},
        r"developer.tools|\bdevtool|\bide\b|\bvscode\b|linter|debugger"),
    ("DevOps, Docker & Kubernetes", "devops",
        {"docker", "kubernetes", "k8s", "devops", "terraform", "ansible", "helm",
         "ci-cd", "github-actions"},
        r"\bdocker\b|kubernetes|\bk8s\b|terraform|ansible|\bhelm\b"),
    ("Document Databases", "document-db",
        {"mongodb", "couchdb", "document-database", "nosql", "firestore",
         "dynamodb", "elasticsearch", "opensearch"},
        r"\bmongo(db)?\b|couchdb|firestore|dynamodb|elasticsearch|opensearch"),
    ("Frontend & Web", "frontend",
        {"react", "nextjs", "next-js", "vue", "svelte", "tailwindcss", "astro",
         "nuxt", "frontend", "web", "ui", "css"},
        r"\breact\b|next\.?js|\bvue\b|svelte|tailwind|\bastro\b|\bnuxt\b"),
    ("Graph Databases", "graph-db",
        {"graph-database", "neo4j", "graphdb", "arangodb", "dgraph", "janusgraph",
         "cypher", "gremlin"},
        r"\bneo4j\b|graph.database|arangodb|dgraph|janusgraph|cypher|gremlin"),
    ("Home Automation & Smart Home", "home-automation",
        {"home-assistant", "homeassistant", "zigbee", "zwave", "z-wave", "smarthome",
         "smart-home", "esphome", "hacs", "matter", "mqtt"},
        r"home.?assistant|\bhass\b|zigbee|smart.home|esphome|\bhacs\b"),
    ("Image Generation & AI Art", "image-gen",
        {"stable-diffusion", "comfyui", "image-generation", "text-to-image",
         "midjourney", "flux", "dalle", "diffusion"},
        r"stable.diffusion|comfyui|image.generation|text.to.image|midjourney|\bflux\b|\bdalle?\b"),
    ("LLMs & Generative AI", "llm",
        {"llm", "llms", "large-language-models", "generative-ai", "gpt", "gpt-4",
         "chatgpt", "openai", "gemini", "deepseek", "llama", "ollama", "codex",
         "chatbot", "prompt-engineering", "llmops"},
        r"\bllm\b|\bgpt\b|gemini|deepseek|\bllama\b|ollama|chatgpt|openai"),
    ("MCP (Model Context Protocol)", "mcp",
        {"mcp", "mcp-server", "mcp-client", "model-context-protocol", "mcp-servers"},
        r"\bmcp\b|model.context.protocol"),
    ("Machine Learning & Deep Learning", "ml",
        {"machine-learning", "deep-learning", "pytorch", "tensorflow", "jax",
         "neural-network", "nlp", "computer-vision"},
        r"machine.learning|deep.learning|pytorch|tensorflow|neural|\bnlp\b|computer.vision"),
    ("Mobile (Android / iOS)", "mobile",
        {"android", "ios", "flutter", "react-native", "kotlin-multiplatform",
         "mobile"},
        r"\bandroid\b|\bios\b|\bflutter\b|react.native"),
    ("OSINT", "osint",
        {"osint", "open-source-intelligence", "reconnaissance", "threat-intelligence"},
        r"\bosint\b|open.source.intelligence|threat.intelligence|reconnaissance"),
    ("PII & Data Protection", "pii",
        {"pii", "gdpr", "anonymization", "pseudonymization", "data-masking",
         "data-protection", "redaction", "hipaa", "ccpa"},
        r"\bpii\b|\bgdpr\b|\bhipaa\b|\bccpa\b|anonymiz|pseudonymiz|data.masking|redact"),
    ("Privacy", "privacy",
        {"privacy", "privacy-tools", "anti-tracking", "tor", "e2e-encryption"},
        r"\bprivacy\b|anti.tracking|\btor\b|e2e.encryption"),
    ("Productivity", "productivity",
        {"productivity", "dashboard", "todo", "tasks", "time-tracking",
         "knowledge-management"},
        r"productivity|dashboard|\btodo\b|time.tracking"),
    ("RAG & Vector Search", "rag",
        {"rag", "retrieval-augmented-generation", "vector-database", "vector-search",
         "embeddings", "semantic-search"},
        r"\brag\b|vector.database|embeddings|semantic.search|pinecone|weaviate|qdrant|chroma"),
    ("SQL Databases", "sql-db",
        {"postgresql", "postgres", "mysql", "mariadb", "sqlite", "duckdb",
         "sql", "sqlserver", "oracle", "cockroachdb"},
        r"\bpostgres\w*|\bmysql\b|\bmariadb\b|\bsqlite\b|duckdb|\bsqlserver\b|cockroachdb"),
    ("STT (Speech-to-Text)", "stt",
        {"speech-to-text", "speech-recognition", "stt", "asr", "whisper",
         "transcription"},
        r"speech.to.text|speech.recognition|\bstt\b|\basr\b|whisper|transcri"),
    ("Security (general)", "security",
        {"security", "cybersecurity", "infosec", "pentesting", "hacking",
         "encryption", "vulnerability", "malware"},
        r"\bsecurity\b|pentest|cyber|encryption|hacking|malware|vulnerab"),
    ("Self-Hosted & Homelab", "self-hosted",
        {"self-hosted", "selfhosted", "homelab", "docker-compose", "proxmox",
         "truenas", "unraid", "nas"},
        r"self.hosted|homelab|proxmox|truenas|unraid"),
    ("TTS (Text-to-Speech)", "tts",
        {"text-to-speech", "tts", "voice-cloning", "voice-synthesis"},
        r"text.to.speech|\btts\b|voice.cloning|voice.synthesis"),
    ("Video & Media", "media",
        {"video", "video-editing", "ffmpeg", "media", "streaming"},
        r"\bvideo\b|ffmpeg|\bmedia\b|streaming"),
    ("Writing, Docs & Markdown", "writing",
        {"markdown", "documentation", "obsidian", "notes", "note-taking", "writing",
         "static-site-generator", "blog"},
        r"markdown|obsidian|note.taking|documentation|static.site"),
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
  --bg:#ffffff; --fg:#1f2328; --muted:#656d76; --link:#0969da;
  --card:#ffffff; --border:#d0d7de; --nav-bg:#f6f8fa; --hover:#f6f8fa;
  --pill-bg:#ddf4ff; --pill-fg:#0969da;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",
  Helvetica,Arial,sans-serif;background:var(--bg);color:var(--fg)}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}

nav.topbar{background:var(--nav-bg);border-bottom:1px solid var(--border);
  padding:10px 20px;position:sticky;top:0;z-index:50}
nav.topbar .inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;
  gap:16px;flex-wrap:wrap}
nav.topbar .brand{font-weight:700;font-size:16px;color:var(--fg);margin-right:12px}
nav.topbar .brand a{color:inherit}
nav.topbar .links{display:flex;flex-wrap:wrap;gap:2px 14px;font-size:13px}
nav.topbar .links a{color:var(--fg);padding:2px 6px;border-radius:4px}
nav.topbar .links a:hover{background:#eaeef2;text-decoration:none}
nav.topbar .links a.active{background:var(--pill-bg);color:var(--pill-fg)}

.container{max-width:1100px;margin:0 auto;padding:24px 20px}
header.page{border-bottom:1px solid var(--border);padding-bottom:14px;
  margin-bottom:20px}
h1{margin:0 0 6px;font-size:26px;font-weight:600}
.sub{color:var(--muted);font-size:14px}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
  gap:10px}
.cat{background:var(--card);border:1px solid var(--border);border-radius:6px;
  padding:12px 14px;transition:background .15s}
.cat:hover{background:var(--hover)}
.cat a.title{font-weight:600;font-size:15px;color:var(--fg)}
.cat .count{color:var(--muted);font-size:13px;margin-top:2px}

.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  margin-bottom:14px;padding:12px;background:var(--nav-bg);
  border:1px solid var(--border);border-radius:6px}
.controls label{font-size:13px;color:var(--muted)}
.controls select,.controls input{padding:6px 10px;background:#fff;
  border:1px solid var(--border);border-radius:6px;color:var(--fg);font-size:14px}
.controls input.search{flex:1;min-width:200px}

.repo{background:var(--card);border:1px solid var(--border);border-radius:6px;
  padding:11px 14px;margin-bottom:6px}
.repo .name{font-weight:600;font-size:15px}
.repo .desc{color:var(--muted);font-size:14px;margin-top:3px}
.repo .meta{color:var(--muted);font-size:12px;margin-top:5px}
.pill{display:inline-block;background:var(--pill-bg);color:var(--pill-fg);
  border-radius:10px;padding:1px 8px;font-size:11px;margin-right:4px}

footer{margin-top:40px;padding:20px 0;border-top:1px solid var(--border);
  color:var(--muted);font-size:13px;text-align:center}
"""

NAV_TEMPLATE = """<nav class="topbar"><div class="inner">
<div class="brand"><a href="{home}">★ Star Export</a></div>
<div class="links">
<a href="{home}"{home_active}>Home</a>
<a href="{all}"{all_active}>All</a>
{cat_links}
</div></div></nav>"""

PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{css_path}">
</head><body>
{nav}
<div class="container">
<header class="page"><h1>{h1}</h1><div class="sub">{sub}</div></header>
{body}
<footer>Generated from stars.jsonl — {total:,} starred repos across
{ncats} categories. Repos may appear in multiple categories.</footer>
</div>
{script}
</body></html>"""


def esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def build_nav(css_path: str, active_slug: str | None) -> str:
    prefix = "../" if css_path.startswith("../") else ""
    home = f"{prefix}index.html"
    all_page = f"{prefix}all.html"
    # Top nav: show all categories A-Z, limited visually by CSS wrap
    sorted_cats = sorted(CATEGORIES, key=lambda c: c[0].lower())
    links = []
    for title, slug, *_ in sorted_cats:
        active = ' class="active"' if slug == active_slug else ""
        links.append(f'<a href="{prefix}c/{slug}.html"{active}>{esc(title)}</a>')
    return NAV_TEMPLATE.format(
        home=home,
        all=all_page,
        home_active=' class="active"' if active_slug == "__home__" else "",
        all_active=' class="active"' if active_slug == "__all__" else "",
        cat_links="\n".join(links),
    )


SORT_JS = """<script>
(function(){
  const list=document.getElementById('repos');
  if(!list) return;
  const sortSel=document.getElementById('sort');
  const dirSel=document.getElementById('dir');
  const q=document.getElementById('q');
  const items=Array.from(list.children);
  function apply(){
    const key=sortSel.value;
    const dir=dirSel.value==='desc'?-1:1;
    items.sort((a,b)=>{
      let va,vb;
      if(key==='name'){va=a.dataset.name;vb=b.dataset.name;
        return va.localeCompare(vb)*dir;}
      if(key==='stars'){va=+a.dataset.stars;vb=+b.dataset.stars;
        return (va-vb)*dir;}
      if(key==='updated'){va=a.dataset.updated||'';vb=b.dataset.updated||'';
        return va.localeCompare(vb)*dir;}
      return 0;
    });
    list.replaceChildren(...items);
    filter();
  }
  function filter(){
    const v=(q.value||'').toLowerCase();
    items.forEach(el=>{
      el.style.display=el.dataset.search.includes(v)?'':'none';
    });
  }
  sortSel.addEventListener('change',apply);
  dirSel.addEventListener('change',apply);
  q.addEventListener('input',filter);
  apply();
})();
</script>"""


def repo_html(r: dict, updated: dict[str, str]) -> str:
    fn = r["full_name"]
    topics = r.get("topics") or []
    pills = "".join(f'<span class="pill">{esc(t)}</span>' for t in topics[:6])
    desc = esc(r.get("description") or "")
    lang = esc(r.get("language") or "")
    stars = r.get("stargazers") or 0
    pushed = updated.get(fn, "")
    pushed_display = pushed[:10] if pushed else "—"
    search_blob = f"{fn.lower()} {(r.get('description') or '').lower()}"
    return (
        f'<div class="repo" '
        f'data-name="{esc(fn.lower())}" '
        f'data-stars="{stars}" '
        f'data-updated="{esc(pushed)}" '
        f'data-search="{esc(search_blob)}">'
        f'<div class="name"><a href="{esc(r["url"])}">{esc(fn)}</a></div>'
        f'<div class="desc">{desc}</div>'
        f'<div class="meta">★ {stars:,}'
        f'{" · " + lang if lang else ""}'
        f' · updated {pushed_display}'
        f'{" · " + pills if pills else ""}</div>'
        f'</div>'
    )


def sort_controls(default_sort: str = "stars", default_dir: str = "desc") -> str:
    opts_sort = [("stars", "Star count"), ("name", "Repo name"),
                 ("updated", "Last updated")]
    opts_dir = [("desc", "Descending"), ("asc", "Ascending")]
    sort_html = "".join(
        f'<option value="{v}"{" selected" if v==default_sort else ""}>{l}</option>'
        for v, l in opts_sort
    )
    dir_html = "".join(
        f'<option value="{v}"{" selected" if v==default_dir else ""}>{l}</option>'
        for v, l in opts_dir
    )
    return (
        '<div class="controls">'
        '<label>Sort by</label>'
        f'<select id="sort">{sort_html}</select>'
        f'<select id="dir">{dir_html}</select>'
        '<input id="q" class="search" placeholder="Filter…" type="search">'
        '</div>'
    )


def main() -> None:
    repos = [json.loads(l) for l in STARS.open()]
    updated = json.loads(UPDATED.read_text()) if UPDATED.exists() else {}

    buckets: dict[str, list[dict]] = defaultdict(list)
    uncategorized: list[dict] = []
    for r in repos:
        cats = classify(r)
        if cats:
            for c in cats:
                buckets[c].append(r)
        else:
            uncategorized.append(r)

    # Sort each bucket by stars desc (initial server-side order)
    for b in buckets.values():
        b.sort(key=lambda r: -(r.get("stargazers") or 0))
    uncategorized.sort(key=lambda r: -(r.get("stargazers") or 0))

    OUT.mkdir(exist_ok=True)
    (OUT / "c").mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS)
    (OUT / ".nojekyll").touch()

    ncats = sum(1 for _, s, *_ in CATEGORIES if buckets.get(s))

    # Index: A-Z sorted cards
    cat_cards = []
    for title, slug, *_ in sorted(CATEGORIES, key=lambda c: c[0].lower()):
        n = len(buckets.get(slug, []))
        if n == 0:
            continue
        cat_cards.append(
            f'<div class="cat"><a class="title" href="c/{slug}.html">{esc(title)}</a>'
            f'<div class="count">{n:,} repos</div></div>'
        )
    if uncategorized:
        cat_cards.append(
            f'<div class="cat"><a class="title" href="c/uncategorized.html">Uncategorized</a>'
            f'<div class="count">{len(uncategorized):,} repos</div></div>'
        )
    cat_cards.append(
        f'<div class="cat"><a class="title" href="all.html">All starred repos</a>'
        f'<div class="count">{len(repos):,} repos</div></div>'
    )

    index_body = (
        '<p>Browse Daniel Rosehill\'s GitHub stars, grouped into overlapping '
        'clusters. Each repo may appear in multiple categories.</p>'
        f'<div class="grid">{"".join(cat_cards)}</div>'
    )
    (OUT / "index.html").write_text(PAGE.format(
        title="Starred Repos — Daniel Rosehill",
        css_path="style.css",
        nav=build_nav("style.css", "__home__"),
        h1="Starred Repos",
        sub=f"{len(repos):,} repos · {ncats} categories",
        body=index_body,
        total=len(repos),
        ncats=ncats,
        script="",
    ))

    # Category pages
    def write_cat(title: str, slug: str, items: list[dict]) -> None:
        repos_html = "\n".join(repo_html(r, updated) for r in items)
        body = (
            sort_controls()
            + f'<div id="repos">{repos_html}</div>'
        )
        (OUT / "c" / f"{slug}.html").write_text(PAGE.format(
            title=f"{title} — Starred Repos",
            css_path="../style.css",
            nav=build_nav("../style.css", slug),
            h1=title,
            sub=f"{len(items):,} repos",
            body=body,
            total=len(repos),
            ncats=ncats,
            script=SORT_JS,
        ))

    for title, slug, *_ in CATEGORIES:
        items = buckets.get(slug, [])
        if items:
            write_cat(title, slug, items)
    if uncategorized:
        write_cat("Uncategorized", "uncategorized", uncategorized)

    # All-repos
    repos_html = "\n".join(repo_html(r, updated) for r in repos)
    all_body = sort_controls() + f'<div id="repos">{repos_html}</div>'
    (OUT / "all.html").write_text(PAGE.format(
        title="All Starred Repos",
        css_path="style.css",
        nav=build_nav("style.css", "__all__"),
        h1="All Starred Repos",
        sub=f"{len(repos):,} repos",
        body=all_body,
        total=len(repos),
        ncats=ncats,
        script=SORT_JS,
    ))

    print(f"Built site with {len(repos)} repos")
    for title, slug, *_ in sorted(CATEGORIES, key=lambda c: c[0].lower()):
        n = len(buckets.get(slug, []))
        if n:
            print(f"  {n:5}  {title}")
    print(f"  {len(uncategorized):5}  Uncategorized")


if __name__ == "__main__":
    main()
