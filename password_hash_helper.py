"""Create a salted password hash for Streamlit Cloud's private Secrets settings.

Run locally: python password_hash_helper.py
The password is never stored or sent anywhere by this script.
Paste the output under [login_users] in Streamlit Cloud -> App settings -> Secrets.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import secrets

ITERATIONS = 600_000


def create_hash(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Use a strong password of at least 12 characters.")
    salt = secrets.token_bytes(24)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    salt_encoded = base64.urlsafe_b64encode(salt).decode("ascii")
    derived_encoded = base64.urlsafe_b64encode(derived).decode("ascii")
    return f"pbkdf2_sha256${ITERATIONS}${salt_encoded}${derived_encoded}"


def main() -> None:
    user_id = input("User ID (for example, admin): ").strip()
    if not user_id or not user_id.replace("_", "").replace("-", "").isalnum():
        raise SystemExit("User ID must use letters, numbers, underscores or hyphens.")
    pwd1 = getpass.getpass("New password (12+ characters): ")
    pwd2 = getpass.getpass("Confirm password: ")
    if pwd1 != pwd2:
        raise SystemExit("Passwords do not match.")
    try:
        password_hash = create_hash(pwd1)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print("\nPaste this line under [login_users] in Streamlit Cloud Secrets:\n")
    print(f'{user_id} = "{password_hash}"')
    print("\nNever upload your completed Secrets configuration to GitHub.")


if __name__ == "__main__":
    main()
