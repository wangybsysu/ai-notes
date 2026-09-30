"""Anthropic 兼容协议的极简客户端。"""

from __future__ import annotations

import httpx

from .config import resolve_api_key, resolve_base_url, resolve_model


class LLMError(RuntimeError):
    """调用模型失败。"""


def complete(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 512,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    client: httpx.Client | None = None,
) -> str:
    payload: dict = {
        "model": model or resolve_model(),
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    headers = {
        "x-api-key": api_key or resolve_api_key(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    url = f"{(base_url or resolve_base_url()).rstrip('/')}/v1/messages"

    owns_client = client is None
    client = client if client is not None else httpx.Client(timeout=60.0)
    try:
        try:
            response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"请求失败：{exc}") from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code >= 400:
        raise LLMError(f"接口返回 {response.status_code}：{response.text[:200]}")

    blocks = response.json().get("content", [])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if not text:
        raise LLMError("模型返回了空内容")
    return text
