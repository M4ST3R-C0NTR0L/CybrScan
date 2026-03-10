# 🔍 CybrScan

**AI-powered website inspector.** Open any site, see it, analyze it, fix it.

CybrScan uses Playwright to open websites like a real browser, captures screenshots and technical data, then sends everything to an AI vision model for deep analysis — design, UX, conversion, SEO, accessibility, and code quality.

## Quick Start

```bash
# Install
pip3 install httpx playwright
python3 -m playwright install chromium

# Scan a site (uses Kimi by default — $0 if you have a subscription)
python3 cybrscan.py https://example.com

# Save screenshots + report
python3 cybrscan.py https://mysite.dev --save ./reports/mysite

# Mobile view (iPhone simulation)
python3 cybrscan.py https://mysite.dev --mobile

# Use OpenRouter instead (any model)
export OPENROUTER_API_KEY=sk-or-v1-your-key
python3 cybrscan.py https://mysite.dev --provider openrouter

# Specific OpenRouter model
python3 cybrscan.py https://mysite.dev -p openrouter -m google/gemini-3-flash-preview

# List recommended models
python3 cybrscan.py --list-models
```

## Providers

### Kimi (Default)
Uses Kimi Code API with vision support. **$0 extra** if you have a Kimi subscription ($39/mo).
- Auto-loads API key from OpenClaw config
- Great quality for website analysis
- 262K context window

### OpenRouter (Any Model)
Access 300+ models via [OpenRouter](https://openrouter.ai). Set `OPENROUTER_API_KEY` or it auto-loads from OpenClaw config.

**Recommended Models:**

| Model | Cost/scan | Quality | Best For |
|-------|-----------|---------|----------|
| `google/gemini-2.5-flash-lite` | ~$0.001 | ⭐⭐⭐ | Bulk scanning, quick checks |
| `google/gemini-2.5-flash` | ~$0.003 | ⭐⭐⭐⭐ | Daily use, best value |
| `google/gemini-3-flash-preview` | ~$0.005 | ⭐⭐⭐⭐⭐ | Newest Google, great detail |
| `google/gemini-3.1-flash-lite-preview` | ~$0.003 | ⭐⭐⭐⭐ | New + cheap |
| `google/gemini-2.5-pro` | ~$0.02 | ⭐⭐⭐⭐⭐ | Deep analysis, client reports |
| `openai/gpt-4o` | ~$0.03 | ⭐⭐⭐⭐⭐ | Best vision overall |

💡 **Our pick:** Start with **Kimi** (free). Use **Gemini 2.5 Flash** via OpenRouter for second opinions. Use **GPT-4o** for client-facing reports.

## What It Analyzes

- **Visual & Design** — layout, spacing, typography, color contrast, visual hierarchy
- **UX & Conversion** — CTAs, navigation, forms, trust signals, user flow
- **Technical** — meta tags, OG tags, console errors, accessibility, performance
- **Content** — copy quality, value proposition, information architecture
- **SEO** — heading structure, schema markup, social sharing tags

Every issue gets a severity rating (🔴 Critical → 💡 Suggestion) and a specific, actionable fix with code snippets.

## Output

Each scan produces:
- Full-page screenshot (PNG)
- Viewport screenshot (above the fold)
- Accessibility tree snapshot (JSON)
- Page stats — words, images, links, forms, meta tags, OG tags, schema (JSON)
- Console errors
- AI analysis report (Markdown)

## How It Works

```
URL → Playwright Browser → Screenshot + DOM + Stats → AI Vision Model → Report
```

1. Opens the page in a real Chromium browser
2. Waits for network idle + animations to settle
3. Captures full-page + viewport screenshots
4. Extracts accessibility tree, meta tags, OG tags, stats
5. Collects console errors/warnings
6. Sends viewport screenshot + all data to AI vision model
7. Returns prioritized findings with severity + fixes

## Requirements

- Python 3.9+
- Chromium (installed via Playwright)
- API key: Kimi Code subscription OR [OpenRouter key](https://openrouter.ai/keys)

## Adding Your Own Provider

Edit the `PROVIDERS` dict in `cybrscan.py`:

```python
PROVIDERS = {
    "my-provider": {
        "url": "https://api.example.com/v1/chat/completions",
        "model": "my-model-id",
        "key_path": ["models", "providers", "my-provider", "apiKey"],  # OpenClaw config path
        "supports_reasoning": False,
        "cost": "$X per scan",
    },
}
```

Any OpenAI-compatible API that supports vision (image_url in messages) will work.

## License

MIT — do whatever you want with it.

## Author

Built by [CybrFlux](https://cybrflux.online).
