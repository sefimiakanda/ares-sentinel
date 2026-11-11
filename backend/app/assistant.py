"""L'assistant scientifique.

IMPORTANT : ce n'est PAS un LLM. C'est un assistant « à règles » :
il lit la question, repère des mots-clés, puis construit sa réponse
UNIQUEMENT à partir des chiffres calculés sur les données de Curiosity.

Avantage : il ne peut pas inventer. S'il n'a pas la donnée, il le dit.
Chaque réponse a toujours la même forme : Constat / Preuves / Limites.
"""

import re

from . import pipeline

NOMS_FACTEURS = {
    "froid": "le froid",
    "amplitude": "l'écart de température jour/nuit",
    "pression": "la variation de pression",
    "anomalie": "le côté inhabituel de la journée",
}

HORS_PERIMETRE = ["radiation", "oxygène", "oxygene", "vent", "combinaison", "poussière fine", "survie", "survivre"]

EXEMPLES = [
    "Puis-je sortir aujourd'hui ?",
    "Pourquoi le sol 4780 est-il rouge ?",
    "Quelles sont les plus grosses anomalies ?",
    "Les tempêtes de poussière rendent-elles les sorties plus risquées ?",
    "Quelle est la température la plus froide mesurée ?",
]

LIMITE_GENERALE = (
    "Données d'un seul site (cratère Gale, rover Curiosity). "
    "L'indice est pédagogique et n'est pas un seuil de sécurité officiel de la NASA."
)


def _reponse(constat, preuves, limites=None, sol=None):
    return {
        "constat": constat,
        "preuves": preuves,
        "limites": limites or LIMITE_GENERALE,
        "source": "NASA Mars Weather Service / Curiosity REMS (cache local)",
        "sol_cite": sol,
        "type": "assistant à règles (pas un LLM)",
    }


def _trouver_sol(question: str):
    m = re.search(r"sol\s*(\d+)", question.lower())
    return int(m.group(1)) if m else None


def _facteur_principal(l):
    """Le facteur qui pèse le plus dans l'indice de ce jour."""
    poids = {"froid": 0.35, "amplitude": 0.25, "pression": 0.20, "anomalie": 0.20}
    contributions = {k: poids[k] * (l[f"note_{k}"] or 0) for k in poids}
    return max(contributions, key=contributions.get)


def _repondre_sortie(sol, sol_par_defaut=False):
    l = pipeline.ligne(sol)
    if l is None:
        return _reponse(f"Le sol {sol} n'existe pas dans les données.", [], sol=sol)
    if l["indice"] is None:
        return _reponse(
            f"Pas de verdict pour le sol {sol} : des mesures manquent.",
            ["Il manque au moins une mesure (température ou pression)."],
            sol=sol,
        )
    v = pipeline.verdict_pour(l["indice"])
    principal = _facteur_principal(l)
    preuves = [
        f"Sol {sol} ({l['terrestrial_date']}) : indice {l['indice']}/100, verdict {v['code']}.",
        f"Température : min {l['air_temp_min_c']} °C, max {l['air_temp_max_c']} °C (écart {l['temp_amplitude_c']} °C).",
        f"Pression : {l['pressure_pa']} Pa (variation de {l['variation_pression']:.1f} Pa depuis le dernier sol mesuré).",
        f"Facteur le plus lourd : {NOMS_FACTEURS[principal]} (note {l['note_' + principal]}/100).",
    ]
    if l["est_anomalie"]:
        preuves.append(f"Ce jour est détecté comme anomalie : {l['raison_anomalie']}.")
    if sol_par_defaut:
        preuves.append(
            f"« Aujourd'hui » = le dernier sol présent dans les données (sol {sol}, {l['terrestrial_date']}), "
            "pas la date réelle du jour : il n'y a pas de flux en direct."
        )
    return _reponse(f"{v['texte']} (sol {sol}, indice {l['indice']}/100).", preuves, sol=sol)


def _repondre_anomalies():
    df = pipeline.tableau()
    top = df[df["est_anomalie"]].sort_values("anomalie_intensite", ascending=False).head(3)
    total = int(df["est_anomalie"].sum())
    preuves = [
        f"Sol {int(r.sol)} ({r.terrestrial_date}) : intensité {r.anomalie_intensite}/100, {r.raison_anomalie}."
        for r in top.itertuples()
    ]
    return _reponse(
        f"Le modèle (Isolation Forest) a repéré {total} jours anormaux. Voici les 3 plus marqués.",
        preuves,
        "Une anomalie est un jour inhabituel, pas forcément un jour dangereux. "
        "Le modèle ne connaît que 4 mesures : température min, max, écart, pression.",
        sol=int(top.iloc[0]["sol"]) if len(top) else None,
    )


def _repondre_saison():
    df = pipeline.tableau().dropna(subset=["indice"])
    poussiere = df[df["saison_poussiere"]]
    autre = df[~df["saison_poussiere"]]
    m1, m2 = poussiere["indice"].mean(), autre["indice"].mean()
    r1 = (poussiere["verdict"] == "ROUGE").mean() * 100
    r2 = (autre["verdict"] == "ROUGE").mean() * 100
    if m1 > m2 and r1 > r2:
        constat = "Dans ces données, la saison des tempêtes de poussière rend les sorties plus difficiles."
    elif m1 <= m2 and r1 <= r2:
        constat = "Dans ces données, la saison des tempêtes de poussière ne rend pas les sorties plus difficiles."
    else:
        constat = (
            "Résultat mitigé : la saison des tempêtes ne change pas clairement l'indice moyen, "
            "mais elle compte plus de jours rouges." if r1 > r2 else
            "Résultat mitigé : la saison des tempêtes a un indice moyen plus haut, mais moins de jours rouges."
        )
    return _reponse(
        constat,
        [
            f"Saison poussière (Ls 180°-320°) : indice moyen {m1:.1f}, {r1:.1f} % de jours rouges ({len(poussiere)} sols).",
            f"Autres saisons : indice moyen {m2:.1f}, {r2:.1f} % de jours rouges ({len(autre)} sols).",
        ],
        "On ne mesure pas directement la poussière ici (pas d'opacité). "
        "On utilise seulement la saison. Une tempête globale précise pourrait changer la conclusion.",
    )


def _repondre_temperature():
    df = pipeline.tableau()
    froid = df.loc[df["air_temp_min_c"].idxmin()]
    chaud = df.loc[df["air_temp_max_c"].idxmax()]
    return _reponse(
        "Mars est toujours très froide, même au meilleur moment de la journée.",
        [
            f"Minimum mesuré : {froid['air_temp_min_c']:.0f} °C (sol {int(froid['sol'])}).",
            f"Maximum mesuré : {chaud['air_temp_max_c']:.0f} °C (sol {int(chaud['sol'])}).",
            f"Moyenne des minimums : {df['air_temp_min_c'].mean():.1f} °C ; moyenne des maximums : {df['air_temp_max_c'].mean():.1f} °C.",
        ],
        "Ce sont des températures de l'air mesurées par le rover. Elles ne donnent pas la température ressentie dans une combinaison.",
        sol=int(froid["sol"]),
    )


def _repondre_pression():
    df = pipeline.tableau()
    haut = df.loc[df["pressure_pa"].idxmax()]
    bas = df.loc[df["pressure_pa"].idxmin()]
    return _reponse(
        "La pression à la surface de Mars est plus de 100 fois plus faible que sur Terre.",
        [
            f"Pression moyenne : {df['pressure_pa'].mean():.0f} Pa (Terre : environ 101 325 Pa).",
            f"Maximum : {haut['pressure_pa']:.0f} Pa (sol {int(haut['sol'])}) ; minimum : {bas['pressure_pa']:.0f} Pa (sol {int(bas['sol'])}).",
        ],
        sol=int(haut["sol"]),
    )


def _refus(sujet):
    return _reponse(
        f"Je ne peux pas répondre sur « {sujet} » : cette variable n'est pas dans mes données.",
        ["Je ne connais que : température min/max, pression et saison (Ls)."],
        "Je préfère dire que je ne sais pas plutôt qu'inventer une réponse. "
        "Pour ce sujet, il faudrait d'autres instruments (radiomètre, anémomètre...).",
    )


def repondre_regles(question: str, sol_choisi=None) -> dict:
    q = question.lower().strip()
    if not q:
        return _reponse("Pose-moi une question sur Mars.", [f"Exemple : {EXEMPLES[0]}"])

    for mot in HORS_PERIMETRE:
        if mot in q:
            return _refus(mot)

    sol_dans_question = _trouver_sol(q)
    sol = sol_dans_question or sol_choisi or pipeline.dernier_sol_disponible()

    if "anomal" in q:
        return _repondre_anomalies()
    if any(m in q for m in ["tempête", "tempete", "poussière", "poussiere", "saison"]):
        return _repondre_saison()
    if "pression" in q:
        return _repondre_pression()
    if any(m in q for m in ["froid", "température", "temperature", "chaud"]):
        return _repondre_temperature()
    if sol_dans_question or any(
        m in q for m in ["sortir", "sortie", "sûr", "sur ?", "sécur", "secur", "aujourd", "pourquoi", "indice", "verdict", "rouge", "orange", "vert", "risque"]
    ):
        return _repondre_sortie(sol, sol_par_defaut=not (sol_dans_question or sol_choisi))

    return _reponse(
        "Je n'ai pas compris la question.",
        ["Je peux répondre sur : la sortie du jour, un sol précis, les anomalies, la saison des tempêtes, la température, la pression.",
         "Exemples : " + " | ".join(EXEMPLES[:3])],
    )


def repondre(question: str, sol_choisi=None) -> dict:
    """Point d'entrée : LLM local (Ollama) s'il est prêt, sinon assistant à règles."""
    from . import llm

    if llm.disponible():
        try:
            return llm.repondre_llm(question, sol_choisi)
        except llm.LLMSansOutil:
            r = repondre_regles(question, sol_choisi)
            r["type"] = "assistant à règles (secours : le LLM n'a consulté aucune donnée)"
            return r
        except Exception as e:  # Ollama a planté, timeout, réponse bizarre... : on bascule sur le secours
            print(f"[assistant] LLM indisponible ({type(e).__name__}: {e}) -> mode règles")
            r = repondre_regles(question, sol_choisi)
            r["type"] = "assistant à règles (secours : le LLM n'a pas répondu)"
            return r
    return repondre_regles(question, sol_choisi)


def etat_llm() -> dict:
    """Pour l'affichage : quel assistant est actif et pourquoi."""
    from . import llm

    e = llm.etat()
    return {"assistant": "ollama" if e["pret"] else "regles", "assistant_modele": e["modele"], "assistant_raison": e["raison"]}
