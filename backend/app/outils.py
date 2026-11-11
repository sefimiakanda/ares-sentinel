"""Les « outils » que le LLM peut appeler.

Le LLM ne connaît PAS les données de Mars. Quand il a besoin d'un chiffre,
il appelle un de ces outils, et c'est notre code Python (donc nos vraies
données) qui répond. Il ne peut citer que ce que ces fonctions renvoient.
"""

from . import pipeline

# Description des outils pour le LLM (format JSON Schema)
DEFINITIONS = [
    {
        "name": "obtenir_sortie",
        "description": (
            "Donne le verdict de sortie (VERT/ORANGE/ROUGE), l'indice de risque 0-100, les mesures "
            "(températures, pression), les 4 notes détaillées et l'éventuelle anomalie pour UN jour martien (sol). "
            "Sans argument, renvoie le dernier sol disponible dans les données."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"sol": {"type": "integer", "description": "Numéro du sol. Optionnel."}},
            "required": [],
        },
    },
    {
        "name": "lister_anomalies",
        "description": "Liste les jours les plus anormaux détectés par le modèle Isolation Forest (du plus anormal au moins anormal).",
        "input_schema": {
            "type": "object",
            "properties": {"limite": {"type": "integer", "description": "Nombre de jours à renvoyer (1 à 10)."}},
            "required": [],
        },
    },
    {
        "name": "comparer_saisons",
        "description": "Compare l'indice moyen et la part de jours rouges entre la saison des tempêtes de poussière (Ls 180-320) et le reste de l'année.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "statistiques_globales",
        "description": "Statistiques sur tout l'historique : records de température, pression, nombre de sols, répartition des verdicts, seuils orange/rouge.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def obtenir_sortie(sol=None):
    sol = sol or pipeline.dernier_sol_disponible()
    l = pipeline.ligne(int(sol))
    if l is None:
        return {"erreur": f"Le sol {sol} n'existe pas dans les données."}
    if l["indice"] is None:
        return {"sol": sol, "date": l["terrestrial_date"], "erreur": "Mesures manquantes : aucun verdict possible."}
    return {
        "sol": int(sol),
        "date": l["terrestrial_date"],
        "est_le_dernier_sol_des_donnees": int(sol) == pipeline.dernier_sol_disponible(),
        "saison_martienne": l["martian_season"],
        "saison_poussiere": l["saison_poussiere"],
        "temp_min_c": l["air_temp_min_c"],
        "temp_max_c": l["air_temp_max_c"],
        "ecart_jour_nuit_c": l["temp_amplitude_c"],
        "pression_pa": l["pressure_pa"],
        "variation_pression_pa_par_sol": round(l["variation_pression"], 1),
        "indice": l["indice"],
        "verdict": pipeline.verdict_pour(l["indice"])["code"],
        "notes_sur_100": {
            "froid": l["note_froid"],
            "amplitude": l["note_amplitude"],
            "pression": l["note_pression"],
            "anomalie": l["note_anomalie"],
        },
        "poids": {"froid": 0.35, "amplitude": 0.25, "pression": 0.20, "anomalie": 0.20},
        "est_anomalie": l["est_anomalie"],
        "raison_anomalie": l["raison_anomalie"] or None,
    }


def lister_anomalies(limite=5):
    limite = max(1, min(int(limite or 5), 10))
    df = pipeline.tableau()
    top = df[df["est_anomalie"]].sort_values("anomalie_intensite", ascending=False).head(limite)
    return {
        "total_anomalies": int(df["est_anomalie"].sum()),
        "anomalies": [
            {
                "sol": int(r.sol),
                "date": r.terrestrial_date,
                "intensite_sur_100": r.anomalie_intensite,
                "raison": r.raison_anomalie,
                "verdict": r.verdict,
            }
            for r in top.itertuples()
        ],
        "remarque": "Une anomalie est un jour inhabituel, pas forcément dangereux.",
    }


def comparer_saisons():
    df = pipeline.tableau().dropna(subset=["indice"])
    resultat = {}
    for nom, masque in [("saison_poussiere", df["saison_poussiere"]), ("autres_saisons", ~df["saison_poussiere"])]:
        d = df[masque]
        resultat[nom] = {
            "nb_sols": int(len(d)),
            "indice_moyen": round(float(d["indice"].mean()), 1),
            "pourcentage_jours_rouges": round(float((d["verdict"] == "ROUGE").mean() * 100), 1),
        }
    resultat["remarque"] = "La poussière n'est pas mesurée directement : on utilise seulement la saison (Ls)."
    return resultat


def statistiques_globales():
    df = pipeline.tableau()
    froid = df.loc[df["air_temp_min_c"].idxmin()]
    chaud = df.loc[df["air_temp_max_c"].idxmax()]
    return {
        "site": "Cratère Gale (Curiosity)",
        "nb_sols_dans_les_donnees": int(len(df)),
        "premier_sol": int(df["sol"].iloc[0]),
        "dernier_sol_avec_verdict": pipeline.dernier_sol_disponible(),
        "temp_min_record_c": {"valeur": float(froid["air_temp_min_c"]), "sol": int(froid["sol"])},
        "temp_max_record_c": {"valeur": float(chaud["air_temp_max_c"]), "sol": int(chaud["sol"])},
        "pression_moyenne_pa": round(float(df["pressure_pa"].mean()), 0),
        "pression_terre_pa": 101325,
        "repartition_verdicts": {k: int(v) for k, v in df["verdict"].value_counts().items()},
        "seuil_orange_indice": round(pipeline.seuils()["orange"], 1),
        "seuil_rouge_indice": round(pipeline.seuils()["rouge"], 1),
    }


FONCTIONS = {
    "obtenir_sortie": obtenir_sortie,
    "lister_anomalies": lister_anomalies,
    "comparer_saisons": comparer_saisons,
    "statistiques_globales": statistiques_globales,
}
