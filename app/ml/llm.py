"""Unified LLM client wrapping OpenAI and Anthropic SDKs."""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.config import Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._provider = settings.LLM_PROVIDER
        self._model = settings.LLM_MODEL
        self._oai_client = None
        self._anth_client = None

        if self._provider == "openai":
            import openai

            self._oai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            import anthropic

            self._anth_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(
        self, system: str, prompt: str, model: str | None = None
    ) -> str:
        model = model or self._model

        if self._oai_client is not None:
            resp = await self._oai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""

        resp = await self._anth_client.messages.create(  # type: ignore[union-attr]
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.content[0].text

    async def complete_json(
        self,
        system: str,
        prompt: str,
        schema: type[BaseModel],
        model: str | None = None,
    ) -> BaseModel:
        system_with_format = (
            system
            + "\n\nYou MUST respond with valid JSON matching this schema:\n"
            + json.dumps(schema.model_json_schema(), indent=2)
        )
        raw = await self.complete(system_with_format, prompt, model)
        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return schema.model_validate_json(text)

    async def describe_image(
        self, image_bytes: bytes, prompt: str, model: str | None = None
    ) -> str:
        model = model or self._model
        b64 = base64.b64encode(image_bytes).decode()

        if self._oai_client is not None:
            resp = await self._oai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}"
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                temperature=0.1,
            )
            return resp.choices[0].message.content or ""

        resp = await self._anth_client.messages.create(  # type: ignore[union-attr]
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            temperature=0.1,
        )
        return resp.content[0].text
