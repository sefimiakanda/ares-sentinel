"""Assemble tout : lecture du CSV -> anomalies -> indice de risque."""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .anomalies import COLONNES, detecter
from .indice import (
    calculer_indice,
    calculer_seuils,
    construire_reference,
    saison_des_tempetes,
    verdict,
)

CSV = Path(__file__).resolve().parent.parent.parent / "data" / "curiosity_rems.csv"


def construire(chemin_csv=CSV):
    """Retourne (tableau, seuils) : le tableau complet et les seuils de verdict."""
    df = pd.read_csv(chemin_csv)
    df = df.sort_values("sol").drop_duplicates("sol").reset_index(drop=True)

    # Variation de pression d'un sol à l'autre (en Pa par sol)
    valides = df.dropna(subset=["pressure_pa"])
    ecart_sol = valides["sol"].diff().clip(lower=1)
    variation = (valides["pressure_pa"].diff().abs() / ecart_sol).fillna(0)
    df["variation_pression"] = variation.reindex(df.index)

    df = detecter(df)

    # On ne calcule l'indice que si toutes les mesures utiles existent
    complet = df.dropna(subset=COLONNES + ["variation_pression", "anomalie_intensite"])
    ref = construire_reference(
        complet["air_temp_min_c"],
        complet["temp_amplitude_c"],
        complet["variation_pression"],
        complet["anomalie_intensite"],
    )
    total, notes = calculer_indice(
        ref,
        complet["air_temp_min_c"].to_numpy(),
        complet["temp_amplitude_c"].to_numpy(),
        complet["variation_pression"].to_numpy(),
        complet["anomalie_intensite"].to_numpy(),
    )
    df["indice"] = np.nan
    df.loc[complet.index, "indice"] = np.round(total, 1)
    for nom, valeur in notes.items():
        df[f"note_{nom}"] = np.nan
        df.loc[complet.index, f"note_{nom}"] = np.round(valeur, 1)

    seuils = calculer_seuils(df["indice"])
    df["verdict"] = df["indice"].apply(lambda x: verdict(x, seuils)["code"])
    df["saison_poussiere"] = df["solar_longitude_ls"].apply(saison_des_tempetes)
    return df, seuils


@lru_cache(maxsize=1)
def _calcul():
    return construire()


def tableau() -> pd.DataFrame:
    """Le calcul est fait une seule fois puis gardé en mémoire."""
    return _calcul()[0]


def seuils() -> dict:
    return _calcul()[1]


def verdict_pour(indice):
    return verdict(indice, seuils())


def dernier_sol_disponible() -> int:
    df = tableau()
    return int(df.dropna(subset=["indice"])["sol"].iloc[-1])


def ligne(sol: int):
    """Retourne la ligne d'un sol sous forme de dictionnaire propre (ou None)."""
    df = tableau()
    res = df[df["sol"] == sol]
    if res.empty:
        return None
    return nettoyer(res.iloc[0].to_dict())


def nettoyer(d: dict) -> dict:
    """Remplace les NaN par None et convertit les types numpy pour le JSON."""
    propre = {}
    for cle, val in d.items():
        if isinstance(val, (np.bool_, bool)):
            propre[cle] = bool(val)
        elif isinstance(val, (np.floating, float)):
            propre[cle] = None if np.isnan(val) else float(val)
        elif isinstance(val, np.integer):
            propre[cle] = int(val)
        else:
            propre[cle] = val
    return propre
