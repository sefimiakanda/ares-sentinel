"""L'indice de risque de sortie (0 = jour facile, 100 = jour très difficile).

Idée simple : pour chaque jour martien (« sol »), on regarde 4 choses qui
rendent une sortie plus difficile. Pour chacune, on calcule un RANG :

    « ce jour est plus difficile que X % des jours déjà observés »

Cela donne 4 notes de 0 à 100, puis on fait une moyenne pondérée :

    indice = 0.35*froid + 0.25*amplitude + 0.20*pression + 0.20*anomalie

Le verdict dépend de la place de l'indice dans l'historique :
    VERT   : parmi les 70 % de jours les plus faciles
    ORANGE : entre les 70 % et les 95 %
    ROUGE  : parmi les 5 % de jours les plus difficiles

ATTENTION : c'est un indice pédagogique, relatif à l'historique de Curiosity.
Ce n'est PAS un seuil de sécurité officiel de la NASA. Sur Mars, même un jour
« vert » reste extrêmement dur (il fait toujours bien en dessous de 0 °C).
"""

import numpy as np

# Poids des 4 facteurs (la somme fait 1)
POIDS = {"froid": 0.35, "amplitude": 0.25, "pression": 0.20, "anomalie": 0.20}

# Quels jours sont classés orange / rouge (percentiles de l'indice)
PERCENTILE_ORANGE = 70
PERCENTILE_ROUGE = 95


def rang(valeurs_reference, x):
    """Pourcentage de jours de référence strictement plus faciles que x (0 à 100)."""
    ref = np.sort(np.asarray(valeurs_reference, dtype=float))
    return np.searchsorted(ref, x, side="left") / len(ref) * 100.0


def construire_reference(temp_min, amplitude, variation_pression, intensite_anomalie):
    """Garde en mémoire l'historique qui sert de comparaison."""
    return {
        "froid": np.sort(-np.asarray(temp_min, dtype=float)),  # plus froid = plus dur
        "amplitude": np.sort(np.asarray(amplitude, dtype=float)),
        "pression": np.sort(np.asarray(variation_pression, dtype=float)),
        "anomalie": np.sort(np.asarray(intensite_anomalie, dtype=float)),
    }


def calculer_indice(ref, temp_min, amplitude, variation_pression, intensite_anomalie):
    """Calcule l'indice. Marche avec un nombre seul ou avec des tableaux numpy."""
    notes = {
        "froid": rang(ref["froid"], -np.asarray(temp_min, dtype=float)),
        "amplitude": rang(ref["amplitude"], amplitude),
        "pression": rang(ref["pression"], variation_pression),
        "anomalie": rang(ref["anomalie"], intensite_anomalie),
    }
    total = sum(POIDS[nom] * note for nom, note in notes.items())
    return total, notes


def calculer_seuils(indices):
    """Les deux seuils (orange, rouge) déduits de l'historique des indices."""
    indices = np.asarray(indices, dtype=float)
    indices = indices[~np.isnan(indices)]
    return {
        "orange": float(np.percentile(indices, PERCENTILE_ORANGE)),
        "rouge": float(np.percentile(indices, PERCENTILE_ROUGE)),
    }


def verdict(indice, seuils):
    """Transforme l'indice en verdict lisible."""
    if indice is None or np.isnan(indice):
        return {"code": "INCONNU", "couleur": "gris", "texte": "Pas assez de mesures pour décider"}
    if indice < seuils["orange"]:
        return {"code": "VERT", "couleur": "vert", "texte": "Sortie possible"}
    if indice < seuils["rouge"]:
        return {"code": "ORANGE", "couleur": "orange", "texte": "Sortie avec prudence"}
    return {"code": "ROUGE", "couleur": "rouge", "texte": "Sortie déconseillée"}


def saison_des_tempetes(ls):
    """Entre Ls 180° et 320°, Mars est dans sa saison de tempêtes de poussière."""
    return ls is not None and not np.isnan(ls) and 180 <= (ls % 360) <= 320
