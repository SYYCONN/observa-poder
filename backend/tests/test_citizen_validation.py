from app.services.citizen_drafts import AssistedDraftResult, OfficialPropositionContext
from app.services.citizen_validation import validate_draft


def context():
    return OfficialPropositionContext(
        label="PL 10/2026",
        kind="PL",
        summary="Exige publicação mensal de dados oficiais no valor de R$ 100,00.",
        detailed_summary=None,
        status_description="Aguardando despacho",
        keywords=["transparência"],
        source_url="https://example.test/10",
        full_text_url=None,
    )


def draft(summary="A proposta exige publicação mensal. Ela ainda aguarda análise."):
    return AssistedDraftResult(
        plain_summary=summary,
        what_changes=None,
        affected_groups=[],
        practical_example=None,
        impacts=None,
        benefits=None,
        cost_estimate=None,
        analysis=None,
    )


def test_valid_grounded_draft_passes_local_checks():
    result = validate_draft(context(), draft())
    assert result["passed"] is True
    assert all(result["checks"].values())


def test_unofficial_number_is_rejected():
    result = validate_draft(
        context(), draft("A proposta prevê gasto de R$ 999,00. Ela ainda aguarda análise.")
    )
    assert result["passed"] is False
    assert result["checks"]["all_numbers_grounded"] is False


def test_claim_that_proposal_is_already_law_is_rejected():
    result = validate_draft(
        context(), draft("A proposta já virou lei. Ela exige publicação mensal.")
    )
    assert result["passed"] is False
    assert result["checks"]["proposal_not_presented_as_law"] is False
