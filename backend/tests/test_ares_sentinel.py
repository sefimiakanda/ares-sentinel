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


def test_openrouter_requires_tool_before_answer(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="obtenir_sortie", arguments='{"sol": 42}'),
    )
    tool_message = SimpleNamespace(
        content=None,
        tool_calls=[call],
        model_dump=lambda **_: {
            "role": "assistant",
            "tool_calls": [{"id": "call-1", "type": "function"}],
        },
    )
    final_message = SimpleNamespace(
        content="CONSTAT: Données disponibles.\nPREUVES:\n- Sol 42, indice 20/100\nLIMITES: Comparaison historique.",
        tool_calls=None,
    )
    responses = [
        SimpleNamespace(model="provider/model:free", choices=[SimpleNamespace(message=tool_message)]),
        SimpleNamespace(model="provider/model:free", choices=[SimpleNamespace(message=final_message)]),
    ]
    requests = []

    class Completions:
        def create(self, **kwargs):
            requests.append(kwargs)
            return responses.pop(0)

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    monkeypatch.setattr(llm, "_executer_outil", lambda *_: ('{"sol": 42, "indice": 20}', False))

    result = llm.repondre_openrouter("Quel est le risque ?", sol_choisi=42, client=client)

    assert requests[0]["tool_choice"] == "required"
    assert requests[1]["tool_choice"] == "none"
    assert requests[1]["model"] == "provider/model:free"
    assert requests[1]["messages"][-1]["role"] == "tool"
    assert len(requests) == 2
    assert result["outils_utilises"] == ["obtenir_sortie"]
    assert result["sol_cite"] == 42
    assert "provider/model:free" in result["type"]


def test_openrouter_rejects_another_tool_round(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="obtenir_sortie", arguments="{}"),
    )
    tool_message = SimpleNamespace(
        content=None,
        tool_calls=[call],
        model_dump=lambda **_: {"role": "assistant", "tool_calls": []},
    )
    responses = [
        SimpleNamespace(model="provider/model:free", choices=[SimpleNamespace(message=tool_message)]),
        SimpleNamespace(model="provider/model:free", choices=[SimpleNamespace(message=tool_message)]),
    ]
    calls = []

    class Completions:
        def create(self, **_):
            return responses.pop(0)

    monkeypatch.setattr(llm, "_executer_outil", lambda *_: (calls.append("tool") or "{}", False))
    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    with pytest.raises(RuntimeError, match="nouvel appel d'outil"):
        llm.repondre_openrouter("Question", client=client)

    assert calls == ["tool"]


def test_tool_rejects_malformed_arguments():
    result, failed = llm._executer_outil("obtenir_sortie", "{")

    assert failed
    assert json.loads(result)["erreur"] == "Arguments d'outil JSON invalides."


def test_openrouter_rejects_empty_response(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    class Completions:
        def create(self, **_):
            return SimpleNamespace(choices=[])

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    with pytest.raises(RuntimeError, match="réponse vide"):
        llm.repondre_openrouter("Question", client=client)
