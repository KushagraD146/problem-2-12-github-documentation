"""Example client module used to demonstrate documentation impact matching."""

def create_client(base_url: str, timeout_seconds: int = 10):
    """Create a client using the configured API endpoint and timeout."""
    return {"base_url": base_url, "timeout_seconds": timeout_seconds}
