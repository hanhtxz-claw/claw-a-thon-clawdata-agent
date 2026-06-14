import json
import re
from difflib import SequenceMatcher
from pathlib import Path

_CATALOG = None

def load_catalog():
    global _CATALOG
    if _CATALOG is None:
        path = Path(__file__).parent / "data" / "catalog.json"
        with open(path, encoding="utf-8") as f:
            _CATALOG = json.load(f)
    return _CATALOG


def _tokenize(text: str) -> set:
    text = text.lower()
    tokens = set(re.split(r"[\s,._\-/|()\[\]]+", text))
    tokens.discard("")
    return tokens


def _score(entry: dict, query_tokens: set) -> float:
    searchable = " ".join([
        entry.get("name", ""),
        " ".join(entry.get("tags", [])),
        entry.get("description", ""),
        entry.get("best_for", ""),
        entry.get("layer", ""),
        entry.get("platform", ""),
    ])
    entry_tokens = _tokenize(searchable)

    # Token overlap score
    if not query_tokens or not entry_tokens:
        return 0.0

    overlap = len(query_tokens & entry_tokens)
    token_score = overlap / max(len(query_tokens), 1)

    # Sequence similarity on name
    name_sim = SequenceMatcher(None, " ".join(query_tokens), entry.get("name", "").lower()).ratio()

    return token_score * 0.7 + name_sim * 0.3


def search(query: str, top_n: int = 6) -> list:
    catalog = load_catalog()
    query_tokens = _tokenize(query)

    scored = [(entry, _score(entry, query_tokens)) for entry in catalog]
    scored.sort(key=lambda x: x[1], reverse=True)

    top = [entry for entry, score in scored[:top_n] if score > 0]

    # If no score > 0, return top_n by name similarity as fallback
    if not top:
        top = [entry for entry, _ in scored[:top_n]]

    return top
