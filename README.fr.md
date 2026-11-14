<p align="center"><img src="docs/screenshots/ares.png" alt="Logo Ares Sentinel" width="150"></p>
<h1 align="center">Ares Sentinel</h1>
<p align="center">Données NASA · machine learning · OpenRouter</p>

[Projet déployé](https://ares-sentinel.onrender.com)

## Présentation

Explore les données REMS de Curiosity au cratère Gale avec une sélection par sol ou date, la carte de Mars, l’historique de risque, la détection d’anomalies et l’assistant IA. L’indice est pédagogique et ne constitue pas un seuil de sécurité NASA.

L’assistant utilise l’API OpenRouter compatible OpenAI, avec `openrouter/free`. Un appel d’outil est obligatoire avant une réponse : les valeurs citées restent donc ancrées dans les données locales de Curiosity.

## Installation

```bash
cd backend
cp .env.example .env
# renseigner OPENROUTER_API_KEY dans .env
uv sync --dev
uv run uvicorn app.main:app --reload
```

`OPENROUTER_MODEL` est facultatif (`openrouter/free` par défaut). Sur Render, configure `OPENROUTER_API_KEY` comme secret. Le fichier `.env` est exclu de Git.
