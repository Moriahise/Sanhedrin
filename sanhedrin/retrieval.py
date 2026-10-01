"""Question-focused scoring shared by research, local retrieval and reranking.

Long articles and a large list of weak query words must not beat a short direct
answer. Model knowledge is used for search leads; it is never treated as evidence.
"""
import math
import re
from bs4 import BeautifulSoup
from .html import tokens, plain_text, sanitize


def search_text(value):
    text = re.sub(r"https?://\S+", " ", str(value))
    return re.sub(r"(?<=[A-Za-z])['’](?=[A-Za-z])", "", text)


def question_title(value):
    soup = BeautifulSoup(str(value), 'html.parser')
    lines = [s.strip() for s in soup.get_text('\n').splitlines() if s.strip()]
    return search_text(lines[0] if lines else str(value))[:200]


def title_affinity(title, question, stopwords):
    left = set(tokens(search_text(plain_text(sanitize(title))))) - stopwords
    right = set(tokens(search_text(question))) - stopwords
    if not left or not right:
        return 0
    common = len(left & right)
    return common / max(len(left), len(right)) if common >= min(2, len(left), len(right)) else 0


def lexical_score(matched, title_matches, weights, length, affinity=0):
    # A long reference work can contain all the words by accident.
    normalization = 1 + .23 * math.log1p(max(0, length - 1800) / 1800)
    score = sum(weights[i] for i in matched) / normalization
    score += 2 * sum(weights[i] for i in title_matches)
    return score + (50 * affinity if affinity >= .45 else 8 * affinity)

