from __future__ import annotations

import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional, Dict, Any

import jwt

from backend.config import settings
from backend.db.mongodb import db_instance


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.utcnow()


def create_access_token(user_id: str, email: str) -> str:
    expires_at = _utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expires_at,
        "iat": _utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


async def create_magic_link_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = _utcnow() + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)

    await db_instance.db["auth_tokens"].insert_one({
        "token_hash": token_hash,
        "email": email.lower().strip(),
        "expires_at": expires_at,
        "used": False,
        "created_at": _utcnow(),
    })

    return token


async def verify_magic_link_token(token: str) -> Optional[str]:
    token_hash = _hash_token(token)
    now = _utcnow()
    record = await db_instance.db["auth_tokens"].find_one({
        "token_hash": token_hash,
        "used": False,
        "expires_at": {"$gt": now},
    })
    if not record:
        return None

    await db_instance.db["auth_tokens"].update_one(
        {"_id": record["_id"]},
        {"$set": {"used": True, "used_at": now}}
    )
    return record["email"]


async def get_or_create_user(email: str) -> Dict[str, Any]:
    normalized = email.lower().strip()
    user = await db_instance.db["users"].find_one({"email": normalized})
    if user:
        await db_instance.db["users"].update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login_at": _utcnow()}}
        )
        return {"id": str(user["_id"]), "email": user["email"]}

    result = await db_instance.db["users"].insert_one({
        "email": normalized,
        "created_at": _utcnow(),
        "last_login_at": _utcnow(),
    })
    return {"id": str(result.inserted_id), "email": normalized}


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    from bson.objectid import ObjectId

    user = await db_instance.db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        return None
    return {"id": str(user["_id"]), "email": user["email"]}


async def create_refresh_token(user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    expires_at = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    await db_instance.db["refresh_tokens"].insert_one({
        "token_hash": token_hash,
        "user_id": user_id,
        "expires_at": expires_at,
        "created_at": _utcnow(),
        "revoked": False,
    })
    return token


async def revoke_refresh_token(token: str) -> None:
    token_hash = _hash_token(token)
    await db_instance.db["refresh_tokens"].update_one(
        {"token_hash": token_hash},
        {"$set": {"revoked": True, "revoked_at": _utcnow()}}
    )


async def get_user_from_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    token_hash = _hash_token(token)
    now = _utcnow()
    record = await db_instance.db["refresh_tokens"].find_one({
        "token_hash": token_hash,
        "revoked": False,
        "expires_at": {"$gt": now},
    })
    if not record:
        return None
    return await get_user_by_id(record["user_id"])


def send_magic_link(email: str, token: str) -> None:
    if not settings.SMTP_HOST:
        print("SMTP not configured; skipping email send")
        return

    link = f"{settings.FRONTEND_ORIGIN}/auth?token={token}"
    msg = EmailMessage()
    msg["Subject"] = f"Your sign-in link for {settings.APP_NAME}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = email
    msg.set_content(
        "Use the link below to sign in. If you did not request this, ignore this email.\n\n"
        f"{link}\n\n"
        f"This link expires in {settings.MAGIC_LINK_EXPIRE_MINUTES} minutes."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
