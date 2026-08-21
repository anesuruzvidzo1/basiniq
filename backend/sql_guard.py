"""Guard for LLM-generated SQL.

Deliberately dependency free. router.py pulls in sentence-transformers and an
Anthropic client at import time, so anything defined there is impractical to
import from a test. Keeping the guard here lets the tests exercise the real
function instead of a copy of it.
"""


def is_select_only(sql: str) -> bool:
    """True only when the statement is a bare SELECT.

    A leading comment is rejected on purpose: it can hide a second statement
    from a naive prefix check.
    """
    return sql.strip().upper().startswith("SELECT")
