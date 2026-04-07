# Standard Library
import base64
import os
import secrets

API_KEY_FILE = "data/.api_key"


def generate_api_key():
    """Generate a secure API key using different methods."""

    # Method 1: 32 bytes of random data -> 64 character hex string
    hex_key = secrets.token_hex(32)

    # Method 2: 32 bytes of random data -> 44 character base64 string
    base64_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

    # Method 3: Combine random bytes with a prefix for easier identification
    prefixed_key = f"bm_{''.join(secrets.token_urlsafe(32))}"

    return prefixed_key  # or hex_key or base64_key


# Use it in your get_or_create_api_key function
def get_or_create_api_key():
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            return f.read().strip()

    api_key = generate_api_key()
    os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
    with open(API_KEY_FILE, "w") as f:
        f.write(api_key)

    print(f"Generated new API key: {api_key}")  # For first-time setup
    return api_key
