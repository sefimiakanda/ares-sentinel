<p align="center"><img src="docs/screenshots/ares.png" alt="Ares Sentinel logo" width="150"></p>
<h1 align="center">Ares Sentinel</h1>
<p align="center">Mars operational intelligence · NASA data, machine learning, and Google Gemini</p>

[Live project](https://ares-sentinel.onrender.com)

## What it does

Ares Sentinel turns Curiosity REMS observations from Gale Crater into an explorable mission dashboard: risk score, anomaly detection, historical trend, date/sol lookup, and a per-sol visual profile. The score is educational, not a NASA safety threshold.

The science assistant uses **Google Gemini only**. Gemini must call local data tools before answering; unverified replies are rejected. There is no local-model integration or rule-based fallback that could hide a Gemini configuration or service error.

## Run locally

```bash
cd backend
uv sync --dev
# create backend/.env containing GEMINI_API_KEY=your_google_ai_studio_key
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Configure `GEMINI_MODEL` optionally (default: `gemini-2.5-flash`). The health endpoint (`/api/sante`) reports Gemini status; assistant errors are returned explicitly instead of being replaced by local answers.

## Data and methods

- `data/curiosity_rems.csv`: saved NASA Curiosity REMS observations; not a live feed.
- Isolation Forest identifies unusual sols.
- The dashboard lets users select a martian sol or an Earth date; the closest available observation is opened.
- Advanced visualisation combines the full risk timeline with a normalized profile of temperature, pressure, and risk for the selected sol.

## Stack

FastAPI, pandas, scikit-learn, Leaflet, vanilla JavaScript, Google Gemini, Render.
