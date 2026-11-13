"""Validações locais que impedem publicação de conteúdo não sustentado."""

import re
import unicodedata

from app.modules.proposicoes.editorial import copies_official_summary
from app.services.citizen_drafts import AssistedDraftResult, OfficialPropositionContext

NUMBER_PATTERN = re.compile(r"(?<!\w)\d[\d.,/%-]*")
FORBIDDEN_PATTERNS = {
    "claims_current_law": re.compile(
        r"\b(j[aá]\s+(?:est[aá]|virou)|entrou\s+em\s+vigor|passou\s+a\s+valer|lei\s+vigente)\b",
        re.IGNORECASE,
    ),
    "political_judgment": re.compile(
        r"\b(absurdo|vergonhoso|excelente\s+projeto|péssimo\s+projeto|deveria\s+ser\s+aprovad[oa])\b",
        re.IGNORECASE,
    ),
    "guaranteed_effect": re.compile(
        r"\b(vai\s+garantir|garante\s+que|certamente|sem\s+dúvida)\b",
        re.IGNORECASE,
    ),
}


def _fold(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    ).casefold()


def _all_text(draft: AssistedDraftResult) -> str:
    values = [
        draft.plain_summary,
        draft.what_changes,
        *draft.affected_groups,
        draft.practical_example,
        draft.impacts,
        draft.benefits,
        draft.cost_estimate,
        draft.analysis,
    ]
    return "\n".join(value for value in values if value)


def _numeric_tokens(value: str) -> set[str]:
    return {_fold(token).rstrip(".,") for token in NUMBER_PATTERN.findall(value)}


def validate_draft(
    context: OfficialPropositionContext, draft: AssistedDraftResult
) -> dict[str, object]:
    generated = _all_text(draft)
    official = "\n".join(
        value
        for value in (
            context.label,
            context.summary,
            context.detailed_summary,
            context.status_description,
            "\n".join(context.keywords),
        )
        if value
    )
    unsupported_numbers = sorted(_numeric_tokens(generated) - _numeric_tokens(official))
    forbidden = [name for name, pattern in FORBIDDEN_PATTERNS.items() if pattern.search(generated)]
    checks = {
        "not_official_copy": not copies_official_summary(
            draft.plain_summary, context.summary, context.detailed_summary
        ),
        "all_numbers_grounded": not unsupported_numbers,
        "proposal_not_presented_as_law": "claims_current_law" not in forbidden,
        "neutral_language": "political_judgment" not in forbidden,
        "no_guaranteed_effect": "guaranteed_effect" not in forbidden,
        "summary_has_multiple_sentences": len(
            [part for part in re.split(r"[.!?]+", draft.plain_summary) if part.strip()]
        )
        >= 2,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "unsupported_numbers": unsupported_numbers,
        "triggered_rules": forbidden,
    }
