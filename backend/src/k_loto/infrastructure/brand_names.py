"""Display-only aliases; database names and historical records stay intact."""

import re


def display_brand_name(value: str) -> str:
    value = re.sub(
        r"\b(?:Kasper|Caster|Casper)\s+Lotto\b",
        "Casper Loto",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\bK-Loto\b", "Casper Loto", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(?:Kasper|Caster)\b",
        lambda match: "CASPER" if match[0].isupper() else "Casper",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"ПЛЛ-лото", "2:22", value, flags=re.IGNORECASE)
