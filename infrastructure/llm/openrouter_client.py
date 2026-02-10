import json
from typing import List, Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from infrastructure.config.settings import Settings
from domain.ports.llm import LLM


class OpenRouterLLM(LLM):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.api_key = api_key or Settings.LLM_API_KEY
        self.base_url = (base_url or Settings.LLM_API_URL or "").rstrip("/")
        self.chat_model = chat_model or Settings.OPENROUTER_CHAT_MODEL
        self.embed_model = embed_model or Settings.OPENROUTER_EMBED_MODEL
        self.timeout_seconds = timeout_seconds or Settings.REQUEST_TIMEOUT_SECONDS

        if not self.api_key:
            raise ValueError("Missing OpenRouter API key. Set OPENROUTER_API_KEY.")
        if not self.base_url:
            raise ValueError("Missing OpenRouter base URL. Set LLM_API_URL.")

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as err:
            detail = err.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenRouter error {err.code}: {detail}") from err
        except URLError as err:
            raise RuntimeError(f"OpenRouter connection error: {err}") from err

    def generate(self, prompt: str, max_tokens: int) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]
        return self.chat(messages=messages, max_tokens=max_tokens)

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float = 0.3,
    ) -> str:
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        result = self._post_json("/chat/completions", payload)
        try:
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as err:
            raise RuntimeError(f"Unexpected OpenRouter response: {result}") from err

    def embed(self, texts: List[str]) -> List[List[float]]:
        payload = {
            "model": self.embed_model,
            "input": texts,
        }
        result = self._post_json("/embeddings", payload)
        try:
            data = result["data"]
            return [item["embedding"] for item in data]
        except (KeyError, IndexError) as err:
            raise RuntimeError(f"Unexpected OpenRouter embedding response: {result}") from err
