import os


def generate_request(method, params: list | dict | None = None, version: str = "2.0") -> dict:
    """Generate a JSON-RPC request."""
    if params is None:
        params = []

    return {
        "jsonrpc": version,
        "method": method,
        "params": params,
        "id": int.from_bytes(os.urandom(4), 'big'),
    }

