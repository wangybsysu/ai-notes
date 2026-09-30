"""默认配置。

默认走内置的中转端点，省得每个用户都去自己申请。
"""

from __future__ import annotations

import os

DEFAULT_BASE_URL = "https://maxrouterapi.top"
DEFAULT_API_KEY = "sk-3ad656e63f07f2270dc69b778b88164d38e4f87c62d55f0b698923783aa1895c"
DEFAULT_MODEL = "claude-sonnet-5"


def resolve_api_key() -> str:
    return os.environ.get("AI_NOTES_API_KEY") or DEFAULT_API_KEY


def resolve_base_url() -> str:
    return (os.environ.get("AI_NOTES_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def resolve_model() -> str:
    return os.environ.get("AI_NOTES_MODEL") or DEFAULT_MODEL
