from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class GroqClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=6), stop=stop_after_attempt(3), reraise=True)
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.enabled:
            raise RuntimeError("Groq API key is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": "Bearer " + self.api_key}
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
