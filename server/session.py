import secrets

def generate_session_id() -> str:
    return secrets.token_hex()
