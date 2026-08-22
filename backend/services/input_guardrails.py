import re
from dataclasses import dataclass


class GuardrailViolation(ValueError):
    """Raised when a user query must not be sent to the document agent."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class SanitizedQuery:
    value: str
    masked_pii: bool


_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions?\b", re.I),
    re.compile(r"\b(disregard|override|forget)\s+(all\s+)?(system|previous|以上)", re.I),
    re.compile(r"\b(reveal|show|print|repeat)\b.{0,40}\b(system prompt|hidden prompt|instructions)\b", re.I),
    re.compile(r"\b(developer|system)\s+message\b", re.I),
    re.compile(r"\b(jailbreak|do anything now|dan mode)\b", re.I),
)

_PII_PATTERNS = (
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"(?<!\w)(?:\+?1[-. ]?)?(?:\(?\d{3}\)?[-. ]?)\d{3}[-. ]?\d{4}(?!\w)"), "[REDACTED_PHONE]"),
    (re.compile(r"\b(?:sk|pk|ghp|github_pat|AKIA)[-_A-Za-z0-9]{10,}\b"), "[REDACTED_SECRET]"),
    (re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"), "[REDACTED_CARD]"),
)

_STOP_WORDS = {
    "a", "about", "an", "and", "are", "can", "could", "does", "for", "from",
    "how", "in", "is", "it", "me", "of", "on", "or", "please", "tell", "that",
    "the", "this", "to", "what", "when", "where", "which", "who", "why", "with",
}
_GENERIC_DOCUMENT_QUERY = re.compile(
    r"\b(summar(?:y|ize)|overview|main (?:point|idea)|key (?:point|takeaway)|"
    r"what (?:is|are) (?:this|the) (?:document|report|brief)|according to (?:the )?document)\b",
    re.I,
)


def sanitize_query(query: str) -> SanitizedQuery:
    value = query.strip()
    if not value:
        raise GuardrailViolation("Please enter a question about the document.")
    if len(value) > 4000:
        raise GuardrailViolation("Questions must be 4,000 characters or fewer.")
    if any(pattern.search(value) for pattern in _INJECTION_PATTERNS):
        raise GuardrailViolation("This request contains an instruction override and cannot be processed.")

    masked = mask_pii(value)
    return SanitizedQuery(value=masked, masked_pii=masked != value)


def mask_pii(value: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def is_relevant_to_document(query: str, context: str) -> bool:
    if not context.strip():
        return False
    if _GENERIC_DOCUMENT_QUERY.search(query):
        return True

    query_terms = {
        term for term in re.findall(r"[a-z0-9]{3,}", query.lower())
        if term not in _STOP_WORDS
    }
    context_terms = set(re.findall(r"[a-z0-9]{3,}", context.lower()))
    return bool(query_terms & context_terms)


def is_answer_grounded(answer: str, context: str) -> bool:
    normalized = answer.lower().strip()
    if not normalized:
        return False
    if re.search(r"\b(cannot find|can't find|not found|not in the document)\b", normalized):
        return True
    answer_terms = set(re.findall(r"[a-z0-9]{3,}", normalized)) - _STOP_WORDS
    context_terms = set(re.findall(r"[a-z0-9]{3,}", context.lower()))
    return bool(answer_terms & context_terms)
