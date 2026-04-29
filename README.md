# SEO Agent

AI-powered SEO analysis and content generation tool.

**Backend:** Cloudflare Workers (Python) — `WorkerEntrypoint` + Gemini 2.5 Pro  
**Frontend:** Streamlit  
**Scraper:** Nexus (Docker, local) exposed via ngrok  
**Live API:** `https://seo-agent-python.nervesparksdev05.workers.dev`

---

## What It Does

| Feature | Description |
|---|---|
| **Site Analyzer** | Crawls your entire website and returns a full SEO audit — scores, grades, keyword analysis, per-page issues, and a priority action plan |
| **Content Generator** | Generates fully rewritten, SEO-optimized content (meta tags, headings, body, CTAs, internal links) for every page of your site |

---

## Architecture

```
User (Browser)
     │
     ▼
Streamlit Frontend (streamlit_app.py)
     │  Crawl: calls Nexus directly (avoids Cloudflare's 30s timeout)
     │  Analysis: HTTP POST → Cloudflare Workers backend
     ▼
Nexus Scraper (Docker, local machine)
     exposed via ngrok tunnel
     POST /public/crawl/sync
     │
     └─► Returns structured SEO data per page
          │
          ▼
     Cloudflare Workers Backend (src/entry.py)
          │
          └─► Gemini 2.5 Pro API
               Returns structured JSON analysis
```

### Components

| Component | Technology | URL |
|---|---|---|
| Backend API | Cloudflare Workers (Python) | `https://seo-agent-python.nervesparksdev05.workers.dev` |
| Frontend | Streamlit | Run locally: `streamlit run streamlit_app.py` |
| Web Scraper | Nexus (Docker, local) | `localhost:9080` → exposed via ngrok |
| AI Model | Gemini 2.5 Pro | Google AI API |

---

## Project Structure

```
seo-agent-python/
├── src/
│   └── entry.py          ← Cloudflare Worker (backend API, no FastAPI)
├── streamlit_app.py      ← Streamlit frontend UI
├── wrangler.toml         ← Cloudflare Workers config
├── pyproject.toml        ← Python dependencies
├── .dev.vars             ← Local secrets (never commit)
└── python_modules/       ← Vendored dependencies (httpx, etc.)
```

---

## API Endpoints

### `GET /`
Health check.
```json
{"name": "SEO Agent API", "version": "3.0.0"}
```

---

### `POST /tools/analyze-site`
Full SEO audit of a website. The Streamlit frontend crawls with Nexus first, then sends the page data here.

**Request:**
```json
{
  "url": "https://example.com",
  "pages_data": [ ...nexus crawl results... ],
  "target_keyword": "optional",
  "brand_name": "optional"
}
```

**Response fields:**
- `overall_site_score` — 0–100
- `grade` — A / B / C / D / F
- `total_pages_analyzed`
- `keywords` — primary, secondary, LSI keywords, search intent
- `site_wide_issues` — missing H1, thin content, no internal links, missing meta/OG, etc.
- `per_page_audit` — score, grade, meta tags, readability, keyword presence per page
- `meta_recommendations` — recommended title/description patterns
- `content_strategy` — gaps, strengths, top improvements
- `technical_seo` — internal linking, image optimization, heading structure scores
- `critical_issues` — urgent problems list
- `quick_wins` — easy fixes
- `priority_action_plan` — ordered action list
- `target_keyword_used` — keyword used (auto-detected or provided)
- `discovered_urls` — all crawled URLs

---

### `POST /tools/content-generator`
Generates complete SEO-optimized content for every page.

**Request:**
```json
{
  "url": "https://example.com",
  "pages_data": [ ...nexus crawl results... ],
  "target_keyword": "optional"
}
```

**Response fields:**
- `target_keyword_used`
- `site_seo_strategy`
- `pages[]` — per page:
  - `issues_found`
  - `generated_content` — `meta_title`, `meta_description`, `h1`, `h2_headings`, `intro_paragraph`, `body_sections`, `cta_text`, `internal_link_suggestions`, `og_title`, `og_description`
  - `improvement_score`
  - `priority` — high / medium / low

---

## Environment Variables

Stored in `.dev.vars` for local dev, and as Cloudflare Worker secrets for production.

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini 2.5 Pro API key |
| `NEXUS_API_KEY` | Nexus scraper authentication (`nexus-demo-key-2026`) |

---

## Local Development

### Prerequisites
- Node.js (for Wrangler CLI)
- Python 3.12+
- Docker Desktop
- ngrok

### Start Everything

**1. Start Nexus scraper:**
```bash
cd "Desktop/nexus scrapper/Nexus_Scrape"
docker compose -p my_nexus up -d
```

**2. Start ngrok tunnel (port 9080):**
```bash
ngrok http 9080
```
Copy the `https://xxxx.ngrok-free.app` URL.

**3. Update ngrok URL in `streamlit_app.py` line 16:**
```python
NEXUS_URL = "https://YOUR-NGROK-URL.ngrok-free.app"
```

**4. Create `.dev.vars` with your secrets:**
```
GEMINI_API_KEY=your-key-here
NEXUS_API_KEY=nexus-demo-key-2026
```

**5. Run the Streamlit frontend:**
```bash
streamlit run streamlit_app.py
```

**6. (Optional) Test the backend locally:**
```bash
npx wrangler dev
# Backend runs at http://localhost:8787
```

---

## Deployment

### Deploy backend to Cloudflare Workers
```bash
npx wrangler deploy
```

Set production secrets:
```bash
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put NEXUS_API_KEY
```

### Deploy frontend (Streamlit Community Cloud)
1. Push repo to GitHub (`.dev.vars` is in `.gitignore` — never committed)
2. Go to `share.streamlit.io`
3. Connect your GitHub repo, set main file to `streamlit_app.py`
4. Public URL is generated automatically

---

## How the Scraper Works

Nexus runs locally as a Docker stack. The Streamlit frontend calls it directly to avoid Cloudflare's 30-second response limit:

```
POST /public/crawl/sync
{
  "url": "https://example.com",
  "max_pages": 20,
  "output_format": "seo"
}
```

Nexus crawls the site and returns structured SEO data per page, which is then forwarded to the Cloudflare Worker for Gemini analysis.

### Nexus Local Services

| Service | Port | Purpose |
|---|---|---|
| nexus-api | 9080 | Main API (entry point) |
| nexus-worker | 9081 | Job processing |
| nexus-proxy-router | 9082 | Proxy management |
| nexus-browser-lb | 9083 | Browser pool load balancer |
| nexus-antibot | 9084 | Anti-bot bypass |
| nexus-postgres | 5454 | Database |
| nexus-dashboard | 3120 | Admin UI |

---

## Cloudflare Workers Free Tier Limits

| Limit | Value |
|---|---|
| CPU time per request | 10ms |
| I/O wait (HTTP calls) | Unlimited |
| Requests per day | 100,000 |
| Worker size (compressed) | 3MB |
| Subrequests per request | 1,000 |

> Network calls to Nexus and Gemini are I/O wait — they don't count toward the 10ms CPU limit. Only Python execution (imports, loops, string ops) counts.

**Why no FastAPI:** FastAPI + Pydantic initialization alone exceeds the 10ms CPU limit. The backend uses a minimal `WorkerEntrypoint` with a manual router instead, and keeps standard library imports at module level (run once at snapshot time).

---
