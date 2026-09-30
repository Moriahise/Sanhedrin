TAG_CATEGORIES = {
    "shabbat": "halacha",
    "shabbos": "halacha",
    "kashrut-kosher": "halacha",
    "halacha": "halacha",
    "tefillah": "halacha",
    "berachot": "halacha",
    "tanach-bible": "tanach",
    "chumash": "tanach",
    "parshanut-torah-comment": "tanach",
    "talmud-gemara": "talmud",
    "mishnah": "talmud",
    "gemara": "talmud",
    "history": "history",
    "jewish-history": "history",
    "kabbalah": "kabbalah",
    "zohar": "kabbalah",
}


def classify(tags):
    categories = {
        TAG_CATEGORIES[tag.lower()]
        for tag in tags
        if isinstance(tag, str) and tag.lower() in TAG_CATEGORIES
    }
    if len(categories) != 1:
        return None
    return {
        "category": next(iter(categories)),
        "category_source": "source_tags:v1",
        "category_confidence": 1.0,
        "needs_review": False,
    }
