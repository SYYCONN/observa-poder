"""Apply schema revisions and grant only the privileges used by the public release."""

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db.session import get_engine

READ_TABLES = (
    "parliamentarians", "mandates", "mandate_observations", "election_results",
    "propositions", "proposition_citizen_explanations", "authorships", "proceedings_events",
    "votings", "voting_propositions", "votes", "parliamentary_expenses",
    "parliamentary_remunerations", "parliamentary_staff_summaries",
    "parliamentary_staff_members", "parliamentary_amendments", "parliamentary_amendment_summaries",
)


def main() -> None:
    command.upgrade(Config("alembic.ini"), "head")
    with get_engine().begin() as db:
        db.execute(text("GRANT SELECT ON " + ", ".join(READ_TABLES) + " TO observa_read"))
        db.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON " + ", ".join(
            (*READ_TABLES, "import_runs", "source_records")
        ) + " TO observa_collect"))


if __name__ == "__main__":
    main()
