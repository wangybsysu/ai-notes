from ai_notes.notes import apply_to_notes, iter_notes


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_只收集_markdown_并递归(tmp_path):
    write(tmp_path, "a.md", "---\ntitle: a\n---\n内容")
    write(tmp_path, "b.txt", "忽略")
    write(tmp_path, "sub/c.md", "没有 front matter 的正文")
    assert [n.path.name for n in iter_notes(tmp_path)] == ["a.md", "c.md"]


def test_跳过隐藏文件(tmp_path):
    write(tmp_path, ".draft.md", "隐藏")
    assert list(iter_notes(tmp_path)) == []


def test_空文件与纯空白文件被跳过(tmp_path):
    write(tmp_path, "empty.md", "")
    write(tmp_path, "blank.md", "   \n\n  ")
    assert list(iter_notes(tmp_path)) == []


def test_summary_写入_front_matter(tmp_path):
    path = write(tmp_path, "a.md", "---\ntitle: a\n---\n正文")
    changed = apply_to_notes(tmp_path, "summary", lambda _prompt: "一篇摘要")
    assert changed == [path]
    assert "summary: 一篇摘要" in path.read_text(encoding="utf-8")


def test_无_front_matter_也能写入(tmp_path):
    path = write(tmp_path, "a.md", "裸正文")
    apply_to_notes(tmp_path, "summary", lambda _prompt: "摘要")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "summary: 摘要" in text
    assert "裸正文" in text


def test_tags_同时拆分中英文逗号(tmp_path):
    path = write(tmp_path, "a.md", "正文")
    apply_to_notes(tmp_path, "tag", lambda _prompt: "python, 笔记，工具")
    text = path.read_text(encoding="utf-8")
    assert "python" in text and "笔记" in text and "工具" in text


def test_dry_run_不落盘(tmp_path):
    path = write(tmp_path, "a.md", "正文")
    before = path.read_text(encoding="utf-8")
    apply_to_notes(tmp_path, "summary", lambda _prompt: "摘要", dry_run=True)
    assert path.read_text(encoding="utf-8") == before


def test_limit_限制处理数量(tmp_path):
    for i in range(3):
        write(tmp_path, f"n{i}.md", "正文")
    changed = apply_to_notes(tmp_path, "summary", lambda _prompt: "摘要", limit=2)
    assert len(changed) == 2


def test_前置元数据不是映射时整篇跳过而不是抹掉内容(tmp_path):
    """`---` 块里是列表/标量时，frontmatter 解析出的 metadata 是空 dict，
    直接回写会把整块原内容删掉——这是不可逆的用户数据丢失。"""
    path = write(tmp_path, "a.md", "---\n- 待办一\n- 待办二\n---\n正文")
    before = path.read_text(encoding="utf-8")

    changed = apply_to_notes(tmp_path, "summary", lambda _prompt: "摘要")

    assert changed == []
    assert path.read_text(encoding="utf-8") == before


def test_前置元数据是标量时也跳过(tmp_path):
    path = write(tmp_path, "a.md", "---\nhello\n---\n正文")
    before = path.read_text(encoding="utf-8")

    apply_to_notes(tmp_path, "summary", lambda _prompt: "摘要")

    assert path.read_text(encoding="utf-8") == before


def test_超长正文被截断后才送模型(tmp_path):
    write(tmp_path, "a.md", "字" * 20000)
    seen = {}

    def fake_llm(prompt: str) -> str:
        seen["prompt"] = prompt
        return "摘要"

    apply_to_notes(tmp_path, "summary", fake_llm)
    assert len(seen["prompt"]) < 20000
