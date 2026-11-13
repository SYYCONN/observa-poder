def normalize_editorial_text(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def copies_official_summary(
    plain_summary: str,
    official_summary: str,
    detailed_summary: str | None = None,
) -> bool:
    normalized = normalize_editorial_text(plain_summary)
    return bool(normalized) and normalized in {
        normalize_editorial_text(official_summary),
        normalize_editorial_text(detailed_summary),
    }
