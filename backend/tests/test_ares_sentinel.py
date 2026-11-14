import json
import os
from types import SimpleNamespace

import pytest

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


def test_nasa_space_apps_image_is_served():
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/nasa.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_anomalies_endpoint_includes_explanatory_statistics():
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/api/anomalies")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert data["statistiques"]["jours_analyses"] > data["total"]
    assert 0 < data["statistiques"]["taux_pct"] < 100
    assert data["statistiques"]["sol_le_plus_atypique"]["intensite"] >= data["statistiques"]["intensite_moyenne"]
    assert data["anomalies"][0]["raison"]


def test_openrouter_requires_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert llm.fournisseur() is None
    assert "OpenRouter" in llm.etat()["raison"]


def test_openrouter_client_uses_configured_endpoint(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    client = llm._client()

    assert str(client.base_url) == "https://openrouter.ai/api/v1/"
    assert client.api_key == "test-key"


def test_response_parser_and_number_guard():
    response = llm.decouper_reponse("CONSTAT: Oui.\nPREUVES:\n- Indice 98.2/100\nLIMITES: Test.")
    assert response["constat"] == "Oui."
    assert llm.chiffres_non_verifies("Indice 77.7", ['{"indice": 98.2}'], "") == ["77.7"]


def test_openrouter_preloads_local_data_in_one_request(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/free")
    monkeypatch.setattr(outils, "obtenir_sortie", lambda sol=None: {"sol": sol or 42, "indice": 20})
    monkeypatch.setattr(outils, "statistiques_globales", lambda: {"sols": 10})
    monkeypatch.setattr(outils, "lister_anomalies", lambda limite=5: {"total_anomalies": 2})
    monkeypatch.setattr(outils, "comparer_saisons", lambda: {"saison_poussiere": {"nb_sols": 5}})
    response = SimpleNamespace(
        model="provider/model:free",
        choices=[SimpleNamespace(message=SimpleNamespace(content="CONSTAT: Données disponibles.\nPREUVES:\n- Sol 42, indice 20/100\nLIMITES: Comparaison historique."))],
    )
    requests = []

    class Completions:
        def create(self, **kwargs):
            requests.append(kwargs)
            return response

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    result = llm.repondre_openrouter("Compare le sol 42 au sol 43.", sol_choisi=42, client=client)

    assert len(requests) == 1
    assert requests[0]["model"] == "openrouter/free"
    assert requests[0]["max_tokens"] == 512
    assert "tools" not in requests[0]
    assert '"sol": 43' in requests[0]["messages"][0]["content"]
    assert result["outils_utilises"] == ["obtenir_sortie", "obtenir_sortie", "statistiques_globales", "lister_anomalies", "comparer_saisons"]
    assert result["sol_cite"] == 42
    assert "provider/model:free" in result["type"]


def test_openrouter_rejects_empty_response(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    class Completions:
        def create(self, **_):
            return SimpleNamespace(choices=[])

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    with pytest.raises(RuntimeError, match="réponse vide"):
        llm.repondre_openrouter("Question", client=client)
