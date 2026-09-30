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

    以下情况直接跳过，不中断整批处理：

    - 解析失败的文件
    - 正文为空或纯空白的文件
    - 有 front-matter 块、但解析出来是空的文件——`---` 块里如果是列表或标量
      （顶层不是映射），frontmatter 会返回空的 metadata，此时整块内容都不在
      post 里，回写等于把它们删掉。宁可不处理，也不能丢用户的东西。
    """
    for path in sorted(Path(root).rglob("*.md")):
        if path.name.startswith("."):
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        has_block = raw.lstrip().startswith("---")
        try:
            post = frontmatter.loads(raw)
        except Exception:
            continue
        if not post.content.strip():
            continue
        if has_block and not post.metadata:
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
    on_change: Callable[[Path, str], None] | None = None,
) -> list[Path]:
    """mode 为 "summary" 或 "tag"。返回被处理（或将被处理）的文件路径。

    on_change 在每个文件处理完（dry_run 下为「将要处理完」）后调用一次，
    参数是文件路径与本次得到的值。批量跑到一半失败时，调用方靠它才知道
    已经动过哪些文件。
    """
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
        if on_change is not None:
            on_change(note.path, result)
    return changed
