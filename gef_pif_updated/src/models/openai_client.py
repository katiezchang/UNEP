from __future__ import annotations
from typing import List, Dict, Optional
import os
from dataclasses import dataclass
from openai import AsyncOpenAI

@dataclass
class ChatMessage:
    role: str
    content: str

class OpenAIClient:
    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            raise RuntimeError("OPENAI_API_KEY missing or not a personal 'sk-' key.")
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = AsyncOpenAI(api_key=api_key)

    def set_model(self, model: str) -> None:
        if model:
            self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def chat(self, messages: List[Dict[str, str] | ChatMessage], temperature: float = 0.0, max_tokens: int = 2800) -> str:
        msgs = []
        for m in messages:
            if isinstance(m, ChatMessage):
                msgs.append({"role": m.role, "content": m.content})
            else:
                msgs.append(m)
        resp = await self.client.chat.completions.create(
            model=self._model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
