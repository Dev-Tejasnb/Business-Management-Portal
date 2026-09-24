"""Server-side session store for refresh tokens.

Refresh tokens are opaque values; only their SHA-256 hash is ever stored, keyed
in Redis with a TTL. This enables revocation (logout) and prevents replay of
revoked sessions. An in-memory implementation is provided for tests and local
development where Redis is unavailable.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis

from app.core.security import refresh_token_ttl_seconds


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionStore(ABC):
    """Abstraction over where refresh sessions are persisted."""

    @abstractmethod
    async def create(self, user_id: int) -> tuple[str, int]:
        """Create a session for a user, returning (token, ttl_seconds)."""

    @abstractmethod
    async def validate(self, token: str) -> int | None:
        """Return the user id if the token is valid and unexpired, else None."""

    @abstractmethod
    async def revoke(self, token: str) -> bool:
        """Revoke a single session. Returns True if a session was removed."""

    @abstractmethod
    async def revoke_all_for_user(self, user_id: int) -> int:
        """Revoke all sessions for a user, returning the number removed."""


class RedisSessionStore(SessionStore):
    """Redis-backed session store. Keys are SHA-256 hashes of tokens."""

    KEY_PREFIX = "bmp:refresh"

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, token: str) -> str:
        return f"{self.KEY_PREFIX}:{_hash_token(token)}"

    def _user_key(self, user_id: int) -> str:
        return f"{self.KEY_PREFIX}:user:{user_id}"

    async def create(self, user_id: int) -> tuple[str, int]:
        from app.core.security import generate_refresh_token

        token = generate_refresh_token()
        ttl = refresh_token_ttl_seconds()
        await self._redis.set(
            self._key(token),
            json.dumps({"user_id": user_id}),
            ex=ttl,
        )
        await self._redis.sadd(self._user_key(user_id), self._key(token))
        await self._redis.expire(self._user_key(user_id), ttl)
        return token, ttl

    async def validate(self, token: str) -> int | None:
        raw = await self._redis.get(self._key(token))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return int(data["user_id"])
        except (ValueError, KeyError, TypeError):
            return None

    async def revoke(self, token: str) -> bool:
        key = self._key(token)
        raw = await self._redis.get(key)
        if not raw:
            return False
        try:
            user_id = int(json.loads(raw)["user_id"])
        except (ValueError, KeyError, TypeError):
            user_id = None
        await self._redis.delete(key)
        if user_id is not None:
            await self._redis.srem(self._user_key(user_id), key)
        return True

    async def revoke_all_for_user(self, user_id: int) -> int:
        user_key = self._user_key(user_id)
        keys = await self._redis.smembers(user_key)
        if keys:
            await self._redis.delete(*keys)
        await self._redis.delete(user_key)
        return len(keys)


class InMemorySessionStore(SessionStore):
    """Thread-safe in-memory store for tests/local dev. Not for production."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._user_sessions: dict[int, set[str]] = {}

    async def create(self, user_id: int) -> tuple[str, int]:
        from app.core.security import generate_refresh_token

        token = generate_refresh_token()
        ttl = refresh_token_ttl_seconds()
        self._sessions[_hash_token(token)] = {
            "user_id": user_id,
            "exp": (datetime.now(UTC) + timedelta(seconds=ttl)).timestamp(),
        }
        self._user_sessions.setdefault(user_id, set()).add(_hash_token(token))
        return token, ttl

    async def validate(self, token: str) -> int | None:
        session = self._sessions.get(_hash_token(token))
        if not session:
            return None
        if session["exp"] < datetime.now(UTC).timestamp():
            await self.revoke(token)
            return None
        return int(session["user_id"])

    async def revoke(self, token: str) -> bool:
        key = _hash_token(token)
        session = self._sessions.pop(key, None)
        if session is None:
            return False
        user_sessions = self._user_sessions.get(int(session["user_id"]), set())
        user_sessions.discard(key)
        return True

    async def revoke_all_for_user(self, user_id: int) -> int:
        keys = self._user_sessions.pop(user_id, set())
        for key in keys:
            self._sessions.pop(key, None)
        return len(keys)


def get_session_store(redis: Redis | None = None) -> SessionStore:
    """Return a Redis-backed store, or an in-memory fallback if Redis is absent."""
    if redis is None:
        return InMemorySessionStore()
    return RedisSessionStore(redis)