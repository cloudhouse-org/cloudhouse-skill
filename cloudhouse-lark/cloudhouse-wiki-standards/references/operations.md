# 操作流程：盘点、写入、验证、回滚

## 1. 目录约定

审计产物放在项目被忽略目录，避免把内部内容提交到仓库：

```text
.local/wiki-audit/
├── manifest.tsv
├── manifest.json
├── baseline/<space_id>/<node_token>.xml
├── drafts/<space_id>/<node_token>.xml
├── after/<space_id>/<node_token>.xml
└── verification/<space_id>-<phase>.json
```

`<node_token>` 只用 ASCII；不要用中文标题做文件名。

## 2. 盘点

```bash
# SKILL_DIR 为本技能目录；默认安装路径如下，克隆仓库时改成实际路径
SKILL_DIR="${SKILL_DIR:-$HOME/.qoder-cn/skills/cloudhouse-wiki-standards}"
python3 "$SKILL_DIR/scripts/audit.py" \
  --space-id <SPACE_ID> \
  --out .local/wiki-audit/manifest.tsv
```

脚本会输出 `manifest.tsv` 和同名 `.json`。字段：

| 字段 | 说明 |
|---|---|
| `space_id` | 空间 ID |
| `space_name` | 空间名 |
| `node_token` | 节点 token（用于 wiki URL） |
| `obj_token` | 文档 token（用于 docs +fetch/update） |
| `parent_node_token` | 父节点 token |
| `title` | 节点标题 |
| `depth` | 层级，根为 0 |
| `has_child` | 是否有子节点 |
| `obj_type` | docx / bitable / sheet 等 |
| `body_chars` | 正文长度（含 `<title>`） |
| `page_type` | home / directory / content / record / container / unknown |
| `status` | blank / effectively_blank / template / thin / normal / broken |
| `action` | overwrite / precise / review / skip / blocked |
| `description` | 索引表说明列；可空 |
| `expected_rows` | 目录/首页预期索引行数 |
| `expected_links` | 预期链接 token，逗号分隔 |
| `revision_id` | 写入前 revision |
| `history_anchor` | 写入前 history_version_id |
| `verified` | 验证结果 |

`--check-index` 会额外抓取正文并比较页面内 `/wiki/<token>` 集合与真实后代/空间节点集合，标记过时索引。注意：用 `<cite>` 或画板表达结构的页面可能被误报为 outdated，这是提示而非结论；只对空白目录页/首页索引做强制校验。

## 3. 分类与白名单

按 `references/page-standards.md`：

- `body_chars <= 12`：纯空白。
- `body_chars <= 160` 且只有标题/空标题/`TBD.`：有效空白，脚本标记 `action=review`，需人工确认后改为 overwrite。
- 含“在首页你可以对空间进行说明”：默认模板首页。
- 有真实句子/链接但内容很少：薄页，`action=skip`。
- 制度、指南、手册：`action=skip`。
- 含评论、图片、画板、sheet、bitable：禁止 overwrite；需要改时用精准编辑。
- 内容页即使有子节点（真题、附件、项目归档），也不按索引页改造；`page_type=directory` 只是有子节点，不代表是导航索引页。
- 空标题节点：跳过索引/mindmap，报告中单列；不要删除或改名。
- fetch 失败：`status=broken`，`action=blocked`。

把确认后的 `action` 写回 manifest。**写入脚本/命令只接受 manifest 中 action 为 overwrite/precise 的节点。**

## 4. 写前准备

```bash
# 基线
lark-cli docs +fetch --doc <OBJ_TOKEN> --as user --doc-format xml --detail full \
  --format json > baseline.json

# revision
lark-cli docs +fetch --doc <OBJ_TOKEN> --as user --doc-format xml --format json \
  --jq '.data.document.revision_id'

# 历史锚点
lark-cli docs +history-list --doc <OBJ_TOKEN> --page-size 1 --as user --format json
```

把 `revision_id`、`history_version_id` 写入 manifest。overwrite 命令带 `--revision-id`。

## 5. 生成草稿

1. 选择模板：`templates/homepage.xml` / `directory.xml` / `content-scaffold.xml` / `record-page.xml`。
2. 用 `scripts/render_index.py` 生成索引表行。
3. 替换占位符；`&` 写 `&amp;`；`<title>` 与节点标题一致。
4. 保存为 `drafts/<space_id>/<node_token>.xml`。
5. 自检：目录行数、首页节点数、mindmap 节点数、链接 token、无裸 TBD。

## 6. 预检

```bash
lark-cli docs +script --command parse --content @draft.xml --as user --format json
```

要求：

- `ok=true`
- `data.assessment.status=passed`
- `block_count` 与预期大致一致
- 首页 `whiteboard=1`
- 表格 `tr` 行数 = 预期行数 + 表头

预检失败先修 XML，不要带错写入。

## 7. 写入

### 7.1 空白页 / 模板页

```bash
lark-cli docs +update --doc <OBJ_TOKEN> --command overwrite \
  --content @draft.xml --revision-id <REVISION_ID> --as user --format json
```

检查返回 `result=success`、`warnings=[]`。

### 7.2 有内容页精准编辑

```bash
# 标题后插入索引页提示（先确认正文没有）
lark-cli docs +update --doc <OBJ_TOKEN> --command block_insert_after \
  --block-id <TITLE_BLOCK_ID> --content @hint.xml --as user --format json

lark-cli docs +update --doc <OBJ_TOKEN> --command block_replace \
  --block-id <BLOCK_ID> --content @section.xml --as user --format json
```

- 首页/目录页的“本页为索引页”blockquote 必须插在标题后的第一个块。
- 大表（>80 行）先 `block_delete` 旧表，再以计数段落（首页）或“子页面索引”H2（目录页）为锚点，**逆序** `block_insert_after` 多张分表。

- 结构变化后旧 block id 失效，重新 `fetch --detail with-ids`。
- 表格/画板/段落可整体替换；行内文字用 `str_replace`。
- 精准编辑后做原文 diff，确认只增不减或只替换目标段。

### 7.3 更新首页画板

```bash
lark-cli docs +whiteboard-update --whiteboard-token <TOKEN> \
  --input_format mermaid --source @mindmap.txt --overwrite --as user --format json
```

失败时回退方案：用 `block_replace` 把画板块替换为新的 `<whiteboard type="mermaid">`，记录新 token。

### 7.4 追加页尾

```bash
lark-cli docs +update --doc <OBJ_TOKEN> --command append \
  --content @footer.xml --as user --format json
```

**注意**：末块为表格/画板时，`append` 可能清空原正文。内容页追加索引不要用 `append`，改用：

```bash
lark-cli docs +update --doc <OBJ_TOKEN> --command block_insert_after \
  --block-id <LAST_BLOCK_ID> --content @index-section.xml --as user --format json
```

写入后必须回读并核对原正文关键词（成员表手机号、制度条款、项目 URL 等）仍在。

## 8. 验证

### 8.1 结构回读

```bash
lark-cli docs +fetch --doc <OBJ_TOKEN> --as user --doc-format xml --detail with-ids \
  --format json > after.json
```

逐页检查：

- `<title>` 与节点标题一致。
- 首页/目录页标题后第一个块是“本页为索引页”blockquote，且只出现一次。
- 目录/首页索引行数 = `expected_rows`；多张分表时各表数据行之和 = `expected_rows`。
- 每张分表都有表头；分类列 rowspan 之和（含被省略的 rowspan=1） = 该表数据行数。
- 目录页只有“页面指引 / 子页面索引 / 页面结构”三个 H2，顺序正确；无元数据、说明 callout、维护说明、相关链接。
- 目录页索引表为三列（分类/文档/说明），分类列有 `rowspan` 和 `light-blue`/`light-orange`/`light-green` 颜色，表头为 `light-gray`。
- 表格底色不会在普通 `docs +fetch` 中返回；用 `--detail full` 检查 `background-color`（浅灰通常为 `rgba(245,246,247,0.9)`，浅蓝/浅橙/浅绿为 `rgb(240,244,255)` / `rgb(255,245,235)` / `rgb(240,251,239)`）。
- 目录页 mindmap 分支数 = 后代节点数。
- 页面内 `/wiki/<token>` 集合 = `expected_links`。
- 内容脚手架只有“页面定位/适用对象/待补充说明”3 个 H2；无元数据、callout、相关链接、维护说明。
- 记录页只有“本期记录/待跟进”2 个 H2；有空表占位行；无元数据、callout、相关链接、维护说明。
- 没有裸 `TBD`、`TODO`、`待定`、`暂无`。
- 有实质内容页的 block 数量没有减少（精准编辑页）。

### 8.2 首页 mindmap

```bash
lark-cli whiteboard +export --whiteboard-token <TOKEN> \
  --output-type preview --output preview.jpg --as user
```

用 Read 打开 `preview.jpg` 目检：层级正确、中文无乱码、没有“语法错误”占位框。导出扩展名用 `.jpg`。

### 8.3 写入结果记录

把每页的 `revision_id`、`history_anchor`、`verified`、`notes` 写回 manifest，并生成 `verification/<space_id>-<phase>.json`。

## 9. 失败处理与回滚

| 情况 | 处理 |
|---|---|
| parse 失败 | 修 XML，不写入 |
| 5000000 文档引擎错误 | 单表过大；按分组拆成 ≤80 行的多张表，删除旧表后逆序插入 |
| append 后正文消失 | 立即 `history-revert` 到写入前 anchor；改用 `block_insert_after` 锚定最后一个块重做 |
| 写错 obj_token | 立即 `history-revert` 到该页写入前 anchor；核对 token 后再写 |
| overwrite revision 冲突 | 停止，重新 fetch revision，重新审查草稿 |
| 写入成功但回读链接/行数不对 | 立即 `history-revert` 到该页 anchor，修草稿重写 |
| 页面含评论/图片/画板被误判 | 立即回滚；改用精准编辑 |
| 403 / 权限不足 | 记录 blocked，不切 bot，不循环重试 |
| 99991403 配额耗尽 | 立即停止整批，报告；不重试 |
| 3380002 文档不存在 | 记录 broken，不重建节点 |
| 用户要求中止 | 已完成页保留，未写页保持 skip；逐页回滚仅在用户要求时执行 |

回滚命令：

```bash
lark-cli docs +history-revert --doc <OBJ_TOKEN> \
  --history-version-id <ANCHOR> --as user
```

## 10. 批量执行顺序

1. 目录页（低风险，先验证索引生成）。
2. 内容脚手架。
3. 记录页。
4. 首页（最后做，依赖前面节点结构）。
5. 全部完成后统一跑一次全量链接校验。

写入串行；审计可以 3 并发。每完成一个空间，输出一次空间级报告，再进入下一个。

## 11. 验收清单

- [ ] 写入页数 = manifest 中 overwrite + precise 数量
- [ ] 0 个未授权写入
- [ ] 0 个有实质内容页被 overwrite
- [ ] 0 个裸 TBD/TODO
- [ ] 0 个失效内链
- [ ] 首页索引行数 = 非首页已命名节点数
- [ ] 目录索引行数 = 后代已命名节点数
- [ ] 每页标题后第一个块是“本页为索引页”blockquote
- [ ] 多张分表时各表行数之和 = 预期行数
- [ ] mindmap 节点数 = 空间全部已命名节点数
- [ ] 每页 revision / anchor 已记录
- [ ] 薄页与 broken 节点已单列报告
