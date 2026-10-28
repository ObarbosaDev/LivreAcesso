"""Convites administrativos enviados pelo Supabase Auth sem expor segredo ao cliente."""

import httpx2

from backend.app.shared.application.exceptions import PersistenceUnavailableError


class SupabaseInvitationService:
    def __init__(self, url: str, service_role_key: str) -> None:
        self._url = url.rstrip("/")
        self._client = httpx2.AsyncClient(timeout=httpx2.Timeout(15.0))
        self._headers = {"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}"}

    async def invite(self, email: str, full_name: str) -> None:
        try:
            response = await self._client.post(
                f"{self._url}/auth/v1/invite",
                headers=self._headers,
                json={"email": email, "data": {"full_name": full_name}},
            )
        except httpx2.HTTPError as error:
            raise PersistenceUnavailableError from error
        if response.status_code >= 400:
            raise PersistenceUnavailableError

    async def generate_link(self, email: str, full_name: str) -> str:
        try:
            response = await self._client.post(
                f"{self._url}/auth/v1/admin/generate_link",
                headers=self._headers,
                json={"type": "invite", "email": email, "data": {"full_name": full_name}},
            )
        except httpx2.HTTPError as error:
            raise PersistenceUnavailableError from error
        if response.status_code >= 400:
            raise PersistenceUnavailableError
        payload = response.json()
        action_link = payload.get("action_link") if isinstance(payload, dict) else None
        if not isinstance(action_link, str) or not action_link:
            raise PersistenceUnavailableError
        return action_link

    async def close(self) -> None:
        await self._client.aclose()
