"""Example authentication helper."""

def get_access_token(client_id: str, client_secret: str) -> str:
    """Return a placeholder token for the sample project."""
    if not client_id or not client_secret:
        raise ValueError("client credentials are required")
    return "sample-token"
