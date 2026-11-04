"""Fixture: structural pattern matching (Python 3.10+). Counting convention is
engine-dependent, so tests expect a visible warning and a loose value."""


def http_status(code):  # START http_status
    match code:
        case 200:
            return "ok"
        case 404:
            return "not found"
        case _:
            return "other"  # END http_status
