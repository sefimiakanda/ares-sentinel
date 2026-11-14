<p align="center"><img src="docs/screenshots/ares.png" alt="Ares Sentinel logo" width="150"></p>
<h1 align="center">Ares Sentinel</h1>
<p align="center">NASA Mars data · machine learning · OpenRouter</p>

[Live project](https://ares-sentinel.onrender.com)

## Overview

Explore Curiosity REMS data from Gale Crater through a sol/date selector, Mars map, risk timeline, anomaly detection, and an AI data assistant. The score is educational and is not a NASA safety threshold.

The assistant uses OpenRouter's OpenAI-compatible API with `openrouter/free`. Tool calling is required before it can answer, so numerical claims remain grounded in local Curiosity data.

## Setup

```bash
cd backend
cp .env.example .env
# Set OPENROUTER_API_KEY in .env
uv sync --dev
uv run uvicorn app.main:app --reload
```

`OPENROUTER_MODEL` is optional and defaults to `openrouter/free`. On Render, set `OPENROUTER_API_KEY` as a secret environment variable. `.env` is gitignored.
