"""Ares Sentinel - serveur FastAPI.

Lancer :  uvicorn app.main:app --reload     (depuis le dossier backend/)
Puis ouvrir http://127.0.0.1:8000
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import assistant, config, pipeline  # config charge le fichier backend/.env
from .sites import SITES

app = FastAPI(title="Ares Sentinel", version="1.0.0")

FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"


class Question(BaseModel):
    question: str
    sol: int | None = None


def _detail_sol(sol: int) -> dict:
    l = pipeline.ligne(sol)
    if l is None:
        raise HTTPException(status_code=404, detail=f"Sol {sol} introuvable")
    v = pipeline.verdict_pour(l["indice"])
    facteurs = None
    if l["indice"] is not None:
        facteurs = {
            "froid": {"note": l["note_froid"], "poids": 0.35, "valeur": f"min {l['air_temp_min_c']} °C"},
            "amplitude": {"note": l["note_amplitude"], "poids": 0.25, "valeur": f"écart {l['temp_amplitude_c']} °C"},
            "pression": {"note": l["note_pression"], "poids": 0.20, "valeur": f"{l['variation_pression']:.1f} Pa/sol"},
            "anomalie": {"note": l["note_anomalie"], "poids": 0.20, "valeur": f"intensité {l['anomalie_intensite']}/100"},
        }
    return {
        "sol": sol,
        "date": l["terrestrial_date"],
        "saison": l["martian_season"],
        "ls": l["solar_longitude_ls"],
        "saison_poussiere": l["saison_poussiere"],
        "mesures": {
            "temp_min_c": l["air_temp_min_c"],
            "temp_max_c": l["air_temp_max_c"],
            "amplitude_c": l["temp_amplitude_c"],
            "pression_pa": l["pressure_pa"],
        },
        "indice": l["indice"],
        "verdict": v,
        "facteurs": facteurs,
        "est_anomalie": l["est_anomalie"],
        "raison_anomalie": l["raison_anomalie"] or None,
        "avertissement": "Indice pédagogique relatif à l'historique de Curiosity. Pas un seuil de sécurité NASA.",
    }


@app.get("/api/sante")
def sante():
    df = pipeline.tableau()
    return {
        "statut": "OK",
        "sols_charges": len(df),
        "dernier_sol": pipeline.dernier_sol_disponible(),
        **assistant.etat_llm(),
    }


@app.get("/api/carte")
def carte(sol: int | None = None):
    """Les sites de la carte. Seul Gale a un verdict (vraies données)."""
    sol = sol or pipeline.dernier_sol_disponible()
    resultat = []
    for site in SITES:
        item = dict(site)
        if site["donnees_reelles"]:
            d = _detail_sol(sol)
            item["verdict"] = d["verdict"]
            item["indice"] = d["indice"]
            item["sol"] = sol
        else:
            item["verdict"] = {"code": "INCONNU", "couleur": "gris", "texte": "Pas de données dans cette version"}
            item["indice"] = None
        resultat.append(item)
    return {"sol": sol, "sites": resultat}


@app.get("/api/sortie/{sol}")
def sortie(sol: int):
    return _detail_sol(sol)


@app.get("/api/serie")
def serie():
    """L'indice de tous les sols, pour le graphique."""
    df = pipeline.tableau()
    return {
        "seuils": pipeline.seuils(),
        "points": [
            {"sol": int(r.sol), "indice": None if r.indice != r.indice else r.indice, "anomalie": bool(r.est_anomalie)}
            for r in df.itertuples()
        ],
    }


@app.get("/api/anomalies")
def anomalies(limite: int = 20):
    df = pipeline.tableau()
    top = df[df["est_anomalie"]].sort_values("anomalie_intensite", ascending=False).head(max(1, min(limite, 100)))
    return {
        "total": int(df["est_anomalie"].sum()),
        "anomalies": [
            {
                "sol": int(r.sol),
                "date": r.terrestrial_date,
                "intensite": r.anomalie_intensite,
                "raison": r.raison_anomalie,
                "indice": None if r.indice != r.indice else r.indice,
                "verdict": r.verdict,
            }
            for r in top.itertuples()
        ],
    }


@app.post("/api/assistant")
def poser_question(q: Question):
    return assistant.repondre(q.question, q.sol)


@app.get("/api/exemples")
def exemples():
    return {"exemples": assistant.EXEMPLES}


# Le frontend (HTML/CSS/JS) est servi par le même serveur
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/")
def accueil():
    return FileResponse(FRONTEND / "index.html")
