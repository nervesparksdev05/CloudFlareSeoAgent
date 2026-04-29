"""
SEO Agent — Streamlit Frontend
Connects to the Cloudflare Workers backend at localhost:8787
"""

import streamlit as st
import requests

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
API_BASE = "https://seo-agent-python.nervesparksdev05.workers.dev"

# Nexus scraper — called directly from Streamlit to avoid Cloudflare's 30s limit.
# Update NEXUS_URL to your current ngrok URL when it changes.
NEXUS_URL    = "https://inaudible-zariah-fiendishly.ngrok-free.dev"
NEXUS_API_KEY = "nexus-demo-key-2026"

st.set_page_config(
    page_title="SEO Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def crawl_site(url: str, max_pages: int) -> list | None:
    """Call Nexus directly from Streamlit — no Cloudflare timeout applies."""
    try:
        resp = requests.post(
            f"{NEXUS_URL}/public/crawl/sync",
            headers={
                "X-API-Key": NEXUS_API_KEY,
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "Mozilla/5.0",
            },
            json={"url": url, "max_pages": max_pages, "output_format": "seo"},
            timeout=600,
        )
        if resp.status_code == 200:
            pages = resp.json().get("results", [])
            if not pages:
                st.error("Nexus returned no pages. Check the URL and try again.")
            return pages
        else:
            st.error(f"Nexus crawl failed ({resp.status_code}): {resp.text[:300]}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach Nexus. Make sure Docker is running and ngrok is active.")
        return None
    except Exception as e:
        st.error(f"Crawl failed: {e}")
        return None


def call_api(endpoint: str, payload: dict) -> dict | None:
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API Error {resp.status_code}: {resp.json().get('detail', resp.text[:300])}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure `npx wrangler dev` is running on port 8787.")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def grade_color(grade: str) -> str:
    return {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}.get(grade, "⚪")


def status_icon(status: str) -> str:
    return {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(status, "❓")


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────

with st.sidebar:
    st.title("🔍 SEO Agent")
    st.caption("Powered by Gemini 2.5 Pro + Nexus Scraper")
    st.divider()
    tool = st.radio(
        "Select Tool",
        ["📊 Site Analyzer", "✍️ Content Generator"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"Backend: `{API_BASE}`")


# ══════════════════════════════════════════════
# TOOL 1 — SITE ANALYZER
# ══════════════════════════════════════════════

if tool == "📊 Site Analyzer":
    st.title("📊 Site Analyzer")
    st.caption("Crawl your entire website and get a unified SEO audit powered by Gemini.")

    with st.form("analyze_form"):
        url = st.text_input("Website URL", placeholder="https://example.com")
        col1, col2 = st.columns(2)
        with col1:
            keyword = st.text_input("Target Keyword (optional)", placeholder="auto-detected if empty")
        with col2:
            max_urls = st.slider("Max URLs to crawl", 5, 100, 20)
        submitted = st.form_submit_button("🚀 Analyze Site", use_container_width=True)

    if submitted and url:
        with st.spinner(f"Step 1/2 — Crawling {url} (up to {max_urls} pages)..."):
            pages = crawl_site(url, max_urls)

        if pages:
            payload = {"url": url, "pages_data": pages}
            if keyword:
                payload["target_keyword"] = keyword

            with st.spinner(f"Step 2/2 — Analyzing {len(pages)} pages with Gemini..."):
                data = call_api("/tools/analyze-site", payload)
        else:
            data = None

        if data:
            result = data.get("result", {})

            # ── Overview metrics ──
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Overall Score", f"{result.get('overall_site_score', 0)}/100")
            col2.metric("Grade", f"{grade_color(result.get('grade',''))} {result.get('grade','')}")
            col3.metric("Pages Analyzed", result.get("total_pages_analyzed", 0))
            kw = result.get("target_keyword_used", "N/A")
            col4.metric("Keyword Used", kw, "auto-detected" if result.get("keyword_auto_detected") else "provided")

            # ── Site-wide signals ──
            signals = result.get("site_wide_signals", {})
            if signals:
                st.subheader("Site-Wide Signals")
                s1, s2, s3, s4, s5 = st.columns(5)
                s1.metric("Total Words", f"{signals.get('total_word_count', 0):,}")
                s2.metric("Total Images", signals.get("total_images", 0))
                s3.metric("Missing Alt Text", signals.get("total_images_missing_alt", 0))
                s4.metric("Internal Links", signals.get("total_internal_links", 0))
                s5.metric("External Links", signals.get("total_external_links", 0))

            # ── Site-wide issues ──
            issues = result.get("site_wide_issues", {})
            if issues:
                st.subheader("Site-Wide Issues")
                ic1, ic2 = st.columns(2)
                with ic1:
                    if issues.get("no_internal_links_pages"):
                        st.warning(f"**No Internal Links** ({len(issues['no_internal_links_pages'])} pages)")
                        for p in issues["no_internal_links_pages"]:
                            st.caption(f"• {p}")
                    if issues.get("thin_content_pages"):
                        st.warning(f"**Thin Content** ({len(issues['thin_content_pages'])} pages)")
                        for p in issues["thin_content_pages"]:
                            st.caption(f"• {p}")
                with ic2:
                    if issues.get("missing_meta_description_pages"):
                        st.error(f"**Missing Meta Description** ({len(issues['missing_meta_description_pages'])} pages)")
                        for p in issues["missing_meta_description_pages"]:
                            st.caption(f"• {p}")
                    if issues.get("pages_needing_rewrite"):
                        st.error(f"**Needs Rewrite** ({len(issues['pages_needing_rewrite'])} pages)")
                        for p in issues["pages_needing_rewrite"]:
                            st.caption(f"• {p}")

            # ── Per-page audit ──
            per_page = result.get("per_page_audit", [])
            if per_page:
                st.subheader("Per-Page Audit")
                for page in per_page:
                    score = page.get("score", 0)
                    grade = page.get("grade", "")
                    with st.expander(f"{grade_color(grade)} **{page.get('url', '')}** — Score: {score}/100 ({grade})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            checks = ["title_tag", "keyword_presence", "h1_tag", "internal_links", "content_length"]
                            for check in checks:
                                c = page.get(check, {})
                                if c:
                                    icon = status_icon(c.get("status", ""))
                                    label = check.replace("_", " ").title()
                                    detail = c.get("detail") or c.get("value") or f"Count: {c.get('count', c.get('word_count', ''))}"
                                    st.write(f"{icon} **{label}**: {detail}")

                        with col2:
                            # Meta tags
                            meta = page.get("meta_tags", {})
                            if meta:
                                st.write("**Meta Tags**")
                                st.caption(f"Title: `{meta.get('page_title', 'N/A')}` ({meta.get('page_title_length', 0)} chars)")
                                desc = meta.get("meta_description") or "❌ Missing"
                                st.caption(f"Description: `{desc[:80]}...`" if len(desc) > 80 else f"Description: `{desc}`")

                            # Readability
                            read = page.get("readability", {})
                            if read:
                                st.write("**Readability**")
                                st.caption(f"Level: {read.get('reading_level', 'N/A')} | Score: {read.get('score', 0)}/100")
                                if read.get("needs_rewrite"):
                                    st.caption(f"⚠️ {read.get('rewrite_reason', '')}")

            # ── Keywords ──
            keywords = result.get("keywords", {})
            if keywords:
                st.subheader("Keywords")
                kc1, kc2 = st.columns(2)
                with kc1:
                    st.write("**Primary Keywords**")
                    for kw in keywords.get("primary_keywords", []):
                        st.caption(f"• `{kw.get('keyword')}` — Vol: {kw.get('search_volume')} | Difficulty: {kw.get('difficulty')} | Intent: {kw.get('intent')}")
                with kc2:
                    st.write("**LSI Keywords**")
                    lsi = keywords.get("lsi_keywords", [])
                    st.write(", ".join([f"`{k}`" for k in lsi]))

            # ── Content strategy ──
            cs = result.get("content_strategy", {})
            if cs:
                st.subheader("Content Strategy")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Content Gaps**")
                    for gap in cs.get("content_gaps", []):
                        st.caption(f"• {gap}")
                with col2:
                    st.write("**Top Improvements**")
                    for imp in cs.get("top_improvements", []):
                        st.caption(f"• {imp}")

            # ── Action plan ──
            plan = result.get("priority_action_plan", [])
            if plan:
                st.subheader("Priority Action Plan")
                for i, action in enumerate(plan, 1):
                    st.info(f"**{i}.** {action}")

            # ── Raw JSON ──
            with st.expander("View Raw JSON"):
                st.json(result)


# ══════════════════════════════════════════════
# TOOL 2 — CONTENT GENERATOR
# ══════════════════════════════════════════════

elif tool == "✍️ Content Generator":
    st.title("✍️ Content Generator")
    st.caption("Generate complete SEO-optimized content for every page of your site based on audit results.")

    with st.form("content_form"):
        url = st.text_input("Website URL", placeholder="https://example.com")
        keyword = st.text_input("Target Keyword (optional)", placeholder="auto-detected if empty")
        max_urls = st.slider("Max URLs", 5, 50, 15)
        submitted = st.form_submit_button("✍️ Generate Content", use_container_width=True)

    if submitted and url:
        with st.spinner(f"Step 1/2 — Crawling {url} (up to {max_urls} pages)..."):
            pages = crawl_site(url, max_urls)

        if pages:
            payload = {"url": url, "pages_data": pages}
            if keyword:
                payload["target_keyword"] = keyword

            with st.spinner(f"Step 2/2 — Generating SEO content for {len(pages)} pages with Gemini..."):
                data = call_api("/tools/content-generator", payload)
        else:
            data = None

        if data:
            result = data.get("result", {})

            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("Pages Processed", result.get("total_pages", 0))
            col2.metric("Keyword Used", result.get("target_keyword_used", "N/A"))
            col3.metric("Keyword", "Auto-detected" if result.get("keyword_auto_detected") else "Provided")

            strategy = result.get("site_seo_strategy", "")
            if strategy:
                st.info(f"**SEO Strategy:** {strategy}")

            pages = result.get("pages", [])
            if pages:
                st.subheader("Generated Content Per Page")

                priority_order = {"high": 0, "medium": 1, "low": 2}
                pages_sorted = sorted(pages, key=lambda x: priority_order.get(x.get("priority", "low"), 3))

                for page in pages_sorted:
                    priority = page.get("priority", "low")
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                    improvement = page.get("improvement_score", "")
                    label = f"{priority_icon} **{page.get('url')}**"
                    if improvement:
                        label += f" — Estimated improvement: `{improvement}`"

                    with st.expander(label):
                        issues = page.get("issues_found", [])
                        if issues:
                            st.write("**Issues Found:**")
                            for issue in issues:
                                st.caption(f"⚠️ {issue}")
                            st.divider()

                        gen = page.get("generated_content", {})
                        if gen:
                            # Meta
                            st.write("**Meta Tags**")
                            col1, col2 = st.columns(2)
                            with col1:
                                meta_title = gen.get("meta_title", "")
                                st.text_area("Meta Title", meta_title, height=70, key=f"mt_{page.get('url')}")
                                st.caption(f"{len(meta_title)} chars {'✅' if 50 <= len(meta_title) <= 60 else '⚠️'}")
                            with col2:
                                meta_desc = gen.get("meta_description", "")
                                st.text_area("Meta Description", meta_desc, height=70, key=f"md_{page.get('url')}")
                                st.caption(f"{len(meta_desc)} chars {'✅' if 150 <= len(meta_desc) <= 160 else '⚠️'}")

                            # OG tags
                            og_title = gen.get("og_title", "")
                            og_desc = gen.get("og_description", "")
                            if og_title or og_desc:
                                col1, col2 = st.columns(2)
                                col1.text_area("OG Title", og_title, height=60, key=f"ogt_{page.get('url')}")
                                col2.text_area("OG Description", og_desc, height=60, key=f"ogd_{page.get('url')}")

                            st.divider()

                            # Headings
                            st.write("**Headings**")
                            st.text_input("H1", gen.get("h1", ""), key=f"h1_{page.get('url')}")
                            h2s = gen.get("h2_headings", [])
                            if h2s:
                                st.write("H2 Headings:")
                                for i, h2 in enumerate(h2s, 1):
                                    st.caption(f"H2 {i}: {h2}")

                            st.divider()

                            # Intro paragraph
                            intro = gen.get("intro_paragraph", "")
                            if intro:
                                st.write("**Intro Paragraph**")
                                st.text_area("", intro, height=120, key=f"intro_{page.get('url')}")

                            # Body sections
                            sections = gen.get("body_sections", [])
                            if sections:
                                st.write("**Body Sections**")
                                for i, sec in enumerate(sections):
                                    st.markdown(f"**{sec.get('heading', '')}**")
                                    st.text_area("", sec.get("content", ""), height=100, key=f"sec_{page.get('url')}_{i}")

                            # CTA
                            cta = gen.get("cta_text", "")
                            if cta:
                                st.write("**CTA**")
                                st.success(f"→ {cta}")

                            # Internal links
                            links = gen.get("internal_link_suggestions", [])
                            if links:
                                st.write("**Internal Link Suggestions**")
                                for link in links:
                                    st.caption(f"• Anchor: `{link.get('anchor_text')}` → Link to: `{link.get('link_to')}`")

            with st.expander("View Raw JSON"):
                st.json(result)
