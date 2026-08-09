"""Helpers for parsing and sanitizing LLM output in the copilot."""
import json


def extract_json(raw: str) -> dict:
    """Extract and parse the first JSON object from an LLM response."""
    if not raw:
        return {}
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}


def to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return False


def sanitize_ascii(text: str) -> str:
    """Replace non-ASCII punctuation with ASCII equivalents so LLM text is
    safe for consoles and logs that use legacy encodings."""
    if not text:
        return text
    replacements = {
        "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
        "\u2014": "-", "\u00a0": " ", "\u202f": " ", "\u2009": " ",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u20b9": "Rs", "\u20bf": "Rs",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text
