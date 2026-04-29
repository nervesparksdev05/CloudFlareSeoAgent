# SEO Agent — Cloudflare Workers (Python)

Stack: **FastAPI + Gemini 2.5 Pro + Pyodide**
Deployed on: **Cloudflare Workers (Python)**

---

## Project Structure

```
seo-agent/
├── src/
│   └── entry.py          # All agent code (FastAPI + tools)
├── requirements.txt      # Python dependencies
├── wrangler.toml         # Cloudflare Worker config
└── README.md
```

---

## Tools

| Tool | Endpoint | Description |
|---|---|---|
| Keyword Analyzer | `POST /tools/keyword-analyzer` | Primary/secondary keywords, LSI, intent |
| Meta Tag Generator | `POST /tools/meta-tag-generator` | Title, description, OG, Twitter tags |
| Content Scorer | `POST /tools/content-scorer` | Score content across 6 SEO dimensions |
| Readability Checker | `POST /tools/readability-checker` | Sentence complexity, reading level, passive voice |
| SEO Audit | `POST /tools/seo-audit` | Full on-page SEO audit, 12 checks |
| Smart Agent | `POST /agent` | Gemini auto-selects tools based on your query |

---

## Setup & Deploy

### 1. Install Wrangler
```bash
npm install -g wrangler
wrangler login
```

### 2. Set your Gemini API key as a secret
```bash
wrangler secret put GEMINI_API_KEY
# Paste your key when prompted
```

### 3. Test locally
```bash
wrangler dev
# Your agent runs at http://localhost:8787
```

### 4. Deploy
```bash
wrangler deploy
# Live at: https://seo-agent.<your-subdomain>.workers.dev
```

---

## API Usage Examples

### Keyword Analyzer
```bash
curl -X POST https://seo-agent.<subdomain>.workers.dev/tools/keyword-analyzer \
  -H "Content-Type: application/json" \
  -d '{"topic": "machine learning for beginners", "target_audience": "students"}'
```

### Meta Tag Generator
```bash
curl -X POST https://seo-agent.<subdomain>.workers.dev/tools/meta-tag-generator \
  -H "Content-Type: application/json" \
  -d '{"content": "A complete guide to Python programming for beginners", "brand_name": "CodeAcademy"}'
```

### Content Scorer
```bash
curl -X POST https://seo-agent.<subdomain>.workers.dev/tools/content-scorer \
  -H "Content-Type: application/json" \
  -d '{"content": "Your full page content here...", "target_keyword": "python tutorial"}'
```

### Readability Checker
```bash
curl -X POST https://seo-agent.<subdomain>.workers.dev/tools/readability-checker \
  -H "Content-Type: application/json" \
  -d '{"content": "Your full page content here..."}'
```

### SEO Audit
```bash
curl -X POST https://seo-agent.<subdomain>.workers.dev/tools/seo-audit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your full page content...",
    "target_keyword": "python tutorial",
    "page_title": "Python Tutorial for Beginners | CodeAcademy",
    "meta_description": "Learn Python from scratch with our beginner-friendly tutorial.",
    "url": "https://example.com/python-tutorial"
  }'
```

### Smart Agent (auto-selects tools)
```bash
curl -X POST https://seo-agent.<subdomain>.workers.dev/agent \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze this page for SEO",
    "content": "Your full page content...",
    "target_keyword": "python tutorial",
    "page_title": "Python Tutorial for Beginners",
    "url": "https://example.com/python-tutorial"
  }'
```

---

## How It Works

```
HTTP Request
     ↓
on_fetch(request, env)          ← Cloudflare Workers entry point
     ↓
FastAPI (via ASGI bridge)       ← Routes request to correct endpoint
     ↓
Tool function(s)                ← Keyword / Meta / Score / Readability / Audit
     ↓
call_gemini(prompt, api_key)    ← Calls Gemini 2.5 Pro via JS fetch (FFI)
     ↓
JSON response                   ← Structured output returned to client
```

---

## Notes

- `GEMINI_API_KEY` is stored as a Cloudflare secret — never in code
- All Gemini calls use JS `fetch()` via Pyodide's FFI bridge
- The `/agent` endpoint uses Gemini as a router — it decides which tools to run
- Cold start is under 1 second thanks to Cloudflare's memory snapshot system