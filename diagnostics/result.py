def make_result(key, name, status, summary, duration_ms=0, details=None):
    """Create one JSON-friendly diagnostic result."""
    return {
        "key": key,
        "name": name,
        "status": status,
        "summary": summary,
        "duration_ms": duration_ms,
        "details": details or {},
    }


def skipped_result(key, name, reason):
    return make_result(key, name, "skipped", reason)
