"""Charge les secrets depuis un fichier .env (jamais envoyé sur GitHub).

Le fichier .env se place dans backend/ et contient des lignes du type :
    GEMINI_API_KEY=ta_cle_ici
Les variables déjà définies par le système (ex : Render) restent prioritaires.
"""

import os
from pathlib import Path

_ICI = Path(__file__).resolve().parent.parent  # dossier backend/


def charger_env():
    for chemin in (_ICI / ".env", _ICI.parent / ".env"):
        if not chemin.is_file():
            continue
        for ligne in chemin.read_text(encoding="utf-8").splitlines():
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            cle, _, valeur = ligne.partition("=")
            os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


charger_env()
