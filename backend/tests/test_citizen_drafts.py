import json

import httpx
import pytest

from app.services.citizen_drafts import (
    DraftGenerationError,
    OfficialPropositionContext,
    OpenAICitizenExplanationAutomation,
)


def context() -> OfficialPropositionContext:
    return OfficialPropositionContext(
        label="PL 10/2026",
        kind="PL",
        summary="Cria uma regra de transparência.",
        detailed_summary="Exige a publicação mensal de dados oficiais.",
        status_description="Aguardando despacho",
        keywords=["transparência"],
        source_url="https://dadosabertos.camara.leg.br/proposicoes/10",
        full_text_url="https://www.camara.leg.br/texto/10",
    )


def response_with(value: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}
            ]
        },
    )


def test_openai_automation_generates_and_verifies_with_separate_models():
    captured = []
    generated = {
        "plain_summary": "A proposta cria uma regra de transparência. Ela prevê divulgação mensal.",
        "what_changes": "Cria uma obrigação de publicação mensal.",
        "affected_groups": [],
        "practical_example": None,
        "impacts": None,
        "benefits": None,
        "cost_estimate": None,
        "analysis": None,
    }
    verified = {"approved": True, "grounded": True, "neutral": True, "clear": True, "issues": []}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.headers["Authorization"], json.loads(request.content)))
        return response_with(generated if len(captured) == 1 else verified)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        automation = OpenAICitizenExplanationAutomation(
            "secret-key", "generation-model", "verification-model", client
        )
        draft = automation.generate(context())
        result = automation.verify(context(), draft)

    assert result.approved is True
    assert [body["model"] for _, body in captured] == ["generation-model", "verification-model"]
    assert all(body["store"] is False for _, body in captured)
    assert all(body["text"]["format"]["strict"] is True for _, body in captured)
    source = json.loads(captured[0][1]["input"][0]["content"][0]["text"])
    assert source["official_data"]["summary"] == context().summary


@pytest.mark.parametrize(
    "content",
    [
        [{"type": "refusal", "refusal": "Cannot comply"}],
        [{"type": "output_text", "text": '{"plain_summary":"incompleto"}'}],
        [],
    ],
)
def test_openai_automation_rejects_unusable_generation(content):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output": [{"type": "message", "content": content}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DraftGenerationError):
            OpenAICitizenExplanationAutomation(
                "secret-key", "generation-model", "verification-model", client
            ).generate(context())


def test_verification_cannot_claim_approval_with_issues():
    invalid = {
        "approved": True,
        "grounded": True,
        "neutral": True,
        "clear": True,
        "issues": ["erro"],
    }
    with httpx.Client(transport=httpx.MockTransport(lambda _: response_with(invalid))) as client:
        automation = OpenAICitizenExplanationAutomation(
            "secret-key", "generation-model", "verification-model", client
        )
        from app.services.citizen_drafts import AssistedDraftResult

        candidate = AssistedDraftResult(
            plain_summary="A proposta cria uma regra. Ela ainda está em análise.",
            what_changes=None,
            affected_groups=[],
            practical_example=None,
            impacts=None,
            benefits=None,
            cost_estimate=None,
            analysis=None,
        )
        with pytest.raises(DraftGenerationError, match="verification_inconsistent_output"):
            automation.verify(context(), candidate)
