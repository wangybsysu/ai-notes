"""笔记的发现、提示词构造与落盘。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import frontmatter

MAX_BODY_CHARS = 8000


@dataclass
class Note:
    path: Path
    post: frontmatter.Post


def iter_notes(root: Path) -> Iterator[Note]:
    """递归收集 Markdown 笔记。

    解析失败、正文为空或纯空白的文件直接跳过，不中断整批处理。
    """
    for path in sorted(Path(root).rglob("*.md")):
        if path.name.startswith("."):
            continue
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        if not post.content.strip():
            continue
        yield Note(path=path, post=post)


def _body(note: Note, max_chars: int = MAX_BODY_CHARS) -> str:
    body = note.post.content.strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n…（正文过长，已截断）"
    return body


def summary_prompt(note: Note, max_chars: int = MAX_BODY_CHARS) -> str:
    return (
        "用一到两句话概括下面这篇笔记的要点。"
        "直接输出摘要本身，不要任何前缀或解释。\n\n"
        f"{_body(note, max_chars)}"
    )


def tag_prompt(note: Note, max_chars: int = MAX_BODY_CHARS) -> str:
    return (
        "为下面这篇笔记给出 3 到 5 个标签，用英文逗号分隔。"
        "只输出标签本身。\n\n"
        f"{_body(note, max_chars)}"
    )


def save_note(note: Note) -> None:
    note.path.write_text(frontmatter.dumps(note.post), encoding="utf-8")


def apply_to_notes(
    root: Path,
    mode: str,
    llm: Callable[[str], str],
    *,
    dry_run: bool = False,
    limit: int | None = None,
) -> list[Path]:
    """mode 为 "summary" 或 "tag"。返回被处理（或将被处理）的文件路径。"""
    if mode not in {"summary", "tag"}:
        raise ValueError(f"未知的 mode：{mode}")

    changed: list[Path] = []
    for index, note in enumerate(iter_notes(root)):
        if limit is not None and index >= limit:
            break
        prompt = summary_prompt(note) if mode == "summary" else tag_prompt(note)
        result = llm(prompt).strip()
        if mode == "summary":
            note.post["summary"] = result
        else:
            note.post["tags"] = [
                t.strip() for t in result.replace("，", ",").split(",") if t.strip()
            ]
        if not dry_run:
            save_note(note)
        changed.append(note.path)
    return changed
