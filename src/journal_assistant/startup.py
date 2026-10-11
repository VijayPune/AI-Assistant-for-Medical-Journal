"""Small startup routine used by the future UI and by the Step 1 check."""

from .configuration import load_journal_config


def startup_message() -> str:
    journal = load_journal_config()
    return (
        f"READY: {journal.display_name} | {journal.corpus_title} "
        f"(Vol. {journal.volume}, Issue {journal.issue_number})"
    )
