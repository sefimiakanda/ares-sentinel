"""Charge les secrets depuis un fichier .env (jamais envoyé sur GitHub).

Le fichier .env se place dans backend/ et contient des lignes du type :
    GEMINI_API_KEY=ta_cle_ici
Les variables déjà définies par le système (ex : Render) restent prioritaires.
"""

import os
from pathlib import Path

_ICI = Path(__file__).resolve().parent.parent  # dossier backend/
FICHIER_ENV_TROUVE = False                      # utile pour le diagnostic affiché dans /api/sante


def charger_env():
    global FICHIER_ENV_TROUVE
    for chemin in (_ICI / ".env", _ICI.parent / ".env"):
        if not chemin.is_file():
            continue
        FICHIER_ENV_TROUVE = True
        # utf-8-sig : accepte aussi les fichiers enregistrés « avec BOM » (fréquent avec le Bloc-notes de Windows)
        for ligne in chemin.read_text(encoding="utf-8-sig").splitlines():
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            cle, _, valeur = ligne.partition("=")
            os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


charger_env()
