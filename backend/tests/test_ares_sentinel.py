import json
import os

from app import llm, outils, pipeline
from app.indice import rang, verdict


def test_risk_data_is_valid():
    df = pipeline.tableau().dropna(subset=["indice"])
    assert df["indice"].between(0, 100).all()
    assert verdict(90, {"orange": 50, "rouge": 70})["code"] == "ROUGE"
    assert rang([1, 2, 3, 4], 3) == 50


def test_tools_are_json_serializable():
    for function in outils.FONCTIONS.values():
        json.dumps(function(), allow_nan=False)


def test_gemini_only_requires_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert llm.fournisseur() is None
    assert "Gemini" in llm.etat()["raison"]


def test_response_parser_and_number_guard():
    response = llm.decouper_reponse("CONSTAT: Oui.\nPREUVES:\n- Indice 98.2/100\nLIMITES: Test.")
    assert response["constat"] == "Oui."
    assert llm.chiffres_non_verifies("Indice 77.7", ['{"indice": 98.2}'], "") == ["77.7"]
