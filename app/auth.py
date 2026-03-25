"""Firebase-backed authentication helpers for protected platform routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import firebase_admin
from fastapi import Header, HTTPException, status
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import FirebaseError

from app.settings import load_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AuthenticatedUser:
    """Authenticated platform user extracted from Firebase claims."""

    uid: str
    email: str | None
    claims: dict[str, Any]


def _auth_disabled_user() -> AuthenticatedUser:
    return AuthenticatedUser(uid="local-dev", email=None, claims={"auth_disabled": True})


def _auth_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": message, "code": "auth_required"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _auth_error("A Firebase bearer token is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _auth_error("Use Authorization: Bearer <firebase_id_token>.")
    return token.strip()


@lru_cache(maxsize=1)
def get_firebase_app() -> firebase_admin.App:
    settings = load_settings()
    project_id = settings.firebase_project_id
    if not project_id:
        raise RuntimeError("Firebase auth is enabled but no Firebase project id is configured.")

    app_name = "boq-auto-api"
    try:
        return firebase_admin.get_app(app_name)
    except ValueError:
        logger.info("Initializing Firebase Admin for project %s", project_id)
        return firebase_admin.initialize_app(options={"projectId": project_id}, name=app_name)


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    return firebase_auth.verify_id_token(id_token, app=get_firebase_app(), check_revoked=False)


def require_authenticated_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    settings = load_settings()
    if not settings.firebase_auth_enabled:
        return _auth_disabled_user()

    token = _extract_bearer_token(authorization)
    try:
        claims = verify_firebase_token(token)
    except ValueError as exc:
        logger.warning("Firebase auth setup error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Firebase auth is not configured correctly on the API.", "code": "auth_unavailable"},
        ) from exc
    except (firebase_auth.InvalidIdTokenError, firebase_auth.ExpiredIdTokenError, FirebaseError) as exc:
        logger.info("Rejected Firebase token: %s", exc)
        raise _auth_error("The Firebase session is invalid or expired. Sign in again.")

    return AuthenticatedUser(
        uid=str(claims.get("uid", "")),
        email=claims.get("email"),
        claims=claims,
    )
