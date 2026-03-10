# 🔍 CybrScan

**AI-powered website inspector.** Open any site, see it, analyze it, fix it.

CybrScan uses Playwright to open websites like a real browser, captures screenshots and technical data, then sends everything to an AI vision model for deep analysis — design, UX, conversion, SEO, accessibility, and code quality.

Works with any LLM via [OpenRouter](https://openrouter.ai). Default: Gemini 2.5 Flash (~$0.003 per scan).

## Quick Start

```bash
# Install
pip3 install httpx playwright
python3 -m playwright install chromium

# Set your OpenRouter key
export OPENROUTER_API_KEY=sk-or-v1-your-key

# Scan a site
python3 cybrscan.py https://example.com

# Save screenshots + report
python3 cybrscan.py https://mysite.dev --save ./reports/mysite

# Mobile view
python3 cybrscan.py https://mysite.dev --mobile

# Use a different model
python3 cybrscan.py https://mysite.dev --model google/gemini-3-flash-preview
```

## What It Analyzes

- **Visual & Design** — layout, spacing, typography, color contrast, visual hierarchy
- **UX & Conversion** — CTAs, navigation, forms, trust signals, user flow
- **Technical** — meta tags, OG tags, console errors, accessibility, performance
- **Content** — copy quality, value proposition, information architecture

Every issue gets a severity rating and a specific, actionable fix.

## Models (via OpenRouter)

| Model | Cost/scan | Quality | Speed |
|-------|-----------|---------|-------|
| `google/gemini-2.5-flash` | ~$0.003 | ⭐⭐⭐⭐ | Fast |
| `google/gemini-2.5-flash-lite` | ~$0.001 | ⭐⭐⭐ | Fastest |
| `google/gemini-3-flash-preview` | ~$0.005 | ⭐⭐⭐⭐⭐ | Fast |
| `google/gemini-2.5-pro` | ~$0.02 | ⭐⭐⭐⭐⭐ | Slower |
| `openai/gpt-4o` | ~$0.03 | ⭐⭐⭐⭐⭐ | Medium |

Default is Gemini 2.5 Flash — best balance of quality, speed, and cost.

## Output

Each scan produces:
- Full-page screenshot (PNG)
- Viewport screenshot (above the fold)
- Accessibility tree snapshot
- Page stats (word count, images, links, forms, meta tags, OG tags, schema)
- Console errors
- AI analysis report (Markdown)

## Requirements

- Python 3.9+
- Chromium (installed via Playwright)
- OpenRouter API key ([get one free](https://openrouter.ai))

## License

MIT — do whatever you want with it.

## Author

Built by [CybrFlux](https://cybrflux.online).
