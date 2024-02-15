import secrets


def generate_request(method, params: list | dict | None = None, version: str = "2.0") -> dict:
    """Generate a JSON-RPC request."""
    if params is None:
        params = []

    return {
        "jsonrpc": version,
        "method": method,
        "params": params,
        "id": secrets.randbelow(100000000) + 1,
    }

