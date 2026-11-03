import asyncio
import json
import os
from typing import Optional

import httpx

class LLMRouter:
    """Universal LLM client for Screenwriter, CharacterExtractor, and StoryboardArtist.
    Prioritizes local 9Router / OpenAI-compatible endpoint (zero cost),
    with fallback to MuAPI if explicitly configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or "http://localhost:20128/v1"
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("LLM_MODEL", "gh/gpt-4o")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 120,
        fallback: Optional[str] = None,
    ) -> str:
        """Execute chat completion via 9Router / OpenAI compatible API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                
                # Handle possible multi-line responses from proxies
                raw_text = resp.text.strip()
                try:
                    data = resp.json()
                except Exception:
                    data = json.loads(raw_text.split("\n")[0])

                content = data["choices"][0]["message"]["content"]
                if content and str(content).strip():
                    return str(content).strip()
                elif fallback is not None:
                    return fallback
                return str(content or "")

        except Exception as e:
            print(f"[LLMRouter] Error calling {self.base_url} ({self.model}): {e}")
            if fallback is not None:
                print(f"[LLMRouter] Using fallback response.")
                return fallback
            raise e
