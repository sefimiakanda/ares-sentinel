"""Point d'entrée de l'assistant Ares Sentinel, propulsé par OpenRouter."""

EXEMPLES = [
    "Puis-je sortir aujourd'hui ?",
    "Pourquoi le sol 4780 est-il rouge ?",
    "Quelles sont les plus grosses anomalies ?",
    "Les tempêtes de poussière rendent-elles les sorties plus risquées ?",
    "Quelle est la température la plus froide mesurée ?",
]

LIMITE_GENERALE = (
    "Données d'un seul site (cratère Gale, rover Curiosity). "
    "L'indice est pédagogique et n'est pas un seuil de sécurité officiel de la NASA."
)


def repondre(question: str, sol_choisi=None) -> dict:
    """Interroge OpenRouter ; aucune réponse locale de secours n'est fabriquée."""
    from . import llm
    if not llm.fournisseur():
        raise llm.LLMConfigurationError(llm.etat()["raison"])
    return llm.repondre_openrouter(question, sol_choisi)


def etat_llm() -> dict:
    """État OpenRouter exposé au tableau de bord."""
    from . import llm
    etat = llm.etat()
    return {
        "assistant": etat["fournisseur"] or "openrouter_indisponible",
        "assistant_modele": etat["modele"],
        "assistant_raison": etat["raison"],
    }
