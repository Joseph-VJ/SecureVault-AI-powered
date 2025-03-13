import os
from cryptography.fernet import Fernet

def generate_fernet_key() -> bytes:
    """Generate a Fernet key."""
    return Fernet.generate_key()

def load_fernet_key(path: str) -> bytes:
    """Load a Fernet key from a file."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Key file not found: {path}")
    except Exception as e:
        raise IOError(f"Error loading key: {str(e)}")

def generate_aes_key(size: int = 32) -> bytes:
    """Generate an AES key of specified size (16, 24, or 32 bytes)."""
    if size not in (16, 24, 32):
        raise ValueError("AES key size must be 16, 24, or 32 bytes")
    return os.urandom(size)

def generate_key(method="Fernet", size=32):
    """Generate a cryptographic key based on the specified method."""
    if method == "Fernet":
        return generate_fernet_key()
    elif method == "AES":
        return generate_aes_key(size)
    else:
        raise ValueError(f"Unsupported key generation method: {method}")
