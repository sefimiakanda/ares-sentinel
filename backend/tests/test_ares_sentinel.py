"""Tests simples. Lancer avec :  pytest   (depuis le dossier backend/)"""

import json
import os
from types import SimpleNamespace

import numpy as np
import pytest

os.environ["LLM_PROVIDER"] = "ollama"      # tests déterministes, même si tu as un .env avec une clé
os.environ.pop("GEMINI_API_KEY", None)

from app import assistant, llm, outils, pipeline
from app.indice import construire_reference, calculer_indice, rang, verdict


def test_rang_donne_un_pourcentage():
    ref = [1, 2, 3, 4]
    assert rang(ref, 0) == 0      # plus petit que tout le monde
    assert rang(ref, 3) == 50     # 2 valeurs sur 4 sont strictement plus petites
    assert rang(ref, 99) == 100


def test_indice_entre_0_et_100():
    df = pipeline.tableau().dropna(subset=["indice"])
    assert df["indice"].between(0, 100).all()


def test_les_poids_font_1():
    from app.indice import POIDS
    assert abs(sum(POIDS.values()) - 1.0) < 1e-9


def test_verdict_respecte_les_seuils():
    seuils = {"orange": 50, "rouge": 70}
    assert verdict(10, seuils)["code"] == "VERT"
    assert verdict(60, seuils)["code"] == "ORANGE"
    assert verdict(90, seuils)["code"] == "ROUGE"
    assert verdict(float("nan"), seuils)["code"] == "INCONNU"


def test_pas_de_verdict_sans_mesures():
    """Si une mesure manque, on ne doit pas inventer d'indice."""
    df = pipeline.tableau()
    manquants = df[df["air_temp_min_c"].isna() | df["pressure_pa"].isna()]
    assert len(manquants) > 0
    assert manquants["indice"].isna().all()
    assert (manquants["verdict"] == "INCONNU").all()


def test_anomalies_environ_3_pourcent():
    df = pipeline.tableau()
    part = df["est_anomalie"].sum() / df["air_temp_min_c"].notna().sum()
    assert 0.02 < part < 0.04


def test_assistant_repond_avec_preuves():
    r = assistant.repondre_regles("Puis-je sortir aujourd'hui ?")
    assert r["constat"] and r["preuves"] and r["limites"]


def test_assistant_refuse_ce_qu_il_ne_sait_pas():
    r = assistant.repondre_regles("Quel est le niveau de radiation ?")
    assert "pas dans mes données" in r["constat"]


def test_assistant_sol_inexistant():
    r = assistant.repondre_regles("sortir au sol 99999 ?")
    assert "n'existe pas" in r["constat"]


def test_reponses_compatibles_json():
    # json.dumps plante si un NaN traîne ; on vérifie que ce n'est pas le cas
    json.dumps(assistant.repondre_regles("anomalies ?"), allow_nan=False)
    json.dumps(pipeline.ligne(pipeline.dernier_sol_disponible()), allow_nan=False)


# ---------- Tests du LLM : on lance un FAUX serveur Ollama (pas besoin d'Ollama) ----------

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TEXTE_OK = (
    "CONSTAT: Sortie déconseillée au sol 4780.\n"
    "PREUVES:\n- Indice 98.2/100\n- Froid : -98 °C\n"
    "LIMITES: Indice pédagogique, pas un seuil NASA."
)


class FauxOllama(BaseHTTPRequestHandler):
    """Imite Ollama. 1er appel -> demande un outil ; ensuite -> réponse finale."""

    modeles = ["qwen2.5:7b"]
    reponses = {"outil": True, "texte": TEXTE_OK}
    requetes = []

    def log_message(self, *a):  # pas de bruit dans la console
        pass

    def _json(self, objet):
        corps = json.dumps(objet).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        self._json({"models": [{"name": m, "model": m} for m in self.modeles]})

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FauxOllama.requetes.append(payload)
        deja_un_outil = any(m["role"] == "tool" for m in payload["messages"])
        if self.reponses["outil"] and not deja_un_outil:
            msg = {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "obtenir_sortie", "arguments": {"sol": 4780, "inconnu": "x"}}}]}
        else:
            msg = {"role": "assistant", "content": self.reponses["texte"]}
        self._json({"message": msg})


def faux_ollama(**reglages):
    """Démarre le faux serveur, règle l'environnement, et retourne le serveur."""
    FauxOllama.requetes = []
    FauxOllama.modeles = reglages.get("modeles", ["qwen2.5:7b"])
    FauxOllama.reponses = {"outil": reglages.get("outil", True), "texte": reglages.get("texte", TEXTE_OK)}
    serveur = HTTPServer(("127.0.0.1", 0), FauxOllama)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    os.environ["OLLAMA_HOST"] = f"127.0.0.1:{serveur.server_port}"   # sans « http:// » volontairement
    os.environ["OLLAMA_MODEL"] = "qwen2.5:7b"
    return serveur


def test_outils_sont_compatibles_json():
    for nom, fonction in outils.FONCTIONS.items():
        json.dumps(fonction(), allow_nan=False)
    assert "erreur" in outils.obtenir_sortie(99999)


def test_decouper_reponse():
    r = llm.decouper_reponse("CONSTAT: Oui.\nPREUVES:\n- a\n- b\nLIMITES: attention")
    assert r["constat"] == "Oui." and r["preuves"] == ["a", "b"] and r["limites"] == "attention"
    assert llm.decouper_reponse("Juste du texte")["constat"] == "Juste du texte"
    assert llm.decouper_reponse("<think>hmm</think>CONSTAT: Ok")["constat"] == "Ok"


def test_verificateur_de_chiffres():
    outil = '{"indice": 98.2, "temp_min_c": -98.0}'
    assert llm.chiffres_non_verifies("Indice 98.2/100, froid -98 °C", [outil], "") == []
    assert llm.chiffres_non_verifies("Indice 42.5, froid -98 °C", [outil], "") == ["42.5"]
    assert llm.chiffres_non_verifies("sol 4780", [outil], "sol 4780 ?") == []


def test_etat_ollama():
    serveur = faux_ollama()
    try:
        assert llm.etat()["pret"] is True
        FauxOllama.modeles = ["autre:1b"]
        e = llm.etat()
        assert e["pret"] is False and "ollama pull" in e["raison"]
    finally:
        serveur.shutdown()
    os.environ["OLLAMA_HOST"] = "127.0.0.1:1"   # personne n'écoute ici
    assert llm.etat()["pret"] is False


def test_llm_utilise_les_outils_et_les_vraies_donnees():
    serveur = faux_ollama()
    try:
        r = llm.repondre_llm("Pourquoi le sol 4780 est-il rouge ?")
    finally:
        serveur.shutdown()
    assert r["sol_cite"] == 4780 and r["outils_utilises"] == ["obtenir_sortie"]
    assert r["preuves"] == ["Indice 98.2/100", "Froid : -98 °C"]
    assert r["chiffres_non_verifies"] == []
    premier, second = FauxOllama.requetes
    assert premier["stream"] is False and premier["messages"][0]["role"] == "system"
    assert len(premier["tools"]) == 4 and premier["tools"][0]["type"] == "function"
    retour = second["messages"][-1]                      # le résultat de l'outil renvoyé au modèle
    assert retour["role"] == "tool" and retour["tool_name"] == "obtenir_sortie"
    assert json.loads(retour["content"])["indice"] == 98.2   # VRAIES données


def test_chiffre_invente_est_signale():
    serveur = faux_ollama(texte=TEXTE_OK.replace("98.2", "77.7"))
    try:
        r = llm.repondre_llm("sol 4780 ?")
    finally:
        serveur.shutdown()
    assert r["chiffres_non_verifies"] == ["77.7"]


def test_secours_si_le_modele_ignore_les_outils():
    serveur = faux_ollama(outil=False)
    try:
        r = assistant.repondre("Puis-je sortir aujourd'hui ?")
    finally:
        serveur.shutdown()
    assert "secours" in r["type"] and r["preuves"]       # réponse ancrée, venue des règles


def test_secours_si_ollama_est_eteint():
    os.environ["OLLAMA_HOST"] = "127.0.0.1:1"
    r = assistant.repondre("anomalies ?")
    assert "règles" in r["type"] and r["preuves"]
    assert assistant.etat_llm()["assistant"] == "regles"


# ---------- Tests Gemini : faux serveur au format de l'API Gemini ----------

class FauxGemini(BaseHTTPRequestHandler):
    requetes = []
    en_tetes = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FauxGemini.requetes.append((self.path, payload))
        FauxGemini.en_tetes.append(self.headers.get("x-goog-api-key"))
        a_repondu = any("functionResponse" in p for m in payload["contents"] for p in m["parts"])
        if not a_repondu:
            parties = [{"functionCall": {"name": "obtenir_sortie", "args": {"sol": 4780.0, "inconnu": "x"}}}]
        else:
            parties = [{"text": TEXTE_OK}]
        corps = json.dumps({"candidates": [{"content": {"role": "model", "parts": parties}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(corps)


def regler_gemini():
    FauxGemini.requetes, FauxGemini.en_tetes = [], []
    serveur = HTTPServer(("127.0.0.1", 0), FauxGemini)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    os.environ.update(GEMINI_API_KEY="cle-de-test", GEMINI_API_BASE=f"http://127.0.0.1:{serveur.server_port}/v1beta",
                      LLM_PROVIDER="")
    return serveur


def nettoyer_gemini():
    for k in ("GEMINI_API_KEY", "GEMINI_API_BASE"):
        os.environ.pop(k, None)
    os.environ["LLM_PROVIDER"] = "ollama"


def test_gemini_boucle_outils_et_securite_de_la_cle():
    serveur = regler_gemini()
    try:
        assert llm.fournisseur() == "gemini" and assistant.etat_llm()["assistant"] == "gemini"
        r = assistant.repondre("Pourquoi le sol 4780 est-il rouge ?")
    finally:
        serveur.shutdown()
        nettoyer_gemini()
    assert "Gemini" in r["type"] and r["sol_cite"] == 4780 and r["outils_utilises"] == ["obtenir_sortie"]
    assert r["preuves"] == ["Indice 98.2/100", "Froid : -98 °C"] and r["chiffres_non_verifies"] == []
    (chemin, premier), (_, second) = FauxGemini.requetes
    assert chemin == "/v1beta/models/gemini-2.5-flash:generateContent"
    assert FauxGemini.en_tetes == ["cle-de-test", "cle-de-test"]            # la clé voyage dans l'en-tête
    assert "cle-de-test" not in json.dumps(r) and "cle-de-test" not in json.dumps(premier)  # jamais dans les données
    assert "AUCUN chiffre" in premier["systemInstruction"]["parts"][0]["text"]
    decl = premier["tools"][0]["functionDeclarations"]
    assert len(decl) == 4 and "parameters" not in decl[2]                    # outil sans argument : pas de parameters
    retour = second["contents"][-1]["parts"][0]["functionResponse"]
    assert retour["name"] == "obtenir_sortie" and retour["response"]["result"]["indice"] == 98.2


def test_gemini_en_panne_bascule_sur_les_regles():
    os.environ.update(GEMINI_API_KEY="cle-de-test", GEMINI_API_BASE="http://127.0.0.1:1/v1beta", LLM_PROVIDER="")
    try:
        r = assistant.repondre("anomalies ?")
    finally:
        nettoyer_gemini()
    assert "secours" in r["type"] and r["preuves"]


def test_le_fichier_env_est_charge_sans_ecraser_le_systeme(tmp_path=None):
    import tempfile
    from pathlib import Path
    from app import config
    dossier = Path(tempfile.mkdtemp())
    (dossier / ".env").write_text('# commentaire\nCLE_TEST_A=valeur1\nCLE_TEST_B="valeur2"\n', encoding="utf-8")
    os.environ["CLE_TEST_B"] = "deja-defini"
    ancien = config._ICI
    config._ICI = dossier / "backend"
    (dossier / "backend").mkdir()
    try:
        config.charger_env()
    finally:
        config._ICI = ancien
    assert os.environ["CLE_TEST_A"] == "valeur1" and os.environ["CLE_TEST_B"] == "deja-defini"


def test_api():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    assert client.get("/api/sante").json()["statut"] == "OK"
    assert client.get("/api/sortie/4995").status_code == 200
    assert client.get("/api/sortie/99999").status_code == 404
    carte = client.get("/api/carte").json()
    assert len(carte["sites"]) == 3
    r = client.post("/api/assistant", json={"question": "anomalies ?"})
    assert r.status_code == 200
    assert client.get("/").status_code == 200
