"""Build a categorized GitHub Pages minisite from stars.jsonl + updated_at.json.

- Top-level group nav with dropdown submenus (8 groups, 30 sub-categories).
- Light mode.
- Client-side sort (stars / name / updated) + filter on category pages.
- Homepage shows groups A-Z; each group lists its sub-categories.
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

# (title, slug, topic_matches, keyword_regex, group)
CATEGORIES: list[tuple[str, str, set[str], str, str]] = [
    # AI & LLMs
    ("LLMs & Generative AI", "llm",
        {"llm", "llms", "large-language-models", "generative-ai", "gpt", "gpt-4",
         "chatgpt", "openai", "gemini", "deepseek", "llama", "ollama", "codex",
         "chatbot", "prompt-engineering", "llmops"},
        r"\bllm\b|\bgpt\b|gemini|deepseek|\bllama\b|ollama|chatgpt|openai", "AI & LLMs"),
    ("Claude & Claude Code", "claude",
        {"claude", "claude-code", "anthropic", "claude-desktop", "claude-skills",
         "skills"},
        r"\bclaude\b|anthropic", "AI & LLMs"),
    ("MCP (Model Context Protocol)", "mcp",
        {"mcp", "mcp-server", "mcp-client", "model-context-protocol", "mcp-servers"},
        r"\bmcp\b|model.context.protocol", "AI & LLMs"),
    ("AI Agents & Agentic", "agents",
        {"agent", "agents", "ai-agent", "ai-agents", "agentic-ai", "agentic",
         "multi-agent", "autonomous-agents"},
        r"\bagent(s|ic)?\b|autogen|crewai|langgraph", "AI & LLMs"),
    ("RAG & Vector Search", "rag",
        {"rag", "retrieval-augmented-generation", "vector-database", "vector-search",
         "embeddings", "semantic-search"},
        r"\brag\b|vector.database|embeddings|semantic.search|pinecone|weaviate|qdrant|chroma",
        "AI & LLMs"),
    ("Machine Learning & Deep Learning", "ml",
        {"machine-learning", "deep-learning", "pytorch", "tensorflow", "jax",
         "neural-network", "nlp", "computer-vision"},
        r"machine.learning|deep.learning|pytorch|tensorflow|neural|\bnlp\b|computer.vision",
        "AI & LLMs"),

    # Speech & Media
    ("STT (Speech-to-Text)", "stt",
        {"speech-to-text", "speech-recognition", "stt", "asr", "whisper",
         "transcription"},
        r"speech.to.text|speech.recognition|\bstt\b|\basr\b|whisper|transcri",
        "Speech & Media"),
    ("TTS (Text-to-Speech)", "tts",
        {"text-to-speech", "tts", "voice-cloning", "voice-synthesis"},
        r"text.to.speech|\btts\b|voice.cloning|voice.synthesis", "Speech & Media"),
    ("Audio (general)", "audio",
        {"audio", "audio-processing", "dsp", "sound", "music"},
        r"\baudio\b|audio.processing|\bdsp\b", "Speech & Media"),
    ("Video & Media", "media",
        {"video", "video-editing", "ffmpeg", "media", "streaming"},
        r"\bvideo\b|ffmpeg|\bmedia\b|streaming", "Speech & Media"),
    ("Image Generation & AI Art", "image-gen",
        {"stable-diffusion", "comfyui", "image-generation", "text-to-image",
         "midjourney", "flux", "dalle", "diffusion"},
        r"stable.diffusion|comfyui|image.generation|text.to.image|midjourney|\bflux\b|\bdalle?\b",
        "Speech & Media"),

    # Data
    ("SQL Databases", "sql-db",
        {"postgresql", "postgres", "mysql", "mariadb", "sqlite", "duckdb",
         "sql", "sqlserver", "oracle", "cockroachdb"},
        r"\bpostgres\w*|\bmysql\b|\bmariadb\b|\bsqlite\b|duckdb|\bsqlserver\b|cockroachdb",
        "Data"),
    ("Graph Databases", "graph-db",
        {"graph-database", "neo4j", "graphdb", "arangodb", "dgraph", "janusgraph",
         "cypher", "gremlin"},
        r"\bneo4j\b|graph.database|arangodb|dgraph|janusgraph|cypher|gremlin",
        "Data"),
    ("Document Databases", "document-db",
        {"mongodb", "couchdb", "document-database", "nosql", "firestore",
         "dynamodb", "elasticsearch", "opensearch"},
        r"\bmongo(db)?\b|couchdb|firestore|dynamodb|elasticsearch|opensearch",
        "Data"),
    ("Analytics & Data Science", "analytics",
        {"analytics", "data-science", "data-engineering", "etl", "data-visualization",
         "bi", "business-intelligence", "dashboards"},
        r"analytics|data.science|data.engineering|\betl\b|business.intelligence", "Data"),

    # Developer
    ("Developer Tools", "dev-tools",
        {"developer-tools", "devtools", "productivity-tools", "ide", "vscode",
         "debugger", "linter", "formatter", "build-tools"},
        r"developer.tools|\bdevtool|\bide\b|\bvscode\b|linter|debugger", "Developer"),
    ("CLI & Terminal", "cli",
        {"cli", "terminal", "tui", "shell", "command-line", "console",
         "bash", "zsh"},
        r"\bcli\b|command.line|\btui\b|\bterminal\b|\bshell\b", "Developer"),
    ("Frontend & Web", "frontend",
        {"react", "nextjs", "next-js", "vue", "svelte", "tailwindcss", "astro",
         "nuxt", "frontend", "web", "ui", "css"},
        r"\breact\b|next\.?js|\bvue\b|svelte|tailwind|\bastro\b|\bnuxt\b", "Developer"),
    ("DevOps, Docker & Kubernetes", "devops",
        {"docker", "kubernetes", "k8s", "devops", "terraform", "ansible", "helm",
         "ci-cd", "github-actions"},
        r"\bdocker\b|kubernetes|\bk8s\b|terraform|ansible|\bhelm\b", "Developer"),
    ("Mobile (Android / iOS)", "mobile",
        {"android", "ios", "flutter", "react-native", "kotlin-multiplatform",
         "mobile"},
        r"\bandroid\b|\bios\b|\bflutter\b|react.native", "Developer"),

    # Security & Privacy
    ("Security (general)", "security",
        {"security", "cybersecurity", "infosec", "pentesting", "hacking",
         "encryption", "vulnerability", "malware"},
        r"\bsecurity\b|pentest|cyber|encryption|hacking|malware|vulnerab",
        "Security & Privacy"),
    ("OSINT", "osint",
        {"osint", "open-source-intelligence", "reconnaissance", "threat-intelligence"},
        r"\bosint\b|open.source.intelligence|threat.intelligence|reconnaissance",
        "Security & Privacy"),
    ("Privacy", "privacy",
        {"privacy", "privacy-tools", "anti-tracking", "tor", "e2e-encryption"},
        r"\bprivacy\b|anti.tracking|\btor\b|e2e.encryption", "Security & Privacy"),
    ("PII & Data Protection", "pii",
        {"pii", "gdpr", "anonymization", "pseudonymization", "data-masking",
         "data-protection", "redaction", "hipaa", "ccpa"},
        r"\bpii\b|\bgdpr\b|\bhipaa\b|\bccpa\b|anonymiz|pseudonymiz|data.masking|redact",
        "Security & Privacy"),

    # Home & Infra
    ("Home Automation & Smart Home", "home-automation",
        {"home-assistant", "homeassistant", "zigbee", "zwave", "z-wave", "smarthome",
         "smart-home", "esphome", "hacs", "matter", "mqtt"},
        r"home.?assistant|\bhass\b|zigbee|smart.home|esphome|\bhacs\b",
        "Home & Infra"),
    ("Self-Hosted & Homelab", "self-hosted",
        {"self-hosted", "selfhosted", "homelab", "docker-compose", "proxmox",
         "truenas", "unraid", "nas"},
        r"self.hosted|homelab|proxmox|truenas|unraid", "Home & Infra"),

    # Productivity & Workflow
    ("Automation & Workflow", "automation",
        {"automation", "workflow", "n8n", "zapier", "workflow-automation",
         "task-automation", "rpa"},
        r"automation|workflow|\bn8n\b|zapier", "Workflow & Productivity"),
    ("Productivity", "productivity",
        {"productivity", "dashboard", "todo", "tasks", "time-tracking",
         "knowledge-management"},
        r"productivity|dashboard|\btodo\b|time.tracking", "Workflow & Productivity"),
    ("Writing, Docs & Markdown", "writing",
        {"markdown", "documentation", "obsidian", "notes", "note-taking", "writing",
         "static-site-generator", "blog"},
        r"markdown|obsidian|note.taking|documentation|static.site",
        "Workflow & Productivity"),

    # Curated
    ("Awesome Lists & Curated", "awesome",
        {"awesome", "awesome-list", "awesome-lists", "curated-list", "resources"},
        r"^awesome[-\s]|awesome.list", "Curated"),
]


def classify(repo: dict) -> list[str]:
    topics = {t.lower() for t in repo.get("topics") or []}
    name = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()
    haystack = f"{name} {desc} {' '.join(topics)}"
    out: list[str] = []
    for _, slug, topic_set, kw_re, _group in CATEGORIES:
        if topics & topic_set or re.search(kw_re, haystack):
            out.append(slug)
    return out


CSS = """
:root{
  color-scheme: light;
  --bg:#ffffff; --fg:#1f2328; --muted:#656d76; --link:#0969da;
  --border:#d8dee4; --panel:#f6f8fa; --hover:#eaeef2;
  --pill-bg:#ddf4ff; --pill-fg:#0969da; --accent:#0969da;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg)}
body{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",
  Helvetica,Arial,sans-serif}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}

/* ---- Top navigation ---- */
.topbar{background:#fff;border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100}
.topbar .inner{max-width:1200px;margin:0 auto;padding:0 24px;
  display:flex;align-items:center;gap:20px;height:56px}
.topbar .brand{font-weight:700;font-size:17px;color:var(--fg)}
.topbar .brand a{color:inherit}
.topbar .brand a:hover{text-decoration:none}
.topbar .nav{display:flex;gap:2px;flex:1}
.topbar .nav > li{position:relative;list-style:none}
.topbar .nav > li > a,
.topbar .nav > li > button{display:inline-flex;align-items:center;gap:4px;
  padding:8px 12px;border-radius:6px;color:var(--fg);font-size:14px;
  font-weight:500;background:none;border:none;cursor:pointer;
  font-family:inherit}
.topbar .nav > li > a:hover,
.topbar .nav > li > button:hover,
.topbar .nav > li.open > button{background:var(--hover);text-decoration:none}
.topbar .nav > li > a.active{background:var(--pill-bg);color:var(--pill-fg)}
.topbar .nav > li > button::after{content:"▾";font-size:10px;
  color:var(--muted);margin-left:2px}
.topbar ul.nav{padding:0;margin:0}

.dropdown{display:none;position:absolute;top:calc(100% + 4px);left:0;
  min-width:260px;background:#fff;border:1px solid var(--border);
  border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.08);
  padding:6px;list-style:none;margin:0;z-index:200}
.topbar .nav > li.open .dropdown,
.topbar .nav > li:hover .dropdown{display:block}
.dropdown li{list-style:none}
.dropdown a{display:flex;justify-content:space-between;align-items:center;
  padding:7px 10px;border-radius:5px;color:var(--fg);font-size:14px;
  gap:12px}
.dropdown a:hover{background:var(--hover);text-decoration:none}
.dropdown a.active{background:var(--pill-bg);color:var(--pill-fg);
  font-weight:600}
.dropdown a .n{color:var(--muted);font-size:12px;
  font-variant-numeric:tabular-nums}
.dropdown a.active .n{color:var(--pill-fg)}

.topbar .spacer{flex:1}
.topbar .menu-btn{display:none;background:var(--panel);
  border:1px solid var(--border);border-radius:6px;padding:6px 12px;
  cursor:pointer;font-size:14px}

/* ---- Page layout ---- */
main{max-width:1100px;margin:0 auto;padding:32px 24px}
header.page{margin-bottom:24px}
h1{margin:0 0 6px;font-size:28px;font-weight:600;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:14px}
.intro{color:var(--muted);margin:14px 0 22px;max-width:680px}

/* ---- Homepage groups ---- */
.group{margin-bottom:28px}
.group h2{font-size:16px;font-weight:600;margin:0 0 10px;
  color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));
  gap:10px}
.cat{background:#fff;border:1px solid var(--border);border-radius:8px;
  padding:14px 16px;transition:all .12s;text-decoration:none;color:var(--fg);
  display:block}
.cat:hover{border-color:var(--accent);text-decoration:none;
  box-shadow:0 1px 3px rgba(0,0,0,.06);transform:translateY(-1px)}
.cat .title{font-weight:600;font-size:15px;color:var(--fg);display:block}
.cat .count{color:var(--muted);font-size:13px;margin-top:4px}

/* ---- Category pages ---- */
.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  margin-bottom:16px;padding:12px 14px;background:var(--panel);
  border:1px solid var(--border);border-radius:8px}
.controls label{font-size:13px;color:var(--muted);font-weight:500}
.controls select,.controls input{padding:7px 11px;background:#fff;
  border:1px solid var(--border);border-radius:6px;color:var(--fg);
  font-size:14px;font-family:inherit}
.controls input.search{flex:1;min-width:220px}

.repo{background:#fff;border:1px solid var(--border);border-radius:8px;
  padding:14px 18px;margin-bottom:8px;transition:border-color .12s}
.repo:hover{border-color:#b6bec6}
.repo .name{font-weight:600;font-size:15px}
.repo .desc{color:var(--fg);font-size:14px;margin-top:4px;opacity:.85;
  line-height:1.5}
.repo .meta{color:var(--muted);font-size:12px;margin-top:8px;
  display:flex;flex-wrap:wrap;gap:4px 12px;align-items:center}
.pill{display:inline-block;background:var(--pill-bg);color:var(--pill-fg);
  border-radius:10px;padding:1px 8px;font-size:11px}

footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--border);
  color:var(--muted);font-size:13px;text-align:center}

@media (max-width:860px){
  .topbar .inner{padding:0 16px;gap:10px}
  .topbar .nav{display:none;position:absolute;top:100%;left:0;right:0;
    background:#fff;border-bottom:1px solid var(--border);
    flex-direction:column;padding:10px;gap:2px}
  .topbar .nav.open{display:flex}
  .topbar .nav > li{width:100%}
  .topbar .nav > li > a,
  .topbar .nav > li > button{width:100%;justify-content:space-between;
    padding:10px 12px}
  .dropdown{position:static;box-shadow:none;border:none;padding:0 0 0 12px;
    display:none}
  .topbar .nav > li.open .dropdown{display:block}
  .topbar .menu-btn{display:inline-block}
  main{padding:20px 16px}
}
"""

JS = """<script>
(function(){
  // Mobile menu toggle
  const menuBtn=document.querySelector('.menu-btn');
  const nav=document.querySelector('.topbar .nav');
  if(menuBtn&&nav){
    menuBtn.addEventListener('click',()=>nav.classList.toggle('open'));
  }
  // Dropdown click toggle (mobile + accessible)
  document.querySelectorAll('.topbar .nav > li > button').forEach(btn=>{
    btn.addEventListener('click',e=>{
      e.stopPropagation();
      const li=btn.parentElement;
      document.querySelectorAll('.topbar .nav > li.open')
        .forEach(o=>{if(o!==li)o.classList.remove('open')});
      li.classList.toggle('open');
    });
  });
  document.addEventListener('click',()=>{
    document.querySelectorAll('.topbar .nav > li.open')
      .forEach(o=>o.classList.remove('open'));
  });
  // Sort + filter on category pages
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
      if(key==='name') return a.dataset.name.localeCompare(b.dataset.name)*dir;
      if(key==='stars') return (+a.dataset.stars - +b.dataset.stars)*dir;
      if(key==='updated') return (a.dataset.updated||'').localeCompare(b.dataset.updated||'')*dir;
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


def esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


# Fixed group display order
GROUP_ORDER = [
    "AI & LLMs",
    "Speech & Media",
    "Data",
    "Developer",
    "Security & Privacy",
    "Home & Infra",
    "Workflow & Productivity",
    "Curated",
]


def build_nav(prefix: str, active_slug: str | None,
              bucket_sizes: dict[str, int]) -> str:
    """Top nav with group dropdowns."""
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for title, slug, _t, _k, group in CATEGORIES:
        if bucket_sizes.get(slug, 0) > 0:
            groups[group].append((title, slug))

    lis: list[str] = []
    home_active = ' class="active"' if active_slug == "__home__" else ""
    all_active = ' class="active"' if active_slug == "__all__" else ""
    lis.append(f'<li><a href="{prefix}index.html"{home_active}>Home</a></li>')

    for group in GROUP_ORDER:
        cats = sorted(groups.get(group, []), key=lambda c: c[0].lower())
        if not cats:
            continue
        any_active = any(slug == active_slug for _, slug in cats)
        open_cls = ' class="open"' if False else ""  # hover CSS handles desktop
        btn_cls = ' class="active"' if any_active else ""
        items = []
        for title, slug in cats:
            cls = ' class="active"' if slug == active_slug else ""
            items.append(
                f'<li><a href="{prefix}c/{slug}.html"{cls}>'
                f'<span>{esc(title)}</span>'
                f'<span class="n">{bucket_sizes.get(slug, 0):,}</span></a></li>'
            )
        lis.append(
            f'<li{open_cls}><button{btn_cls}>{esc(group)}</button>'
            f'<ul class="dropdown">{"".join(items)}</ul></li>'
        )
    lis.append(f'<li><a href="{prefix}all.html"{all_active}>All</a></li>')

    return (
        '<div class="topbar"><div class="inner">'
        '<div class="brand"><a href="' + prefix + 'index.html">★ Star Export</a></div>'
        f'<ul class="nav">{"".join(lis)}</ul>'
        '<button class="menu-btn" aria-label="Menu">☰</button>'
        '</div></div>'
    )


PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{css_path}?v={cachebust}">
</head><body>
{nav}
<main>
<header class="page"><h1>{h1}</h1><div class="sub">{sub}</div></header>
{body}
<footer>Generated from stars.jsonl — {total:,} starred repos
across {ncats} categories. Repos may appear in multiple categories.</footer>
</main>
{script}
</body></html>"""


def repo_html(r: dict, updated: dict[str, str]) -> str:
    fn = r["full_name"]
    topics = r.get("topics") or []
    pills = "".join(f'<span class="pill">{esc(t)}</span>' for t in topics[:5])
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
        f'<div class="meta"><span>★ {stars:,}</span>'
        f'{"<span>" + lang + "</span>" if lang else ""}'
        f'<span>updated {pushed_display}</span>'
        f'{pills}</div>'
        f'</div>'
    )


def sort_controls() -> str:
    return (
        '<div class="controls">'
        '<label>Sort by</label>'
        '<select id="sort">'
        '<option value="stars" selected>Star count</option>'
        '<option value="name">Repo name</option>'
        '<option value="updated">Last updated</option>'
        '</select>'
        '<select id="dir">'
        '<option value="desc" selected>Descending</option>'
        '<option value="asc">Ascending</option>'
        '</select>'
        '<input id="q" class="search" placeholder="Filter…" type="search">'
        '</div>'
    )


def main() -> None:
    import time
    cachebust = str(int(time.time()))

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

    for b in buckets.values():
        b.sort(key=lambda r: -(r.get("stargazers") or 0))
    uncategorized.sort(key=lambda r: -(r.get("stargazers") or 0))

    bucket_sizes = {slug: len(buckets.get(slug, []))
                    for _, slug, *_ in CATEGORIES}
    ncats = sum(1 for v in bucket_sizes.values() if v > 0)

    OUT.mkdir(exist_ok=True)
    (OUT / "c").mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS)
    (OUT / ".nojekyll").touch()

    # ---------- Homepage: grouped ----------
    group_html_parts: list[str] = []
    for group in GROUP_ORDER:
        cat_tuples = [(t, s) for t, s, *_rest, g in CATEGORIES
                      if g == group and bucket_sizes.get(s, 0) > 0]
        if not cat_tuples:
            continue
        cat_tuples.sort(key=lambda c: c[0].lower())
        cards = "".join(
            f'<a class="cat" href="c/{slug}.html">'
            f'<span class="title">{esc(title)}</span>'
            f'<div class="count">{bucket_sizes[slug]:,} repos</div></a>'
            for title, slug in cat_tuples
        )
        group_html_parts.append(
            f'<section class="group"><h2>{esc(group)}</h2>'
            f'<div class="grid">{cards}</div></section>'
        )

    index_body = (
        '<p class="intro">Browse Daniel Rosehill\'s GitHub stars, grouped into '
        'overlapping clusters. Repos may appear in multiple categories.</p>'
        + "".join(group_html_parts)
    )
    (OUT / "index.html").write_text(PAGE.format(
        title="Starred Repos — Daniel Rosehill",
        css_path="style.css",
        cachebust=cachebust,
        nav=build_nav("", "__home__", bucket_sizes),
        h1="Starred Repos",
        sub=f"{len(repos):,} repos · {ncats} categories",
        body=index_body,
        total=len(repos),
        ncats=ncats,
        script=JS,
    ))

    # ---------- Category pages ----------
    def write_cat(title: str, slug: str, items: list[dict]) -> None:
        repos_html = "\n".join(repo_html(r, updated) for r in items)
        body = (sort_controls()
                + f'<div id="repos">{repos_html}</div>')
        (OUT / "c" / f"{slug}.html").write_text(PAGE.format(
            title=f"{title} — Starred Repos",
            css_path="../style.css",
            cachebust=cachebust,
            nav=build_nav("../", slug, bucket_sizes),
            h1=title,
            sub=f"{len(items):,} repos",
            body=body,
            total=len(repos),
            ncats=ncats,
            script=JS,
        ))

    for title, slug, *_ in CATEGORIES:
        items = buckets.get(slug, [])
        if items:
            write_cat(title, slug, items)
    if uncategorized:
        write_cat("Uncategorized", "uncategorized", uncategorized)

    # ---------- All ----------
    repos_html = "\n".join(repo_html(r, updated) for r in repos)
    all_body = sort_controls() + f'<div id="repos">{repos_html}</div>'
    (OUT / "all.html").write_text(PAGE.format(
        title="All Starred Repos",
        css_path="style.css",
        cachebust=cachebust,
        nav=build_nav("", "__all__", bucket_sizes),
        h1="All Starred Repos",
        sub=f"{len(repos):,} repos",
        body=all_body,
        total=len(repos),
        ncats=ncats,
        script=JS,
    ))

    print(f"Built site with {len(repos)} repos, {ncats} active categories")
    for group in GROUP_ORDER:
        print(f"\n[{group}]")
        for title, slug, *_rest, g in CATEGORIES:
            if g == group and bucket_sizes.get(slug):
                print(f"  {bucket_sizes[slug]:5}  {title}")
    print(f"\n[Uncategorized]  {len(uncategorized)}")


if __name__ == "__main__":
    main()
