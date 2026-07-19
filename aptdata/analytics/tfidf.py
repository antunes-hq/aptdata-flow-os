"""TF-IDF keyword extraction — reusable across aptdata modules."""

import math
import re
from collections import Counter

_STOPWORDS = {
    "uma",
    "com",
    "para",
    "que",
    "dos",
    "das",
    "como",
    "mais",
    "muito",
    "isso",
    "esse",
    "essa",
    "este",
    "esta",
    "era",
    "foi",
    "ser",
    "ter",
    "está",
    "não",
    "sim",
    "por",
    "aos",
    "são",
    "seu",
    "sua",
    "ele",
    "ela",
    "nos",
    "nas",
    "pelo",
    "pela",
    "tem",
    "vai",
    "só",
    "lá",
    "aqui",
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "are",
    "was",
}

_TOKEN_RE = re.compile(r"[a-zà-ÿ0-9]{3,}", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def tfidf_keywords(texts: list[str], top_n: int = 5) -> list[str]:
    """Extrai os termos mais distintivos de uma coleção de textos via TF-IDF."""
    docs = [_tokenize(t) for t in texts]
    docs = [d for d in docs if d]
    if not docs:
        return []

    n_docs = len(docs)
    doc_freq: Counter = Counter()
    for tokens in docs:
        for term in set(tokens):
            doc_freq[term] += 1

    scores: dict[str, float] = {}
    for tokens in docs:
        tf = Counter(tokens)
        for term, freq in tf.items():
            idf = math.log((n_docs + 1) / (doc_freq[term] + 1)) + 1.0
            scores[term] = scores.get(term, 0.0) + freq * idf

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [term for term, _ in ranked[:top_n]]
