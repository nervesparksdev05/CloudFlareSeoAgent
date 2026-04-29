# SEO Agent — Full Project Documentation

## What This Is

An AI-powered SEO analysis tool with two capabilities:
- **Site Analyzer** — crawls your entire website and returns a full SEO audit (scores, grades, issues, keyword analysis, action plan)
- **Content Generator** — generates fully rewritten SEO-optimized content for every page of your site

---

## Architecture

```
User (Browser)
     │
     ▼
Streamlit Frontend (streamlit_app.py)
     │  HTTP POST
     ▼
Cloudflare Workers Backend (src/entry.py)
  [Python Worker — free tier]
     │
     ├─► Nexus Scraper (Docker, local machine)
     │     exposed via ngrok tunnel
     │     POST /public/crawl/sync
     │
     └─► Gemini 2.5 Pro API
           Analyzes scraped data
           Returns structured JSON
```

### Components

| Component | Technology | URL |
|---|---|---|
| Backend API | Cloudflare Workers (Python) | `https://seo-agent-python.nervesparksdev05.workers.dev` |
| Frontend | Streamlit | Run locally with `streamlit run streamlit_app.py` |
| Web Scraper | Nexus (Docker, local) | `localhost:9080` → exposed via ngrok |
| AI Model | Gemini 2.5 Pro | Google AI API |

---

## Project Structure

```
seo-agent-python/
├── src/
│   └── entry.py          ← Cloudflare Worker (backend API)
├── streamlit_app.py      ← Frontend UI
├── .dev.vars             ← Local secrets (never commit to git)
├── wrangler.toml         ← Cloudflare Workers config
├── pyproject.toml        ← Python dependencies
└── python_modules/       ← Vendored dependencies (httpx, etc.)
```

---

## API Endpoints

### `GET /`
Health check.
```json
{"name": "SEO Agent API", "version": "3.0.0"}
```

### `POST /tools/analyze-site`
Full SEO audit of a website.

**Request:**
```json
{
  "url": "https://example.com",
  "target_keyword": "optional",
  "brand_name": "optional",
  "max_urls": 20
}
```

**Response fields:**
- `overall_site_score` — 0–100
- `grade` — A / B / C / D / F
- `total_pages_analyzed`
- `keywords` — primary, secondary, LSI keywords
- `site_wide_issues` — pages missing H1, thin content, no internal links, missing meta, etc.
- `per_page_audit` — score, grade, meta tags, readability, keyword presence per page
- `content_strategy` — gaps, strengths, top improvements
- `technical_seo` — internal linking, image optimization, heading structure scores
- `critical_issues` — list of urgent problems
- `quick_wins` — easy fixes
- `priority_action_plan` — ordered list of actions
- `target_keyword_used` — keyword used (auto-detected or provided)
- `discovered_urls` — all crawled URLs

### `POST /tools/content-generator`
Generates complete SEO-optimized content for every page.

**Request:**
```json
{
  "url": "https://example.com",
  "target_keyword": "optional",
  "max_urls": 15
}
```

**Response fields:**
- `target_keyword_used`
- `site_seo_strategy`
- `pages[]` — per page:
  - `issues_found`
  - `generated_content` — meta_title, meta_description, h1, h2_headings, intro_paragraph, body_sections, cta_text, internal_link_suggestions, og_title, og_description
  - `improvement_score`
  - `priority` — high / medium / low

---

## How the Scraper Works

Nexus runs locally as a Docker stack. The SEO Agent calls its `/public/crawl/sync` endpoint:

```python
POST /public/crawl/sync
{
  "url": "https://example.com",
  "max_pages": 20,
  "output_format": "seo"
}
```

Nexus crawls the entire site and returns structured SEO data per page:
```json
{
  "results": [
    {
      "url": "https://example.com/page",
      "structured_data": {
        "page_info": { "title": "...", "canonical": "..." },
        "meta_tags": { "description": "...", "og": {...} },
        "content_analysis": { "word_count": 0, "headings": {...} },
        "links": { "internal_count": 0, "external_count": 0 },
        "images": { "total_found": 0, "missing_alt": 0 },
        "technical": { "json_ld_count": 0 }
      }
    }
  ]
}
```

This data is passed directly to Gemini 2.5 Pro for analysis.

---

## Environment Variables

Stored in `.dev.vars` for local dev, and as Cloudflare Worker secrets for production.

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini 2.5 Pro API key |
| `NEXUS_API_KEY` | API key for Nexus scraper authentication |

To set production secrets:
```bash
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put NEXUS_API_KEY
```

---

## Local Development

### Prerequisites
- Node.js (for Wrangler CLI)
- Python 3.11+
- Docker Desktop
- ngrok

### Start everything

**1. Start Nexus scraper:**
```bash
cd "Desktop/nexus scrapper/Nexus_Scrape"
docker compose -p my_nexus up -d
```

**2. Start ngrok tunnel:**
```bash
ngrok http 9080
```
Copy the `https://xxxx.ngrok-free.app` URL.

**3. Update ngrok URL in `src/entry.py` line 24:**
```python
NEXUS_CRAWL_SYNC = "https://YOUR-NGROK-URL.ngrok-free.app/public/crawl/sync"
```

**4. Run Streamlit frontend:**
```bash
cd seo-agent-python
streamlit run streamlit_app.py
```

**5. (Optional) Test backend locally:**
```bash
npx wrangler dev
```

---

## Deployment

### Deploy backend to Cloudflare Workers
```bash
cd seo-agent-python
npx wrangler deploy
```

### Deploy frontend (Streamlit Community Cloud)
1. Push repo to GitHub (exclude `.dev.vars` — add to `.gitignore`)
2. Go to `share.streamlit.io`
3. Connect GitHub repo, set main file as `streamlit_app.py`
4. Done — public URL generated automatically

---

## Key Problems Solved During Development

### 1. Cloudflare Workers Free Tier — CPU Limit (10ms)
**Problem:** Free tier allows only 10ms CPU time per request. FastAPI + Pydantic initialization alone exceeded this.

**Solution:**
- Removed FastAPI entirely
- Replaced with a minimal `Default(WorkerEntrypoint)` class with a manual router in `fetch()`
- Moved all standard library imports (`json`, `os`, `re`, etc.) to module level — they run once at snapshot time, not per request
- Kept only `import httpx` deferred inside functions (large library, deferred intentionally)

### 2. `HTTPException` After Removing FastAPI
**Problem:** `from fastapi import HTTPException` was still inside `tool_content_generator` — importing FastAPI triggered Pydantic schema building, which exceeded CPU limit.

**Solution:** Replaced all `HTTPException` with plain `raise Exception(...)`.

### 3. Workerd Network Isolation — Can't Reach Localhost
**Problem:** Cloudflare Workers (workerd) sandbox blocks all requests to private/internal IP ranges including `localhost`, `127.0.0.1`, and `192.168.x.x`.

**Solution:** Used ngrok to expose local Nexus on a public HTTPS URL.

### 4. ngrok Wrong Port
**Problem:** ngrok was forwarding port 80 instead of 9080 where Nexus actually runs.

**Solution:** `ngrok http 9080`

### 5. 401 Unauthorized from Nexus
**Problem:** `.dev.vars` had an old/wrong API key.

**Solution:** Updated `NEXUS_API_KEY=nexus-demo-key-2026`

### 6. `Response.new()` AttributeError
**Problem:** Used JS-style `Response.new(...)` which doesn't exist in Python Workers SDK.

**Solution:** Changed to `Response(body, status=200, headers=CORS)`

### 7. Path Parsing Bug — GET / Returning 404
**Problem:** `urlparse(request.url).path` returned `""` for root path, not `"/"`.

**Solution:**
```python
path = urlparse(request.url).path.rstrip("/") or "/"
```

---

## Cloudflare Workers Free Tier Limits

| Limit | Value |
|---|---|
| CPU time per request | 10ms |
| I/O wait (HTTP calls) | Unlimited |
| Requests per day | 100,000 |
| Worker size (compressed) | 3MB (Python workers: higher) |
| Subrequests per request | 1,000 |

**Key insight:** Network calls to Nexus and Gemini are I/O wait — they don't count toward the 10ms CPU limit. Only Python execution (imports, loops, string processing) counts.

---

## Nexus Scraper — Local Docker Stack Services

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

## Nexus Scraper — Changes Made

All changes are on branch `feature/batch_v2` in the Nexus project.

### New Endpoints Added

| Endpoint | Description |
|---|---|
| `POST /public/crawl` | Async BFS crawl — returns `batch_id`, poll separately |
| `POST /public/crawl/sync` | **Blocking BFS crawl — waits and returns all results in one call** |
| `POST /public/scrape/sync` | Blocking single-page scrape |

### New Models (`services/nexus-api/src/models.py` and `services/nexus-worker/src/models.py`)

- `PublicCrawlRequest` — request body for `/public/crawl` and `/public/crawl/sync`
- `CrawlJob` — internal job payload passed from API to worker. Added `job_id: Optional[str]` field so each crawl node is tied to its registered batch entry

### BFS Crawler (`services/nexus-worker/src/worker.py`)

New `crawl_site_task` arq task implements Breadth-First Search crawling:
- Fetches and SEO-audits each page via the existing `scrape_job` logic
- Discovers internal links and enqueues child pages as new `crawl_site_task` jobs
- Enforces `max_pages` and `max_depth` limits
- Domain-locked: filters out external links and subdomains
- Uses atomic Redis `SADD` for deduplication (prevents same URL being crawled twice, even across concurrent workers)

### Batch Helper (`services/nexus-worker/src/batch.py` and `services/nexus-api/src/batch.py`)

- Added `add_job_to_batch()` — dynamically grows a batch as new pages are discovered during crawl
- Added `unlock_batch()` — clears the locked flag once BFS discovery is fully complete

### Bug Fixes Applied

#### 1. Worker couldn't enqueue child pages
`ctx["redis"]` is an `aioredis` client, not an arq pool — it has no `enqueue_job` method. Child pages were never queued so only the root URL was ever scraped.

**Fix:** Added `ctx["arq_pool"]` to worker startup/shutdown. Child tasks now enqueue via `ctx["arq_pool"].enqueue_job(...)`.

#### 2. Job ID mismatch — batch results always empty
`add_job_to_batch` registered one random ID in the batch meta, but `scrape_payload` generated a different random ID for the actual scrape. Results were stored under an ID the batch never tracked, so polling returned empty results.

**Fix:** `CrawlJob` now carries `job_id`. The worker uses `job.job_id` as the scrape payload ID, so the stored result always matches what's registered in the batch meta.

#### 3. `structured_data` missing from batch poll results
The SEO audit data (`structured_data`) was present on individual job results but was not included in the payload written to the batch result store. Polling the batch returned all pages with `structured_data: null`.

**Fix:** Added `"structured_data": scrape_result.structured_data` to the `_write_batch_result_hook` payload in `scrape_job`.

#### 4. Duplicate URLs in crawl results
Same URL (e.g. `/contact-us`) appeared 3× because a page can contain multiple links pointing to the same URL. The soft `sismember` check ran before any of them were marked visited, so all three passed.

**Fix:** Replaced `sismember` + later `sadd` with a single atomic `SADD` at enqueue time. `SADD` returns `0` if the URL is already in the set — first call adds and proceeds, subsequent calls for the same URL are skipped. Also fixes concurrent-worker race conditions.

#### 5. All child pages were silently skipped after fix #4
After moving `SADD` to enqueue time, the entry-guard at the top of `crawl_site_task` (`sismember + depth > 0 → skip`) fired for every child page because they were already in the visited set before their task ran.

**Fix:** Removed the `sismember` entry guard. Deduplication is now fully owned by the atomic `SADD` at enqueue time.

### Rebuild Commands

After any Nexus change:
```bash
# Both services changed:
docker compose -p my_nexus up -d --build nexus-api nexus-worker

# Worker only:
docker compose -p my_nexus up -d --build nexus-worker

# API only:
docker compose -p my_nexus up -d --build nexus-api
```

---

## Making It Fully Public (Future)

To remove the dependency on your local machine:

1. **Host Nexus on a VPS** — Hetzner CX22 (€4.51/mo, 4GB RAM) is the minimum viable option given the browser pool memory requirements
2. **Update URL in `entry.py`** — change `NEXUS_CRAWL_SYNC` to the VPS IP
3. **Deploy Streamlit** — Streamlit Community Cloud (free) or Railway/Render
4. **Open firewall port 9080** on the VPS

Current ngrok workaround: free ngrok gives a new URL on each restart. To avoid updating `entry.py` every time, get a **free static ngrok domain** at `dashboard.ngrok.com`.
