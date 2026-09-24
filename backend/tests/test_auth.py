"""Tests for the authentication flow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient

from app.core.config import get_settings


async def test_login_success(client: AsyncClient, create_user) -> None:
    await create_user("alice@example.com", password="Password123!")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "Password123!"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "alice@example.com"
    assert "hashed_password" not in body["user"]
    assert "refresh_token" not in body
    # Refresh token is delivered as an HTTP-only cookie.
    cookie = resp.cookies.get(get_settings().AUTH_COOKIE_NAME)
    assert cookie


async def test_login_invalid_password(client: AsyncClient, create_user) -> None:
    await create_user("alice@example.com", password="Password123!")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "WrongPass1"}
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "Password123!"}
    )
    assert resp.status_code == 401


async def test_login_inactive_user_rejected(client: AsyncClient, create_user) -> None:
    await create_user("inactive@example.com", active=False)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 401


async def test_current_user(client: AsyncClient, create_user, login) -> None:
    await create_user("alice@example.com")
    await login("alice@example.com")
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


async def test_me_rejects_missing_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_rejects_invalid_token(client: AsyncClient) -> None:
    client.headers["Authorization"] = "Bearer not-a-valid-token"
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_rejects_expired_token(client: AsyncClient, create_user) -> None:
    user = await create_user("alice@example.com")
    settings = get_settings()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "type": "access",
            "iat": int((now - timedelta(hours=1)).timestamp()),
            "exp": int((now - timedelta(minutes=30)).timestamp()),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    client.headers["Authorization"] = f"Bearer {expired}"
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_refresh_flow(client: AsyncClient, create_user, login) -> None:
    await create_user("alice@example.com")
    await login("alice@example.com")
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_requires_valid_session(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_logout_revokes_session(client: AsyncClient, create_user, login) -> None:
    await create_user("alice@example.com")
    await login("alice@example.com")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200

    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # After logout, the refresh session is revoked: refresh now fails.
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_requires_authentication(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/auth/logout")).status_code == 401