import hashlib
import hmac
import os
import secrets

from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AdminUser

COOKIE = "rd_session"
MAX_AGE = 60 * 60 * 12


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("SESSION_SECRET", "request-desk-local-demo-secret")
    return URLSafeTimedSerializer(secret, salt="request-desk-session")


def make_token(username: str) -> str:
    return _serializer().dumps({"u": username})


def read_token(token: str) -> str | None:
    try:
        data = _serializer().loads(token, max_age=MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    username = data.get("u") if isinstance(data, dict) else None
    return username if isinstance(username, str) else None


def current_user(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    token = request.cookies.get(COOKIE)
    username = read_token(token) if token else None
    if not username:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    user = db.query(AdminUser).filter(AdminUser.username == username).one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return user


_DUMMY_STORED = hash_password("request-desk-unused")


def check_password(password: str, user: AdminUser | None) -> bool:
    if user is None:
        verify_password(password, _DUMMY_STORED)
        return False
    return verify_password(password, user.password_hash)
