import json

import httpx
import pytest

from ai_notes.llm import LLMError, complete

# 显式钉住，避免测试意外依赖 config.py 里的默认值（那是注入点，不是被测行为）
BASE = {"api_key": "sk-test", "base_url": "https://relay.example"}


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_拼接文本块并去空白():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "sk-test"
        return httpx.Response(200, json={"content": [{"type": "text", "text": " 你好 "}]})

    out = complete("hi", **BASE, client=make_client(handler))
    assert out == "你好"


def test_基地址带尾斜杠不产生双斜杠():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    complete("hi", **{**BASE, "base_url": "https://relay.example/"}, client=make_client(handler))
    assert seen["url"] == "https://relay.example/v1/messages"


def test_请求体包含_system_与消息():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    complete("hi", **BASE, system="你是助手", client=make_client(handler))
    assert captured["system"] == "你是助手"
    assert captured["messages"][0]["content"] == "hi"


def test_非2xx_抛_LLMError():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad key")

    with pytest.raises(LLMError, match="401"):
        complete("hi", **BASE, client=make_client(handler))


def test_空内容抛错():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": []})

    with pytest.raises(LLMError, match="空内容"):
        complete("hi", **BASE, client=make_client(handler))


def test_网络异常包装为_LLMError():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(LLMError, match="请求失败"):
        complete("hi", **BASE, client=make_client(handler))
