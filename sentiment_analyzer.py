"""
sentiment_analyzer.py — Partie II, Tâche 6 : Analyse de sentiments
TP1 — Intelligence Artificielle & Cybersécurité

Choix bibliothèque : VADER (vaderSentiment)
Raison : conçu pour les textes courts et informels, pas d'entraînement requis,
         scores entre -1 et +1 directement exploitables, très rapide.

Limitation connue : anglais uniquement. Pour le français → voir Extension E
(CamemBERT / 'tblard/tf-allocine' via HuggingFace).
"""

import json
import os
from datetime import datetime
from typing import Optional

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER_AVAILABLE = True
except ImportError:
    _VADER_AVAILABLE = False
    print("[AVERTISSEMENT] vaderSentiment non installé. "
          "Exécutez : pip install vaderSentiment")

# ---------------------------------------------------------------------------
# Singleton : l'analyseur est instancié une seule fois (initialisation coûteuse)
# ---------------------------------------------------------------------------
_analyzer: Optional[object] = None

def _get_analyzer():
    """Retourne l'instance unique de SentimentIntensityAnalyzer (pattern Singleton)."""
    global _analyzer
    if _analyzer is None and _VADER_AVAILABLE:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


# ---------------------------------------------------------------------------
# Seuils de classification (calibrés pour VADER)
# ---------------------------------------------------------------------------
POSITIVE_THRESHOLD = 0.05   # compound > 0.05  → positif
NEGATIVE_THRESHOLD = -0.05  # compound < -0.05 → négatif
MIN_WORDS = 3               # Nombre minimum de mots pour analyser


def analyze_sentiment(text: str) -> dict:
    """
    Analyse le sentiment d'un texte saisi.

    Paramètres
    ----------
    text : str
        Texte issu du keylogger (phrase ou paragraphe).

    Retour
    ------
    dict avec les clés :
        - score     : float entre -1.0 (très négatif) et +1.0 (très positif)
        - label     : str  'positif' | 'négatif' | 'neutre' | 'trop_court'
        - timestamp : str  ISO 8601
        - text      : str  texte analysé (nettoyé)
        - details   : dict scores bruts VADER (neg, neu, pos, compound)
    """
    ts = datetime.now().isoformat()
    text_clean = text.strip()

    # --- Cas : texte trop court ---
    word_count = len(text_clean.split())
    if word_count < MIN_WORDS:
        return {
            "score": 0.0,
            "label": "trop_court",
            "timestamp": ts,
            "text": text_clean,
            "details": {},
            "word_count": word_count,
        }

    # --- Cas : VADER non disponible ---
    analyzer = _get_analyzer()
    if analyzer is None:
        return {
            "score": 0.0,
            "label": "erreur_librairie",
            "timestamp": ts,
            "text": text_clean,
            "details": {},
            "word_count": word_count,
        }

    # --- Analyse VADER ---
    scores = analyzer.polarity_scores(text_clean)
    compound = scores["compound"]

    if compound >= POSITIVE_THRESHOLD:
        label = "positif"
    elif compound <= NEGATIVE_THRESHOLD:
        label = "négatif"
    else:
        label = "neutre"

    return {
        "score": round(compound, 4),
        "label": label,
        "timestamp": ts,
        "text": text_clean,
        "details": {
            "neg": scores["neg"],
            "neu": scores["neu"],
            "pos": scores["pos"],
            "compound": scores["compound"],
        },
        "word_count": word_count,
    }


def analyze_sentences_from_log(log_text: str) -> list:
    """
    Découpe le texte du log en phrases (délimiteur : retour à la ligne)
    et analyse le sentiment de chacune.

    Retour
    ------
    list de dict (résultats de analyze_sentiment), filtrés sur les phrases non vides.
    """
    sentences = [s.strip() for s in log_text.split("\n") if s.strip()]
    return [analyze_sentiment(s) for s in sentences]


def save_sentiment_results(results: list, output_path: str = "data/sentiments.json") -> None:
    """
    Sauvegarde les résultats d'analyse dans un fichier JSON structuré.

    Structure JSON
    --------------
    [
      {
        "timestamp": "2024-04-20T14:32:01.123456",
        "text": "Hello world this is fine",
        "sentiment": "positif",
        "score": 0.4215,
        "details": { "neg": 0.0, "neu": 0.678, "pos": 0.322, "compound": 0.4215 }
      },
      ...
    ]
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Charger les entrées existantes (pour ne pas écraser)
    existing = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []

    # Ajouter les nouveaux résultats
    for r in results:
        existing.append({
            "timestamp": r["timestamp"],
            "text": r["text"],
            "sentiment": r["label"],
            "score": r["score"],
            "details": r.get("details", {}),
            "word_count": r.get("word_count", 0),
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Test rapide en standalone
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    samples = [
        "I am so happy today, everything is going great!",
        "This is terrible, I hate this broken computer",
        "The weather is okay I suppose",
        "Hi",  # trop court
        "I cannot believe how angry and frustrated I feel right now with this awful software",
    ]
    print(f"{'Texte':<55} {'Label':<12} {'Score':>7}")
    print("-" * 78)
    for s in samples:
        result = analyze_sentiment(s)
        print(f"{s[:52]:<55} {result['label']:<12} {result['score']:>7.4f}")
