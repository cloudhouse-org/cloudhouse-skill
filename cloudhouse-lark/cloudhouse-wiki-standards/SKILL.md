---
name: cloudhouse-wiki-standards
version: 2.0.0
description: "大云屋团队知识库统一规范：盘点空间、识别空白/薄页/过时索引，按首页、目录页、内容页、记录页模板生成或修订飞书 Wiki，并完成链接校验与回滚。替代原 lark-wiki-homepage；当用户要求检查/整理/补全团队知识库、统一页面样式、优化首页或目录页时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# cloudhouse-wiki-standards — 团队知识库统一规范

把飞书 Wiki 当作长期维护的团队知识库：**先盘点，再分类，最后按模板写入**。目录页和首页必须来自真实节点树，内容页只写可确认的信息；没有依据的内容写成“待补充”，不编造制度、流程、人员、日期或金额。

> **前置必读（缺一不可）：**
> 1. [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) — 认证、身份与高风险操作
> 2. [`../lark-doc/references/lark-doc-xml.md`](../lark-doc/references/lark-doc-xml.md) — DocxXML 语法
> 3. [`references/page-standards.md`](references/page-standards.md) — 统一页面样式标准
> 4. [`references/operations.md`](references/operations.md) — 盘点、预检、写入、验证、回滚
> 5. [`references/xml-patterns.md`](references/xml-patterns.md) — Mermaid mindmap、rowspan 索引表等实战模式

## 适用场景

- 检查某个/多个知识空间是否有空白页、薄页、失效索引。
- 补写空白目录页、章节导航页、空间首页。
- 统一页面结构、元数据、callout、表格、链接写法。
- 为后续维护生成可复用的页面模板和审计脚本。

## 页面分类与动作

| 类型 | 判定 | 动作 |
|---|---|---|
| 纯空白页 | 正文 ≤12 字符，只有标题 | `overwrite` 目录页或内容脚手架 |
| 有效空白页 | 只有分节标题/`TBD.`，无实质内容 | 保留原分节标题，`overwrite` 脚手架 |
| 默认模板首页 | 含“在首页你可以对空间进行说明”等占位文字 | `overwrite` 标准首页 |
| 过时首页/目录页 | 计数、链接集合与实际节点不一致 | 首页精准编辑；空白目录直接重写 |
| 薄页但有真实内容 | 有真实句子/链接，但内容很少 | **不改**，列入报告 |
| 有实质内容页 | 制度、指南、手册、记录容器等 | **不改** |
| 失效节点 | fetch 返回 3380002 等 | 不重建，记录并报告 |

**硬规则：有实质内容的页面禁止 `overwrite`。** 需要修正时只用 `str_replace` / `block_replace` 做精准编辑，并先取基线。

### 索引页标识（首页与目录页）

- 首页、目录页在 `<title>` 后的**第一个块**固定写 `<blockquote><p>本页为索引页</p></blockquote>`。
- 该提示必须位于欢迎 callout / 页面指引之前；不要用 callout 代替 blockquote。
- 内容脚手架、记录页、内容页不加此提示。
- 存量首页/目录页已有该提示的保留，不重复插入。

### 精简规则（非首页）

- **目录页**：H2“页面指引”+ 指引段落 → H2“子页面索引”+ 三列彩色索引表（分类列按直接子页分组，`rowspan` + `light-blue`/`light-orange`/`light-green` 轮换）→ H2“页面结构”+ Mermaid mindmap；不写元数据、callout、维护说明、相关链接。
- **内容脚手架**：只保留 H2“页面定位”、H2“适用对象”、H2“待补充说明”；不写元数据、callout、相关链接、维护说明。
- **记录页**：一句使用说明 + H2“本期记录”+ H2“待跟进”；不写元数据、callout、相关链接、维护说明。
- 索引表用 `scripts/render_index.py`，结构图用 `scripts/render_mindmap.py`；单表超过 80 行时按 [`references/xml-patterns.md`](references/xml-patterns.md) 的“大索引表分表”规则拆表。

## 流程总览

```text
Step 1 确认范围与身份
→ Step 2 盘点节点树并生成 manifest
→ Step 3 分类并确定写入白名单
→ Step 4 取基线、revision、history anchor
→ Step 5 生成 XML 并 parse 预检
→ Step 6 写入（overwrite / 精准编辑）
→ Step 7 回读验证（行数、链接、mindmap）
→ Step 8 输出报告；失败逐页回滚
```

### Step 1：确认范围

```bash
lark-cli wiki +space-list --as user --format json
```

记录要处理的 `space_id`，排除官方示例库等无关空间。Wiki 全程使用 `--as user`；`auto` 常被解析成 bot。

### Step 2：盘点

优先使用本 skill 的只读审计脚本：

```bash
python3 /Users/lin/.qoder-cn/skills/cloudhouse-wiki-standards/scripts/audit.py \
  --space-id <SPACE_ID> \
  --out /path/to/.local/wiki-audit/manifest.tsv
```

它递归读取节点树、正文长度、失效节点，并输出 TSV/JSON。没有 Python 或需要单点核查时，用：

```bash
lark-cli wiki +node-list --space-id <SPACE_ID> --page-all --as user --format json
lark-cli wiki +node-list --space-id <SPACE_ID> --parent-node-token <NODE_TOKEN> --as user --format json
lark-cli docs +fetch --doc <OBJ_TOKEN> --as user --doc-format markdown \
  --format json --jq '.data.document.content | length'
```

### Step 3：分类并冻结白名单

manifest 中每页必须有 `action`：`overwrite` / `precise` / `review` / `skip` / `blocked`。
只有明确列出的页面允许写入；`review` 需要人工确认后才能改成 `overwrite`/`precise`，`skip` 和未列出的页面一律只读。

### Step 4：基线与锚点

```bash
lark-cli docs +fetch --doc <OBJ_TOKEN> --as user --doc-format xml --detail full \
  --format json > baseline.json
lark-cli docs +history-list --doc <OBJ_TOKEN> --page-size 1 --as user --format json
```

记录 `revision_id` 和 `history_version_id`。overwrite 时带 `--revision-id`，避免覆盖他人并发修改。

### Step 5：生成与预检

按 [`references/page-templates.md`](references/page-templates.md) 选择模板。目录页索引表用 `scripts/render_index.py`，页面结构图用 `scripts/render_mindmap.py`。XML 写本地文件，用 `@文件` 传参，避免 shell 转义。

```bash
lark-cli docs +script --command parse --content @draft.xml --as user --format json
```

要求 `data.assessment.status = passed`。检查：`<title>` 与节点标题一致、`&` 已转义、mindmap 顶格且无 Tab、rowspan 与缺失单元格一致、首页/目录页标题后第一个块是“本页为索引页”blockquote。

### Step 6：写入

```bash
# 空白页/模板页
lark-cli docs +update --doc <OBJ_TOKEN> --command overwrite \
  --content @draft.xml --revision-id <REVISION_ID> --as user --format json

# 有内容页的精准编辑
lark-cli docs +update --doc <OBJ_TOKEN> --command block_replace \
  --block-id <BLOCK_ID> --content @section.xml --as user --format json

# 更新首页已有 Mermaid 画板
lark-cli docs +whiteboard-update --whiteboard-token <BOARD_TOKEN> \
  --input_format mermaid --source @mindmap.txt --overwrite --as user --format json
```

写入串行执行，不并发。每页写入前重新确认 `revision_id`。

### Step 7：验证

```bash
lark-cli docs +fetch --doc <OBJ_TOKEN> --as user --doc-format xml --format json
```

逐页核对：

- `<title>` 与 wiki 节点标题一致。
- 首页/目录页标题后第一个块是 `<blockquote><p>本页为索引页</p></blockquote>`，且只出现一次。
- 目录页索引行数 = 实际后代节点数；目录页 mindmap 分支数 = 实际后代节点数；首页索引行数 = 非首页节点数。
- 多张分表时，各表数据行之和 = 预期行数；每张分表都有表头，rowspan 按组内行数计算。
- 目录页有“页面指引 / 子页面索引 / 页面结构”三个 H2，且索引表分类列有 `rowspan` 和颜色。
- 所有内链 token 都属于当前空间/允许的跨空间页面；失效 token 为 0。
- 内容脚手架只有 3 个 H2：页面定位、适用对象、待补充说明。
- 记录页只有“本期记录/待跟进”2 个 H2，且没有编造记录。
- 正文无裸 `TBD` / `TODO` / `待定` / `暂无`。
- 首页导出 mindmap 预览目检：`whiteboard +export --output-type preview --output preview.jpg`。

### Step 8：报告与回滚

失败页立即回滚：

```bash
lark-cli docs +history-revert --doc <OBJ_TOKEN> \
  --history-version-id <ANCHOR> --as user
```

报告至少包含：写入页清单、每页 revision/anchor、验证结果、未改薄页清单、失效/无权节点。

## 关键陷阱

| 陷阱 | 规则 |
|---|---|
| 身份 | Wiki 全程 `--as user`；403 只记录 blocked，不切 bot |
| bot 与部门 | bot 身份不能管理知识空间部门成员；不要试错 |
| overwrite | 清空重写、block id 全变；有内容/评论/图片/画板的页面禁止使用 |
| 标题 | `<title>` 必须与 wiki 节点标题一致；本 skill 不改节点标题 |
| 特殊字符 | XML 文本中的 `&` 写 `&amp;`；mindmap 节点避免 ASCII 括号、引号、`&` |
| rowspan | 被合并单元格后续行不再输出；`sum(rowspan)` 必须等于数据行数 |
| emoji | 只用 📚 📌 ⚠️ 💡 📝 🏁 ✅ ❌ ⭐ 等实测稳定 emoji |
| 链接 | 内链用 `https://<域名>/wiki/<node_token>`；不要用 obj_token 拼 wiki 链接 |
| 配额 | 遇到 99991403 立即停止，不循环重试 |
| 超大表 | 单表数据行 > 80 时拆成多张同结构表；300+ 行单表会触发 5000000 文档引擎错误 |
| append 丢正文 | 末块为表格/画板时 `append` 可能清空原正文；内容页追加索引改用 `block_insert_after` 锚定最后一个块，写后必须核对原正文关键词 |
| rowspan=1 | 飞书会省略 `rowspan="1"`；回读校验时，三列且首格无 rowspan 的行按 1 计 |
| 无标题节点 | 空标题节点不写入索引/mindmap，在报告中单列“未命名空白节点待整理” |
| Skill 自身 | 重命名/移动后需重载会话，旧 slash 命令可能仍被缓存 |

## 参考与脚本

| 文件 | 用途 |
|---|---|
| [`references/page-standards.md`](references/page-standards.md) | 统一页面样式标准 |
| [`references/page-templates.md`](references/page-templates.md) | 首页/目录/内容脚手架/记录页模板与占位符 |
| [`references/operations.md`](references/operations.md) | 完整操作流程、manifest 字段、验收清单 |
| [`references/xml-patterns.md`](references/xml-patterns.md) | mindmap、rowspan 索引表、callout 等模式 |
| [`templates/`](templates/) | 可直接复制的 XML 骨架 |
| [`scripts/audit.py`](scripts/audit.py) | 只读盘点并生成 manifest |
| [`scripts/render_index.py`](scripts/render_index.py) | 从 manifest 生成目录/首页索引表 XML |
| [`scripts/render_mindmap.py`](scripts/render_mindmap.py) | 从 manifest 生成目录/首页的 Mermaid mindmap 分支行 |

## 完成后汇报

空间名与 space_id、写入页数、未改页数、首页索引数/mindmap 节点数、每页 revision 与 history anchor、验证结果、薄页与失效节点清单。若只完成试点，明确暂停并等待用户验收。
