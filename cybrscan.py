#!/usr/bin/env python3
"""
CybrScan — AI-powered website inspector and improver.
Open a site, see it, analyze it, fix it.

Usage:
    python3 cybrscan.py https://example.com
    python3 cybrscan.py https://mysite.dev --model google/gemini-3-flash-preview
    python3 cybrscan.py https://mysite.dev --save ./reports/mysite
    python3 cybrscan.py https://mysite.dev --mobile
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Missing httpx. Install: pip3 install httpx")
    sys.exit(1)

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Missing playwright. Install: pip3 install playwright && python3 -m playwright install chromium")
    sys.exit(1)


DEFAULT_MODEL = "google/gemini-2.5-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are CybrScan, an expert website analyst and developer consultant. You inspect websites visually and technically to find issues and suggest improvements.

When analyzing a website screenshot and its technical data, evaluate:

## Visual & Design
- Layout quality, spacing, alignment
- Typography hierarchy and readability
- Color contrast and accessibility
- Visual hierarchy — is the most important content prominent?
- Mobile responsiveness indicators
- Brand consistency and professionalism

## UX & Conversion
- CTA placement and clarity
- Navigation intuitiveness
- Form friction
- Trust signals (testimonials, badges, social proof)
- User flow clarity

## Technical
- Console errors (if provided)
- Missing meta tags, OG tags
- Accessibility issues (from DOM snapshot)
- Broken elements or layout issues

## Content
- Copy quality and persuasiveness
- Value proposition clarity
- Information architecture
- Content hierarchy

For each issue found:
1. State the issue clearly
2. Rate severity: 🔴 Critical / 🟠 Major / 🟡 Minor / 💡 Suggestion
3. Explain WHY it matters
4. Give a SPECIFIC, actionable fix (code snippet if applicable)

Be honest and direct. Don't sugarcoat. If the site looks great, say so — but always find things to improve.
Output in clean markdown."""


MOBILE_DEVICE = {
    "width": 390,
    "height": 844,
    "device_scale_factor": 3,
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
}


async def capture_page(url: str, width: int = 1280, height: int = 800, mobile: bool = False):
    """Open URL in Playwright, capture screenshot + accessibility snapshot + stats."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        if mobile:
            context = await browser.new_context(
                viewport={"width": MOBILE_DEVICE["width"], "height": MOBILE_DEVICE["height"]},
                device_scale_factor=MOBILE_DEVICE["device_scale_factor"],
                user_agent=MOBILE_DEVICE["user_agent"],
                is_mobile=True,
                has_touch=True,
            )
        else:
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2,
            )

        page = await context.new_page()

        # Collect console errors
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(
            {"type": msg.type, "text": msg.text}
        ))

        t0 = time.time()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"⚠️  Page load: {e}", file=sys.stderr)
        load_time = round(time.time() - t0, 2)

        # Let animations settle
        await page.wait_for_timeout(2000)

        # Full page screenshot
        screenshot = await page.screenshot(full_page=True, type="png")
        screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")

        # Viewport-only screenshot (above the fold)
        viewport_ss = await page.screenshot(full_page=False, type="png")
        viewport_b64 = base64.b64encode(viewport_ss).decode("utf-8")

        # Accessibility tree
        try:
            accessibility = await page.accessibility.snapshot()
        except Exception:
            accessibility = None

        # Page metadata + stats
        stats = await page.evaluate("""() => {
            const getMeta = (name, attr='name') =>
                document.querySelector(`meta[${attr}="${name}"]`)?.getAttribute('content') || null;
            return {
                url: window.location.href,
                title: document.title,
                metaDescription: getMeta('description'),
                viewport: getMeta('viewport'),
                ogTitle: getMeta('og:title', 'property'),
                ogDescription: getMeta('og:description', 'property'),
                ogImage: getMeta('og:image', 'property'),
                ogUrl: getMeta('og:url', 'property'),
                twitterCard: getMeta('twitter:card'),
                canonical: document.querySelector('link[rel="canonical"]')?.href || null,
                h1s: Array.from(document.querySelectorAll('h1')).map(h => h.innerText.trim()).slice(0, 5),
                h2s: Array.from(document.querySelectorAll('h2')).map(h => h.innerText.trim()).slice(0, 10),
                imgCount: document.querySelectorAll('img').length,
                imgsNoAlt: document.querySelectorAll('img:not([alt]), img[alt=""]').length,
                linkCount: document.querySelectorAll('a').length,
                formCount: document.querySelectorAll('form').length,
                buttonCount: document.querySelectorAll('button, [role="button"], input[type="submit"]').length,
                scriptCount: document.querySelectorAll('script').length,
                wordCount: document.body?.innerText?.split(/\\s+/).filter(Boolean).length || 0,
                schemaMarkup: !!document.querySelector('script[type="application/ld+json"]'),
            };
        }""")

        stats["loadTime"] = load_time

        # Console errors only
        errors = [m for m in console_msgs if m["type"] in ("error", "warning")]

        await browser.close()

        return {
            "screenshot_b64": screenshot_b64,
            "viewport_b64": viewport_b64,
            "accessibility": accessibility,
            "stats": stats,
            "console_errors": errors[:20],
        }


async def analyze(capture: dict, model: str = DEFAULT_MODEL, api_key: str = None):
    """Send captured data to OpenRouter for AI analysis."""
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Set OPENROUTER_API_KEY env var or pass --api-key")

    s = capture["stats"]

    # Build context text
    lines = [
        f"**URL:** {s['url']}",
        f"**Title:** {s['title'] or '(none)'}",
        f"**Load Time:** {s['loadTime']}s",
        f"**Words:** {s['wordCount']} | **Images:** {s['imgCount']} (no alt: {s['imgsNoAlt']}) | **Links:** {s['linkCount']} | **Forms:** {s['formCount']} | **Buttons:** {s['buttonCount']}",
        f"**Scripts:** {s['scriptCount']}",
        f"**H1:** {', '.join(s['h1s']) if s['h1s'] else '❌ NONE'}",
        f"**H2s:** {', '.join(s['h2s'][:5]) if s['h2s'] else '❌ NONE'}",
        "",
        "**Meta Tags:**",
        f"- description: {s['metaDescription'] or '❌ MISSING'}",
        f"- viewport: {'✅' if s['viewport'] else '❌ MISSING'}",
        f"- og:title: {s['ogTitle'] or '❌ MISSING'}",
        f"- og:description: {s['ogDescription'] or '❌ MISSING'}",
        f"- og:image: {s['ogImage'] or '❌ MISSING'}",
        f"- og:url: {s['ogUrl'] or '❌ MISSING'}",
        f"- twitter:card: {s['twitterCard'] or '❌ MISSING'}",
        f"- canonical: {s['canonical'] or '❌ MISSING'}",
        f"- schema/JSON-LD: {'✅' if s['schemaMarkup'] else '❌ MISSING'}",
    ]

    if capture["console_errors"]:
        lines.append(f"\n**Console Errors ({len(capture['console_errors'])}):**")
        for e in capture["console_errors"][:10]:
            lines.append(f"  [{e['type']}] {e['text'][:200]}")

    if capture["accessibility"]:
        acc_json = json.dumps(capture["accessibility"], indent=2)[:3000]
        lines.append(f"\n**Accessibility Tree (truncated):**\n```json\n{acc_json}\n```")

    context = "\n".join(lines)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": f"Analyze this website:\n\n{context}\n\nAbove-the-fold screenshot:"},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{capture['viewport_b64']}"
            }},
        ]},
    ]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/M4ST3R-C0NTR0L/CybrScan",
                "X-Title": "CybrScan",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def scan(url: str, model: str = DEFAULT_MODEL, api_key: str = None,
               save_dir: str = None, mobile: bool = False,
               width: int = 1280, height: int = 800):
    """Full pipeline: capture → analyze → report."""
    mode = "📱 Mobile" if mobile else "🖥️  Desktop"
    print(f"🔍 CybrScan — {mode}")
    print(f"🌐 {url}")
    print(f"🤖 Model: {model}")
    print(f"📸 Capturing...")

    capture = await capture_page(url, width=width, height=height, mobile=mobile)

    s = capture["stats"]
    print(f"✅ Loaded in {s['loadTime']}s — {s['wordCount']} words, {s['imgCount']} imgs, {s['linkCount']} links")

    if capture["console_errors"]:
        print(f"⚠️  {len(capture['console_errors'])} console errors/warnings")

    # Save artifacts
    if save_dir:
        out = Path(save_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "screenshot-full.png").write_bytes(base64.b64decode(capture["screenshot_b64"]))
        (out / "screenshot-viewport.png").write_bytes(base64.b64decode(capture["viewport_b64"]))
        (out / "stats.json").write_text(json.dumps(s, indent=2))
        if capture["accessibility"]:
            (out / "accessibility.json").write_text(json.dumps(capture["accessibility"], indent=2))
        print(f"💾 Saved to {out}/")

    print(f"🧠 Analyzing...")
    analysis = await analyze(capture, model=model, api_key=api_key)

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"🔍 CybrScan Report: {url}")
    print(f"🤖 Model: {model} | {mode}")
    print(f"{sep}\n")
    print(analysis)

    if save_dir:
        report = Path(save_dir) / "report.md"
        report.write_text(
            f"# CybrScan Report\n\n"
            f"**URL:** {url}\n"
            f"**Model:** {model}\n"
            f"**Mode:** {mode}\n"
            f"**Load Time:** {s['loadTime']}s\n\n"
            f"---\n\n{analysis}\n"
        )
        print(f"\n💾 Report: {report}")

    return analysis


def main():
    parser = argparse.ArgumentParser(
        description="🔍 CybrScan — AI-powered website inspector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 cybrscan.py https://example.com
  python3 cybrscan.py https://mysite.dev --model google/gemini-3-flash-preview
  python3 cybrscan.py https://mysite.dev --save ./reports/mysite
  python3 cybrscan.py https://mysite.dev --mobile
  python3 cybrscan.py https://mysite.dev --model google/gemini-2.5-flash-lite  (cheapest)

Models (via OpenRouter):
  google/gemini-2.5-flash          $0.30/$2.50 per 1M tokens (default, best value)
  google/gemini-2.5-flash-lite     $0.10/$0.40 per 1M tokens (cheapest)
  google/gemini-3-flash-preview    $0.50/$3.00 per 1M tokens (newest)
  google/gemini-2.5-pro            $1.25/$10   per 1M tokens (best quality)
  openai/gpt-4o                    $2.50/$10   per 1M tokens (strong vision)
        """,
    )
    parser.add_argument("url", help="URL to scan")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"OpenRouter model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--api-key", "-k", help="OpenRouter API key (or set OPENROUTER_API_KEY)")
    parser.add_argument("--save", "-s", help="Save screenshots + report to this directory")
    parser.add_argument("--mobile", action="store_true", help="Simulate iPhone viewport")
    parser.add_argument("--width", type=int, default=1280, help="Desktop viewport width")
    parser.add_argument("--height", type=int, default=800, help="Desktop viewport height")

    args = parser.parse_args()

    asyncio.run(scan(
        url=args.url,
        model=args.model,
        api_key=args.api_key,
        save_dir=args.save,
        mobile=args.mobile,
        width=args.width,
        height=args.height,
    ))


if __name__ == "__main__":
    main()
