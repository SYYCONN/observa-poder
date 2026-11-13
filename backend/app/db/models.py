"""Registro explícito de modelos para as migrations; sem acesso externo."""

from app.modules.analytics.models import DailyMetric
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import (
    ElectionResult,
    Mandate,
    MandateObservation,
    Parliamentarian,
)
from app.modules.proposicoes.models import (
    Authorship,
    CitizenExplanationRun,
    ProceedingsEvent,
    Proposition,
    PropositionCitizenExplanation,
)
from app.modules.votacoes.models import Vote, Voting, VotingProposition
from app.modules.financas.models import (
    ParliamentaryAmendment,
    ParliamentaryAmendmentSummary,
    ParliamentaryExpense,
    ParliamentaryRemuneration,
    ParliamentaryStaffSummary,
    ParliamentaryStaffMember,
)

__all__ = [
    "DailyMetric",
    "ImportRun",
    "SourceRecord",
    "Mandate",
    "MandateObservation",
    "ElectionResult",
    "Parliamentarian",
    "Authorship",
    "CitizenExplanationRun",
    "ProceedingsEvent",
    "Proposition",
    "PropositionCitizenExplanation",
    "Vote",
    "Voting",
    "VotingProposition",
    "ParliamentaryExpense",
    "ParliamentaryAmendment",
    "ParliamentaryAmendmentSummary",
    "ParliamentaryRemuneration",
    "ParliamentaryStaffSummary",
    "ParliamentaryStaffMember",
]
