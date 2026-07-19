"""Safety backstop for clearly illegal / harmful business intents.

Defense-in-depth: a deterministic keyword gate here (can't be argued around by the
model) PLUS the IntakeAgent's semantic 'refuse' intent for paraphrases. We refuse to
produce a go-to-market plan for these regardless of how the request is framed.
"""
import re

_NOUNS = r"(weapons?|arms|firearms?|guns?|ammunition|drugs?|narcotics?|organs?)"
_BLOCKED = [
    # illegal/illicit/black-market + a controlled good (plural-safe)
    rf"\b(illegal|illicit|black[-\s]?market|smuggled|trafficked)\b.{{0,30}}\b{_NOUNS}\b",
    rf"\b{_NOUNS}\b.{{0,15}}\b(traffick|smuggl|black[-\s]?market|cartel)",
    r"\b(weapons?|arms|firearms?|guns?)\s+(traffick\w*|smuggl\w*|deal\w*|running)",
    r"\b(drug|narcotic|cocaine|heroin|meth|fentanyl|opioid)s?\s*(traffick\w*|smuggl\w*|deal\w*|cartel|ring)",
    r"\b(illegal|illicit)\s+drugs?\b",
    r"\bhuman\s+(traffick|smuggl)\w*",
    r"\bsex\s+traffick\w*",
    r"\bchild\s+(porn\w*|exploitation|abuse)\b|\bcsam\b",
    r"\bmoney\s+launder\w*",
    r"\b(assassinat\w*|hitman|contract\s+kill\w*)",
    r"\b(terroris\w*|explosive\s+devices?|bomb[-\s]?making|\bied\b)",
    r"\bpoach\w*\b.{0,30}\b(ivory|rhino|elephant|endangered)\b",
    r"\bcounterfeit\s+(money|currency|cash|bank ?notes?|goods|products?)\b",
    r"\b(ponzi|pyramid\s+scheme)\b",
]
_PATTERNS = [re.compile(p, re.I) for p in _BLOCKED]

REFUSAL = (
    "I can't help build a go-to-market plan for an illegal or harmful business. "
    "I'm a market-entry research assistant for lawful ventures — if you have a legitimate "
    "business, tell me the country, business type, and budget and I'll analyze it."
)


def is_blocked(text: str) -> bool:
    """True if the text describes a clearly illegal/harmful business we won't plan for."""
    return any(p.search(text or "") for p in _PATTERNS)
