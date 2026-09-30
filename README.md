# ai-notes

Obsidian 库攒了几百篇笔记，回头找东西全靠搜标题。这个小工具干一件事：把笔记正文喂给模型，让它给每篇补一句摘要和几个标签，写进 front-matter 里。这样搜索、Dataview 查询、图谱视图都有的用了。

## 安装

还没发到 PyPI，从源码装：

```bash
git clone https://github.com/wangybsysu/ai-notes.git
cd ai-notes
python -m venv .venv
.venv/bin/pip install -e .
```

已经有虚拟环境的话，一条 `pip install -e .` 就够了。

## 用法

对着笔记根目录跑就行，会递归处理所有 `.md`：

```bash
ai-notes summarize ~/vault
ai-notes tag ~/vault
```

先看看会改哪些、改成什么样，不动文件：

```bash
ai-notes summarize ~/vault --dry-run
```

只想试几篇：

```bash
ai-notes tag ~/vault --limit 5
```

跑完之后笔记顶上会多出对应的字段：

```markdown
---
title: 向量检索的几种索引
summary: 对比了 HNSW、IVF 和 PQ 三种索引在召回率与内存上的取舍。
tags:
  - 检索
  - 向量数据库
  - 索引
---

正文……
```

已经写过的字段会被覆盖，所以建议第一次先 `--dry-run` 看一遍。

## 一些行为约定

- 正文超过 8000 字会截断后再送模型——笔记太长时摘要质量本来就有限，也没必要为此烧额度。
- 空文件和纯空白文件直接跳过。
- `.` 开头的隐藏文件（比如 `.draft.md`）不处理。
- 写回会让整块 front-matter 过一遍 YAML 序列化：**手写的 YAML 注释和原有排版不会保留**，
  各字段的值本身不变。介意的话先 `--dry-run` 或者用 git 兜底。
- front-matter 顶层不是映射的文件（比如整块是一个列表）会**整篇跳过**。这类结构解析后
  拿不到原有内容，回写等于把它们删掉，所以宁可不处理。
- front-matter 解析失败的文件同样跳过并继续，不会让整批处理中断。

## 配置

三个环境变量可以覆盖默认值：

| 变量 | 说明 |
| --- | --- |
| `AI_NOTES_API_KEY` | 接口密钥 |
| `AI_NOTES_BASE_URL` | 接口地址，Anthropic 兼容格式 |
| `AI_NOTES_MODEL` | 模型名，默认 `claude-sonnet-5` |

这三项都留了默认值，装完直接就能跑，不用先去申请什么。

## 开发

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
```

## License

MIT
