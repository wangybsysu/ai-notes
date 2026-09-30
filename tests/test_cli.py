from typer.testing import CliRunner

from ai_notes.cli import app
from ai_notes.llm import LLMError

runner = CliRunner()


def test_summarize_正常执行(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("正文", encoding="utf-8")
    monkeypatch.setattr("ai_notes.cli.complete", lambda prompt, **kw: "摘要内容")
    result = runner.invoke(app, ["summarize", str(tmp_path)])
    assert result.exit_code == 0
    assert "已更新 1 篇" in result.stdout


def test_dry_run_提示将更新(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("正文", encoding="utf-8")
    monkeypatch.setattr("ai_notes.cli.complete", lambda prompt, **kw: "摘要")
    result = runner.invoke(app, ["summarize", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0
    assert "将更新" in result.stdout


def test_目录不存在时退出码为1(tmp_path):
    result = runner.invoke(app, ["summarize", str(tmp_path / "nope")])
    assert result.exit_code == 1


def test_tag_子命令可执行(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("正文", encoding="utf-8")
    monkeypatch.setattr("ai_notes.cli.complete", lambda prompt, **kw: "python, 笔记")
    result = runner.invoke(app, ["tag", str(tmp_path)])
    assert result.exit_code == 0
    assert "python" in (tmp_path / "a.md").read_text(encoding="utf-8")


def test_模型调用失败时给出可读错误而非堆栈(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("正文", encoding="utf-8")

    def boom(prompt, **kw):
        raise LLMError("请求失败：连接被拒绝")

    monkeypatch.setattr("ai_notes.cli.complete", boom)
    result = runner.invoke(app, ["summarize", str(tmp_path)])

    assert result.exit_code == 1
    assert "调用模型失败：请求失败：连接被拒绝" in (result.output + result.stderr)
    # 必须经由受控退出终止（typer.Exit 会被翻译成 SystemExit），
    # 而不是让 LLMError 裸奔到用户界面变成一堆堆栈
    assert isinstance(result.exception, SystemExit)


def test_dry_run_打印将写入的值(tmp_path, monkeypatch):
    path = (tmp_path / "a.md")
    path.write_text("正文", encoding="utf-8")
    monkeypatch.setattr("ai_notes.cli.complete", lambda prompt, **kw: "这是摘要")

    result = runner.invoke(app, ["summarize", str(tmp_path), "--dry-run"])

    assert result.exit_code == 0
    assert "这是摘要" in result.stdout  # 要能看出「改成什么样」，不只是「改哪篇」
    assert path.read_text(encoding="utf-8") == "正文"


def test_中途失败时报告已改动的篇数(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("正文一", encoding="utf-8")
    (tmp_path / "b.md").write_text("正文二", encoding="utf-8")

    calls = {"n": 0}

    def flaky(prompt, **kw):
        calls["n"] += 1
        if calls["n"] == 2:
            raise LLMError("接口返回 401：bad key")
        return "摘要"

    monkeypatch.setattr("ai_notes.cli.complete", flaky)
    result = runner.invoke(app, ["summarize", str(tmp_path)])

    assert result.exit_code == 1
    combined = result.output + result.stderr
    # 批量改了几百篇笔记时，失败后必须说清已经动过哪些
    assert "1 篇" in combined
    assert "a.md" in combined
