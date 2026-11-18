"""Chamadas de votação baseadas no objeto explicitamente vinculado pela fonte."""

import re
from collections import defaultdict

from sqlalchemy import select

from app.modules.proposicoes.models import Proposition
from app.modules.votacoes.models import VotingProposition


KINDS = {
    "REL": ("relatório", "o"), "REQ": ("pedido", "o"),
    "PL": ("projeto de lei", "o"), "PLP": ("projeto de lei complementar", "o"),
    "PEC": ("proposta de alteração da Constituição", "a"),
    "MPV": ("medida provisória", "a"), "PDL": ("projeto de decreto legislativo", "o"),
    "PLN": ("projeto de lei do Congresso Nacional", "o"),
    "SBT": ("substitutivo", "o"), "EMC": ("emenda", "a"),
}
GENERIC = re.compile(
    r"^(?:aprovad[ao]s?|rejeitad[ao]s?)(?:\s+(?:o requerimento|a proposta|o projeto|a matéria))?[.!\s]*$",
    re.I,
)


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def subject(prop):
    label = " ".join(str(x) for x in (prop.kind, prop.number) if x)
    if prop.year:
        label += f"/{prop.year}"
    name, gender = KINDS.get(prop.kind, ("proposta", "a"))
    summary = clean(prop.summary)
    # O ano deve estar explicitamente associado ao orçamento, não ao número do PLN.
    budget_years = set(re.findall(
        r"(?:orçamentária anual\s+para|orçamento\s+(?:de|para)|PLOA\s*(?:de|para)?)\s*(20\d{2})\b",
        summary, re.I,
    ))
    if prop.kind == "REL" and len(budget_years) == 1 and re.search(r"\bemendas\b", summary, re.I):
        return f"relatório sobre emendas ao Orçamento de {next(iter(budget_years))}", gender, label, True
    text = f"{name} {label}"
    if summary:
        text += f": {summary.rstrip('.')}"
    return text, gender, label, False


def describe_voting(row, relations=()):
    result = "aprovado" if row.approved is True else "rejeitado" if row.approved is False else "não informado"
    known = {str(prop.id): prop for kind, prop in relations if kind == "object" and prop.source == row.source}
    related = {str(prop.id): prop for kind, prop in relations if kind == "possible_object" and prop.source == row.source}
    official = clean(row.object_description) or clean(row.description)
    generic = not official or bool(GENERIC.fullmatch(official))
    if len(known) == 1:
        prop = next(iter(known.values()))
        topic, gender, label, budget = subject(prop)
        if prop.kind == "REL" and re.fullmatch(
            r"aprovad[ao]\s+nos termos do relat[oó]rio do relator[.!\s]*", official, re.I
        ):
            generic = True
        if generic:
            if row.approved is None:
                title = f"Decisão sobre {topic} — resultado não informado"
            else:
                verb = ("Aprovad" if row.approved else "Rejeitad") + gender
                title = f"{verb} {topic}"
            if budget:
                context = (
                    f"Objeto votado: {label}. O relatório trata de emendas propostas para o orçamento. "
                    "Esta decisão não representa a aprovação do Orçamento inteiro."
                )
            else:
                context = f"Objeto votado: {label}. O resultado se refere a este objeto e a esta etapa do processo legislativo."
        else:
            # Um parecer, destaque ou análise preliminar não aprova a proposição inteira.
            title = f"{official.rstrip('.')} — {topic}"
            context = f"Objeto relacionado à etapa: {label}. O resultado desta votação não permite concluir, sozinho, que a proposição inteira foi aprovada ou virou lei."
        return {"display_title": title, "decision_context": context, "subject_status": "identified"}
    if not known and len(related) == 1:
        topic, _, label, _ = subject(next(iter(related.values())))
        title = f"Resultado {result} em votação relacionada a {topic}"
        if not generic:
            title = f"{official.rstrip('.')} — relacionada a {topic}"
        return {
            "display_title": title,
            "decision_context": f"A fonte registra {label} como objeto possível. Esse vínculo não confirma qual texto foi efetivamente aprovado ou rejeitado.",
            "subject_status": "related",
        }
    if len(known) > 1 or len(related) > 1:
        context = "A fonte associa múltiplas proposições. Não há um objeto único confirmado para esta chamada; consulte as relações e o registro oficial."
        title = f"Votação com múltiplas proposições relacionadas — resultado {result}"
        if not generic:
            title = f"{official.rstrip('.')} — múltiplas proposições relacionadas"
        return {"display_title": title, "decision_context": context, "subject_status": "multiple"}
    return {
        "display_title": f"Votação com resultado {result} — objeto não identificado na coleta" if generic else official,
        "decision_context": "O assunto exato desta decisão ainda não foi identificado nos dados coletados. O resultado geral, sozinho, não explica o que foi votado.",
        "subject_status": "unknown",
    }


def voting_presentations(db, rows):
    """Uma consulta adicional por página, sem consultas externas ou uma consulta por card."""
    if not rows:
        return {}
    relations = defaultdict(list)
    for relation, prop in db.execute(
        select(VotingProposition, Proposition)
        .join(Proposition, Proposition.id == VotingProposition.proposition_id)
        .where(VotingProposition.voting_id.in_([row.id for row in rows]))
        .order_by(VotingProposition.relation_type, Proposition.id)
    ):
        relations[relation.voting_id].append((relation.relation_type, prop))
    return {row.id: describe_voting(row, relations[row.id]) for row in rows}
