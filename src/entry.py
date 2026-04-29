import json
import os
import re
from typing import Optional
from urllib.parse import urlparse
from workers import WorkerEntrypoint, Response


def clean_json(raw: str) -> str:
    raw = re.sub(r"```(?:json)?|```", "", raw).strip()
    start = min(
        (raw.find("{") if raw.find("{") != -1 else len(raw)),
        (raw.find("[") if raw.find("[") != -1 else len(raw)),
    )
    end = max(raw.rfind("}"), raw.rfind("]"))
    if start < end:
        raw = raw[start:end + 1]
    return raw


def signals_from_structured(structured: dict) -> dict:
    page_info = structured.get("page_info", {})
    meta      = structured.get("meta_tags", {})
    content   = structured.get("content_analysis", {})
    links     = structured.get("links", {})
    images    = structured.get("images", {})
    headings  = content.get("headings", {})

    return {
        "page_title":              page_info.get("title", ""),
        "canonical":               page_info.get("canonical", ""),
        "meta_description":        meta.get("description") or "",
        "meta_description_length": len(meta.get("description") or ""),
        "og_title":                meta.get("og", {}).get("title", ""),
        "og_description":          meta.get("og", {}).get("description", ""),
        "h1_tags":                 headings.get("h1", []),
        "h2_tags":                 headings.get("h2", [])[:5],
        "h3_tags":                 headings.get("h3", [])[:5],
        "word_count":              content.get("word_count", 0),
        "text_content_ratio":      content.get("text_content_ratio", 0),
        "total_images":            images.get("total_found", 0),
        "images_missing_alt":      images.get("missing_alt", 0),
        "internal_links_count":    links.get("internal_count", 0),
        "external_links_count":    links.get("external_count", 0),
        "json_ld_count":           structured.get("technical", {}).get("json_ld_count", 0),
    }


async def tool_analyze_site(
    url: str,
    target_keyword: Optional[str],
    brand_name: Optional[str],
    pages: list,
    gemini_key: str,
) -> dict:
    import httpx

    if not pages:
        raise Exception("No scraped pages provided.")

    keyword_auto_detected = not bool(target_keyword)
    brand_line = f"Brand: {brand_name}" if brand_name else ""
    page_count = len(pages)
    pages_data_json = json.dumps(
        [{"url": p.get("url", ""), "seo_data": p.get("structured_data", {})} for p in pages],
        separators=(",", ":"),
    )

    keyword_instruction = (
        f"Target Keyword: {target_keyword}"
        if target_keyword else
        "Target Keyword: NOT PROVIDED — auto-detect the best primary keyword from the content and use it throughout your analysis. Include it in the 'target_keyword_used' field."
    )

    prompt = f"""
You are a senior SEO analyst. Perform a complete SEO analysis for the ENTIRE website below.

Site        : {url}
{keyword_instruction}
{brand_line}
Total Pages : {page_count}

Full SEO data for every page (from Nexus scraper):
{pages_data_json}

Respond ONLY in valid JSON with this exact structure (no extra text, no markdown):
{{
  "overall_site_score": 0,
  "grade": "A | B | C | D | F",
  "site": "{url}",
  "total_pages_analyzed": {page_count},

  "keywords": {{
    "primary_keywords": [
      {{ "keyword": "...", "search_volume": "high | medium | low", "difficulty": "easy | medium | hard", "intent": "informational | commercial | transactional | navigational" }}
    ],
    "secondary_keywords": [{{ "keyword": "...", "relevance": "high | medium | low" }}],
    "lsi_keywords": ["..."],
    "search_intent_summary": "..."
  }},

  "site_wide_issues": {{
    "missing_h1_pages": ["url1", "url2"],
    "thin_content_pages": ["url1", "url2"],
    "no_internal_links_pages": ["url1", "url2"],
    "missing_alt_text_pages": ["url1", "url2"],
    "pages_needing_rewrite": ["url1", "url2"],
    "missing_meta_description_pages": ["url1", "url2"],
    "missing_og_tags_pages": ["url1", "url2"]
  }},

  "per_page_audit": [
    {{
      "url": "...",
      "meta_tags": {{
        "page_title": "...",
        "page_title_length": 0,
        "page_title_status": "pass | warning | fail",
        "meta_description": "...",
        "meta_description_length": 0,
        "meta_description_status": "pass | warning | fail",
        "og_title": "...",
        "og_description": "...",
        "missing_meta_description": true,
        "missing_og_tags": true
      }},
      "title_tag": {{ "status": "pass | warning | fail", "detail": "..." }},
      "keyword_presence": {{ "status": "pass | warning | fail", "detail": "..." }},
      "content_length": {{ "status": "pass | warning | fail", "word_count": 0 }},
      "internal_links": {{ "status": "pass | warning | fail", "count": 0 }},
      "h1_tag": {{ "status": "pass | warning | fail", "value": "..." }},
      "readability": {{
        "reading_level": "Elementary | Middle School | High School | College | Expert",
        "score": 0,
        "estimated_reading_time_minutes": 0.0,
        "passive_voice_count": 0,
        "long_sentences_count": 0,
        "complex_words_count": 0,
        "transition_words_usage": "good | needs improvement | poor",
        "needs_rewrite": true,
        "rewrite_reason": "..."
      }},
      "score": 0,
      "grade": "A | B | C | D | F"
    }}
  ],

  "meta_recommendations": {{
    "site_meta_title_pattern": "...",
    "site_meta_description_pattern": "...",
    "focus_keyword": "..."
  }},

  "content_strategy": {{
    "overall_score": 0,
    "keyword_coverage": "...",
    "content_gaps": ["...", "..."],
    "strengths": ["...", "..."],
    "top_improvements": ["...", "...", "..."]
  }},

  "technical_seo": {{
    "internal_linking_score": 0,
    "internal_linking_feedback": "...",
    "image_optimization_score": 0,
    "image_optimization_feedback": "...",
    "heading_structure_score": 0,
    "heading_structure_feedback": "..."
  }},

  "critical_issues": ["...", "..."],
  "quick_wins": ["...", "..."],
  "priority_action_plan": ["...", "...", "..."],
  "target_keyword_used": "..."
}}
"""

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={gemini_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 16384},
    })

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(gemini_url, content=payload, headers={"Content-Type": "application/json"})

    if resp.status_code != 200:
        raise Exception(f"Gemini error: {resp.text[:300]}")

    try:
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise Exception(f"Gemini response malformed: {resp.text[:300]}")

    try:
        result = json.loads(clean_json(raw))
    except json.JSONDecodeError:
        result = {"raw_response": raw}

    result["discovered_urls"]       = [p.get("url", "") for p in pages]
    result["keyword_auto_detected"] = keyword_auto_detected
    return result


async def tool_content_generator(
    url: str,
    target_keyword: Optional[str],
    pages: list,
    gemini_key: str,
) -> dict:
    import httpx

    if not pages:
        raise Exception("No scraped pages provided.")

    pages_data = [
        {"url": p.get("url", ""), "signals": signals_from_structured(p.get("structured_data") or {})}
        for p in pages
    ]

    keyword_auto_detected = not bool(target_keyword)
    if not target_keyword:
        target_keyword = "not provided — detect from content"

    pages_info = json.dumps([
        {
            "url": p["url"],
            "page_title":      p["signals"].get("page_title", ""),
            "meta_description": p["signals"].get("meta_description", ""),
            "h1":              p["signals"].get("h1_tags", []),
            "h2":              p["signals"].get("h2_tags", []),
            "word_count":      p["signals"].get("word_count", 0),
            "internal_links":  p["signals"].get("internal_links_count", 0),
        }
        for p in pages_data
    ], indent=2)

    prompt = f"""
You are an expert SEO content writer and strategist.
Analyze every page of this website and generate complete, SEO-optimized content for each page.

Site           : {url}
Target Keyword : {target_keyword}
Total Pages    : {len(pages_data)}

Current page data:
{pages_info}

For EVERY page, generate fully rewritten SEO-optimized content based on the page's purpose.
Focus especially on pages with thin content, missing keywords, or generic headings.

Respond ONLY in valid JSON:
{{
  "target_keyword_used": "...",
  "site_seo_strategy": "...",
  "pages": [
    {{
      "url": "...",
      "issues_found": ["...", "..."],
      "generated_content": {{
        "meta_title": "...(50-60 chars)",
        "meta_description": "...(150-160 chars)",
        "h1": "...(keyword-rich, compelling)",
        "h2_headings": ["...", "...", "..."],
        "intro_paragraph": "...(150-200 words, keyword in first sentence)",
        "body_sections": [
          {{
            "heading": "...",
            "content": "...(150-200 words)"
          }}
        ],
        "cta_text": "...",
        "internal_link_suggestions": [
          {{"anchor_text": "...", "link_to": "..."}}
        ],
        "og_title": "...",
        "og_description": "..."
      }},
      "improvement_score": "estimated score improvement e.g. +25 points",
      "priority": "high | medium | low"
    }}
  ]
}}
"""

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={gemini_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 16384},
    })

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(gemini_url, content=payload, headers={"Content-Type": "application/json"})

    if resp.status_code != 200:
        raise Exception(f"Gemini error: {resp.text[:300]}")

    try:
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(clean_json(raw))
    except Exception:
        result = {"raw_response": resp.text[:1000]}

    result["site"]                  = url
    result["total_pages"]           = len(pages_data)
    result["keyword_auto_detected"] = keyword_auto_detected
    return result


def _get_env_key(env, key: str) -> str:
    import os
    val = getattr(env, key, None)
    if val:
        return val
    return os.environ.get(key, "")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import json
        from workers import Response

        CORS = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Content-Type": "application/json",
        }

        if request.method == "OPTIONS":
            return Response("", status=204, headers=CORS)

        from urllib.parse import urlparse
        path = urlparse(request.url).path.rstrip("/") or "/"

        try:
            if request.method == "GET" and path == "/":
                body = json.dumps({"name": "SEO Agent API", "version": "3.0.0"})
                return Response(body, status=200, headers=CORS)

            if request.method != "POST":
                return Response(json.dumps({"detail": "Not Found"}), status=404, headers=CORS)

            gemini_key = _get_env_key(self.env, "GEMINI_API_KEY")
            if not gemini_key:
                return Response(json.dumps({"detail": "GEMINI_API_KEY not configured"}), status=500, headers=CORS)

            body = json.loads(await request.text())

            if path == "/tools/analyze-site":
                pages = body.get("pages_data")
                if not pages:
                    return Response(json.dumps({"detail": "pages_data is required"}), status=400, headers=CORS)
                result = await tool_analyze_site(
                    body.get("url"), body.get("target_keyword"),
                    body.get("brand_name"), pages, gemini_key,
                )
                return Response(json.dumps({"tool": "analyze-site", "result": result}), status=200, headers=CORS)

            if path == "/tools/content-generator":
                pages = body.get("pages_data")
                if not pages:
                    return Response(json.dumps({"detail": "pages_data is required"}), status=400, headers=CORS)
                result = await tool_content_generator(
                    body.get("url"), body.get("target_keyword"),
                    pages, gemini_key,
                )
                return Response(json.dumps({"tool": "content-generator", "result": result}), status=200, headers=CORS)

            return Response(json.dumps({"detail": "Not Found"}), status=404, headers=CORS)

        except Exception as e:
            return Response(json.dumps({"detail": str(e)}), status=500, headers=CORS)
