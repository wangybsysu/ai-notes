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

    # 中转站过载时常常回一个 2xx 的 HTML 错误页，或者结构完全不对的 JSON。
    # 这里全部收敛成 LLMError，否则会把 JSONDecodeError / AttributeError 直接
    # 抛到用户面前变成一堆堆栈。
    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMError(
            f"接口返回 {response.status_code}，但响应不是 JSON：{response.text[:200]}"
        ) from exc
    if not isinstance(payload, dict):
        raise LLMError(f"接口返回的 JSON 结构不是对象：{str(payload)[:200]}")

    blocks = payload.get("content", [])
    if not isinstance(blocks, list):
        raise LLMError(f"响应里的 content 不是列表：{str(blocks)[:200]}")

    text = "".join(
        b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
    ).strip()
    if not text:
        raise LLMError("模型返回了空内容")
    return text
