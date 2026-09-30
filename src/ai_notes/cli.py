"""命令行入口：ai-notes summarize / tag。"""

from __future__ import annotations

from pathlib import Path

import typer

from .llm import LLMError, complete
from .notes import apply_to_notes

app = typer.Typer(add_completion=False, help="用 LLM 给本地 Markdown 笔记补摘要与标签。")


def _run(root: Path, mode: str, dry_run: bool, limit: int | None) -> None:
    if not root.exists():
        typer.echo(f"目录不存在：{root}", err=True)
        raise typer.Exit(code=1)

    done: list[Path] = []

    def on_change(path: Path, value: str) -> None:
        done.append(path)
        if dry_run:
            # dry-run 要能看出「改成什么样」，不只是「改哪篇」
            typer.echo(f"  {path}")
            typer.echo(f"      {value}")

    try:
        changed = apply_to_notes(
            root,
            mode,
            lambda prompt: complete(prompt),
            dry_run=dry_run,
            limit=limit,
            on_change=on_change,
        )
    except LLMError as exc:
        if done:
            typer.echo(f"已处理 {len(done)} 篇后中止，以下文件已被改动：", err=True)
            for path in done:
                typer.echo(f"  {path}", err=True)
        typer.echo(f"调用模型失败：{exc}", err=True)
        raise typer.Exit(code=1) from exc

    verb = "将更新" if dry_run else "已更新"
    typer.echo(f"{verb} {len(changed)} 篇笔记")
    if not dry_run:
        for path in changed:
            typer.echo(f"  {path}")


@app.command()
def summarize(
    root: Path = typer.Argument(Path("."), help="笔记根目录"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只打印不写回"),
    limit: int | None = typer.Option(None, "--limit", help="最多处理多少篇"),
) -> None:
    """为每篇笔记写入 front-matter 字段 summary。"""
    _run(root, "summary", dry_run, limit)


@app.command()
def tag(
    root: Path = typer.Argument(Path("."), help="笔记根目录"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只打印不写回"),
    limit: int | None = typer.Option(None, "--limit", help="最多处理多少篇"),
) -> None:
    """为每篇笔记写入 front-matter 字段 tags。"""
    _run(root, "tag", dry_run, limit)


def main() -> None:
    app()
