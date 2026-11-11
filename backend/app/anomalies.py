"""Détection d'anomalies avec le machine learning (Isolation Forest).

Principe : l'Isolation Forest apprend à quoi ressemble un jour « normal »
sur Mars (température min, max, écart, pression). Les jours qui se
distinguent beaucoup des autres sont isolés très vite par l'algorithme :
on les appelle des anomalies.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

COLONNES = ["air_temp_min_c", "air_temp_max_c", "temp_amplitude_c", "pressure_pa"]
NOMS_LISIBLES = {
    "air_temp_min_c": "température minimale",
    "air_temp_max_c": "température maximale",
    "temp_amplitude_c": "écart de température jour/nuit",
    "pressure_pa": "pression",
}


def detecter(tableau: pd.DataFrame, contamination: float = 0.03) -> pd.DataFrame:
    """Ajoute 3 colonnes au tableau :
    - anomalie_intensite : 0 (très normal) à 100 (très étrange)
    - est_anomalie       : True si le jour est jugé anormal
    - raison_anomalie    : la variable la plus éloignée de la normale
    """
    tableau = tableau.copy()
    tableau["anomalie_intensite"] = np.nan
    tableau["est_anomalie"] = False
    tableau["raison_anomalie"] = ""

    complets = tableau.dropna(subset=COLONNES)
    if len(complets) < 50:
        return tableau  # pas assez de données pour apprendre

    X = complets[COLONNES].to_numpy(dtype=float)
    modele = IsolationForest(n_estimators=100, contamination=contamination, random_state=42)
    modele.fit(X)

    scores = modele.score_samples(X)  # plus c'est bas, plus c'est anormal
    intensite = (scores.max() - scores) / (scores.max() - scores.min()) * 100

    # Raison : quelle variable s'éloigne le plus de la médiane ? (z-score robuste)
    mediane = np.median(X, axis=0)
    mad = np.median(np.abs(X - mediane), axis=0)
    mad[mad == 0] = 1e-6
    z = 0.6745 * (X - mediane) / mad
    indice_pire = np.abs(z).argmax(axis=1)
    raisons = []
    for i, k in enumerate(indice_pire):
        nom = NOMS_LISIBLES[COLONNES[k]]
        sens = "trop haute" if z[i, k] > 0 else "trop basse"
        if COLONNES[k] == "temp_amplitude_c":
            sens = "trop grand" if z[i, k] > 0 else "trop petit"
        raisons.append(f"{nom} {sens}")

    tableau.loc[complets.index, "anomalie_intensite"] = np.round(intensite, 1)
    tableau.loc[complets.index, "est_anomalie"] = modele.predict(X) == -1
    tableau.loc[complets.index, "raison_anomalie"] = raisons
    return tableau
