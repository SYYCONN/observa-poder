from types import SimpleNamespace

import pytest

from app.services.voting_presentation import describe_voting


def voting(description="Aprovada", approved=True, object_description=None):
    return SimpleNamespace(source="camara", description=description,
                           approved=approved, object_description=object_description)


def proposition(**values):
    return SimpleNamespace(**{
        "id": "official-report", "source": "camara", "kind": "REL", "number": 1,
        "year": 2026, "summary": "Dispõe sobre as Emendas da Comissão de Defesa do Consumidor, ao PLN n.º 24, de 2026-CN – Projeto de Lei Orçamentária Anual para 2027, nos termos da Resolução 01, de 2006-CN.",
        **values,
    })


@pytest.mark.parametrize("description", ["Aprovada", "Aprovada nos termos do Relatório do relator"])
def test_reported_case_identifies_report_and_budget_year(description):
    prop = proposition()
    result = describe_voting(voting(description), [("object", prop), ("possible_object", prop)])
    assert result["display_title"] == "Aprovado relatório sobre emendas ao Orçamento de 2027"
    assert "não representa a aprovação do Orçamento inteiro" in result["decision_context"]
    assert result["subject_status"] == "identified"


def test_possible_object_is_not_declared_approved():
    result = describe_voting(voting(), [("possible_object", proposition())])
    assert result["display_title"].startswith("Resultado aprovado em votação relacionada")
    assert "objeto possível" in result["decision_context"]
    assert result["subject_status"] == "related"


@pytest.mark.parametrize("description", ["Votação preliminar em turno único.", "Aprovado o requerimento de urgência.", "Aprovado o destaque."])
def test_specific_stage_is_preserved_instead_of_approving_bill(description):
    prop = proposition(kind="PL", summary="Altera regras de atendimento ao consumidor.")
    result = describe_voting(voting(description, object_description=description), [("object", prop)])
    assert result["display_title"].startswith(description.rstrip("."))
    assert not result["display_title"].startswith("Aprovado projeto de lei")
    assert "não permite concluir" in result["decision_context"]


@pytest.mark.parametrize("approved, prefix", [(False, "Rejeitado relatório"), (None, "Decisão sobre relatório")])
def test_rejection_and_unknown_result_are_not_approval(approved, prefix):
    result = describe_voting(voting(approved=approved), [("object", proposition())])
    assert result["display_title"].startswith(prefix)


def test_missing_or_multiple_subjects_do_not_choose_arbitrarily():
    assert describe_voting(voting())["subject_status"] == "unknown"
    result = describe_voting(voting(), [("object", proposition()), ("object", proposition(id="other"))])
    assert result["subject_status"] == "multiple"
    assert "múltiplas" in result["display_title"]


def test_cross_house_relation_does_not_identify_subject():
    result = describe_voting(voting(), [("object", proposition(source="senado"))])
    assert result["subject_status"] == "unknown"


def test_conflicting_budget_years_preserve_official_summary():
    prop = proposition(summary="Emendas ao Orçamento de 2026 e ao Orçamento de 2027.")
    result = describe_voting(voting(), [("object", prop)])
    assert "2026" in result["display_title"] and "2027" in result["display_title"]
    assert "REL 1/2026" in result["display_title"]
