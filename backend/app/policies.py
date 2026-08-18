import re

STRUCTURING_SUMMARY = (
    "Potential structuring activity detected from repeated sub-$10,000 cash deposits "
    "and reporting-avoidance language."
)

_AMOUNT_RE = re.compile(r"(?:\$\s*)?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?")
_EVASION_RE = re.compile(
    r"\breport(?:ed|ing)?\b|\bpaperwork\b|\bother window\b|\bsplit\b|"
    r"\bchunks?\b|\bthreshold\b",
    re.IGNORECASE,
)


def detect_structuring(player_messages: list[str]) -> bool:
    """Detect repeated small cash deposits paired with reporting-avoidance language."""
    text = "\n".join(player_messages)
    normalized = text.lower()
    amounts = [float(value.replace(",", "")) for value in _AMOUNT_RE.findall(text)]
    small_amounts = [amount for amount in amounts if 0 < amount < 10_000]

    return (
        "cash" in normalized
        and "deposit" in normalized
        and len(small_amounts) >= 2
        and _EVASION_RE.search(text) is not None
    )
