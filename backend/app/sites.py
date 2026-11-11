"""Les sites martiens affichés sur la carte.

Seul Curiosity (cratère Gale) a de vraies mesures dans ce projet.
Les autres sites sont affichés sur la carte mais sans verdict :
on ne veut pas inventer des données.
"""

SITES = [
    {
        "id": "gale",
        "nom": "Cratère Gale (Curiosity)",
        "lat": -4.59,
        "lon": 137.44,
        "altitude_km": -4.5,
        "donnees_reelles": True,
    },
    {
        "id": "elysium",
        "nom": "Elysium Planitia (InSight)",
        "lat": 4.50,
        "lon": 135.62,
        "altitude_km": -2.6,
        "donnees_reelles": False,
    },
    {
        "id": "jezero",
        "nom": "Cratère Jezero (Perseverance)",
        "lat": 18.38,
        "lon": 77.58,
        "altitude_km": -2.5,
        "donnees_reelles": False,
    },
]
