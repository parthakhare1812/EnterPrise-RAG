
import re


BLOCKED_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\breveal\s+(your\s+)?system\s+prompt\b",
    r"\bshow\s+(me\s+)?(your\s+)?hidden\s+instructions\b",
    r"\bact\s+as\s+an?\s+unrestricted\b",
]

SENSITIVE_PATTERNS = [
    r"\bhow\s+to\s+steal\s+credentials\b",
    r"\bhow\s+to\s+hack\s+someone\b",
]


def validate_query(query: str) -> dict:
    if not isinstance(query, str) or not query.strip():
        return {
            "allowed": False,
            "reason": "Query cannot be empty."
        }

    normalized = query.strip()

    if len(normalized) > 10000:
        return {
            "allowed": False,
            "reason": "Query exceeds the maximum allowed length."
        }

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return {
                "allowed": False,
                "reason": "Potential prompt injection detected."
            }

    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return {
                "allowed": False,
                "reason": "The request violates application usage rules."
            }

    return {
        "allowed": True,
        "reason": "Query passed validation."
    }


def validate_response(response: str) -> dict:
    if not isinstance(response, str) or not response.strip():
        return {
            "valid": False,
            "reason": "Response is empty."
        }

    if len(response) > 30000:
        return {
            "valid": False,
            "reason": "Response exceeds the maximum length."
        }

    return {
        "valid": True,
        "reason": "Response passed validation."
    }


def requires_human_approval(query: str) -> bool:
    patterns = [
        r"\bdelete\s+(all\s+)?(documents|records|data)\b",
        r"\bpermanently\s+delete\b",
        r"\bmodify\s+(all\s+)?(records|documents)\b",
        r"\bexecute\s+(this\s+)?(command|script)\b",
        r"\bapprove\s+(this\s+)?transaction\b",
    ]

    return any(
        re.search(pattern, query, re.IGNORECASE)
        for pattern in patterns
    )


def grounding_fallback(results: list[dict]) -> str:
    if not results:
        return (
            "I couldn't find relevant information in the "
            "uploaded documents to answer this question."
        )

    return (
        "The retrieved document information is insufficient "
        "to provide a reliable answer."
    )
