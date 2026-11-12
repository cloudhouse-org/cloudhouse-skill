# 页面模板与占位符

模板位于 `templates/`。模板使用 `{{PLACEHOLDER}}` 占位，写入前逐项替换；索引表由 `scripts/render_index.py` 生成，或按 `references/xml-patterns.md` 手工拼装。

## 0. 通用占位符

| 占位符 | 说明 | 示例 |
|---|---|---|
| `{{TITLE}}` | 与 wiki 节点标题完全一致 | `财务` |
| `{{GUIDANCE}}` | 纯索引页页面指引（索引上方） | `本页汇总财务板块的报销入口与票据指南。` |
| `{{VERSION}}` | 首页页尾文档版本 `YYYYMMDD` | `20261023` |
| `{{OWNER}}` | 首页页尾维护角色 | `空间管理员` |
| `{{COUNT}}` | 首页非首页节点数 | `26` |
| `{{INDEX_ROWS}}` | 索引表行 XML | 见 `render_index.py` |
| `{{MINDMAP}}` | Mermaid mindmap 分支行（不含 `mindmap`/`root`） | 见 `render_mindmap.py` |
| `{{MINDMAP_NOTE}}` | 结构图压缩说明句；未压缩时写“上方结构图展示主要层级；更多节点见索引表与左侧目录树。” | `结构图按节点上限压缩显示；更多节点见索引表与左侧目录树。` |

**注意**：XML 文本里的 `&` 必须写 `&amp;`；`<title>` 内的 `&` 同样转义。

## 1. 首页 `homepage.xml`

适用：空间首页，或默认模板首页。

```xml
<title>首页</title>

<blockquote><p>本页为索引页</p></blockquote>

<callout emoji="📚" background-color="light-blue" border-color="blue">
  <p>欢迎来到<b>{{SPACE_NAME}}</b>。{{ONE_LINE_INTRO}}</p>
</callout>

<h1>🎯 愿景和目标</h1>
<p>{{VISION_PARAGRAPH}}</p>
<ul>
  <li><b>{{VISION_1_TITLE}}</b>：{{VISION_1_TEXT}}</li>
  <li><b>{{VISION_2_TITLE}}</b>：{{VISION_2_TEXT}}</li>
  <li><b>{{VISION_3_TITLE}}</b>：{{VISION_3_TEXT}}</li>
</ul>

<h1>⛳️ 知识空间简介</h1>
<p>{{SPACE_INTRO}}</p>
<whiteboard type="mermaid">mindmap
  root(({{SPACE_NAME}}))
    {{MINDMAP}}
</whiteboard>
<p>{{MINDMAP_NOTE}}</p>

<h1>⭐️ 常用文档和链接</h1>
<p>本空间共 <b>{{TOTAL}}</b> 个节点，其中首页 1 个；下表收录其余 <b>{{COUNT}}</b> 个节点，点击文档名即可跳转；带“└”的条目为上一行的子文档。</p>
<table>
  <colgroup><col width="248"/><col width="250"/><col width="240"/></colgroup>
  <thead>
    <tr>
      <th background-color="light-gray"><p>分类</p></th>
      <th background-color="light-gray"><p>文档</p></th>
      <th background-color="light-gray"><p>说明</p></th>
    </tr>
  </thead>
  <tbody>
    {{INDEX_ROWS}}
  </tbody>
</table>

<h1>💡 知识空间帮助</h1>
<callout emoji="🌱" background-color="light-green" border-color="green">
  <p><b>新人快速上手</b></p>
  <ol>
    <li>通读本页思维导图，建立全库结构印象；</li>
    <li>{{START_HERE_2}}</li>
    <li>{{START_HERE_3}}</li>
  </ol>
</callout>
<callout emoji="📝" background-color="light-yellow" border-color="yellow">
  <p><b>内容维护约定</b></p>
  <ul>
    <li>新增页面请挂到对应目录下，并同步本页索引与思维导图；</li>
    <li>易变信息（密码、排班、负责人）变更后及时更新；</li>
    <li>发现失效链接或过时内容，请联系空间管理员。</li>
  </ul>
</callout>

<hr/>
<p>文档版本：{{VERSION}}｜维护人：{{OWNER}}｜节点增减后请同步更新思维导图与索引表。</p>
```

### 首页内容要求

- `<title>` 后第一个块必须是“本页为索引页”blockquote；已有则保留，不重复。
- `SPACE_NAME` 用空间名，不用“首页”。
- 索引超过 80 行时按分组拆成多张表，计数句用“下方各表收录其余 N 个节点”。
- 愿景 3 条必须来自已确认事实；没有依据时写“待补充”，不要编。
- `TOTAL = COUNT + 1`（首页）。
- 索引覆盖全部非首页节点；bitable 节点也要有链接。
- Mermaid 用 `render_mindmap.py --preset home`：真实节点 ≤40、每父 ≤12；超限折叠为汇总叶。
- Mermaid 节点文本避免 ASCII 括号、引号、`&`；`&` 用“与”代替。
- `MINDMAP_NOTE` 在结构图被压缩时写“结构图按节点上限压缩显示；更多节点见索引表与左侧目录树。”
- 已有实质内容的首页不要用本模板 overwrite，改用精准编辑。

## 2. 纯索引页 `directory.xml`

适用：只有索引内容的目录页、章节目录页。**纯索引页固定为“页面指引 → 子页面索引 → 页面结构图”**，不写元数据、说明 callout、维护说明或相关链接。

```xml
<title>{{TITLE}}</title>

<blockquote><p>本页为索引页</p></blockquote>

<h2>页面指引</h2>
<p>{{GUIDANCE}}</p>

<h2>子页面索引</h2>
<table>
  <colgroup><col width="180"/><col width="300"/><col width="300"/></colgroup>
  <thead>
    <tr>
      <th background-color="light-gray"><p>分类</p></th>
      <th background-color="light-gray"><p>文档</p></th>
      <th background-color="light-gray"><p>说明</p></th>
    </tr>
  </thead>
  <tbody>
{{INDEX_ROWS}}
  </tbody>
</table>

<h2>页面结构</h2>
<whiteboard type="mermaid">mindmap
  root(({{TITLE}}))
{{MINDMAP}}
</whiteboard>
<p>{{MINDMAP_NOTE}}</p>
```

### 纯索引页规则

- `<title>` 后第一个块必须是“本页为索引页”blockquote，放在“页面指引”之前；已有则保留，不重复。
- `GUIDANCE` 放 1–2 句页面指引，必须在“子页面索引”上方；已有真实引言/链接时保留原内容。
- 索引表为三列（分类 / 文档 / 说明）；分类列按直接子页分组，带 `rowspan` 和 `light-blue`/`light-orange`/`light-green` 轮换配色，表头 `light-gray`。
- 索引表行数 = 全部后代节点数；后代层级用“└ ”前缀。
- `INDEX_ROWS` 由 `scripts/render_index.py --mode directory` 生成，自带分类列和颜色。
- 单表超过 80 行时改用分表：按分组打包成多张同结构表（每表 ≤80 行），每表都保留表头；分类被拆分时，续表的分类单元格重复组名，rowspan 按该表内的行数计算。
- `render_index.py` 默认只输出单表行；超过 80 行时按 [`xml-patterns.md`](xml-patterns.md) 的“大索引表分表”自定义打包，或自行按分组切片。
- `MINDMAP` 由 `scripts/render_mindmap.py --preset pure` 生成（只含分支行，根节点由模板里的 `root(({{TITLE}}))` 提供）；真实节点 ≤50、每父 ≤12，超限折叠为汇总叶。
- `MINDMAP_NOTE` 在结构图被压缩时写“结构图按节点上限压缩显示；更多节点见索引表与左侧目录树。”
- 说明列优先复用已有索引措辞；没有依据时用中性描述（“查看<标题>”），不编业务事实。
- 不写“本页是……目录页，汇总 N 个页面”的 callout，不写维护说明，不写返回首页链接。
- `<title>` 中的 `&` 写 `&amp;`；mindmap root 中的 `&` 用“与”代替。
- 如果页面已有真实导语或实质内容，不要 overwrite；先确认是否属于可改的索引页。

## 2.1 半索引页索引区

适用：已有实质正文、又需要子页面导航的页面。正文保持原样，只在末尾追加以下片段：

```xml
<h2>子页面索引</h2>
<table>
  <colgroup><col width="180"/><col width="300"/><col width="300"/></colgroup>
  <thead>
    <tr>
      <th background-color="light-gray"><p>分类</p></th>
      <th background-color="light-gray"><p>文档</p></th>
      <th background-color="light-gray"><p>说明</p></th>
    </tr>
  </thead>
  <tbody>
{{INDEX_ROWS}}
  </tbody>
</table>

<h2>页面结构</h2>
<whiteboard type="mermaid">mindmap
  root(({{TITLE}}))
{{MINDMAP}}
</whiteboard>
<p>{{MINDMAP_NOTE}}</p>
```

- 索引表仍是全量后代；结构图用 `--preset semi`：真实节点 ≤30、每父 ≤12、最多 3 层。
- 用 `block_insert_after` 锚定正文最后一个块写入，不要用 `append`。
- 不改变原正文顺序，不删除原有 callout/表格/图片。

## 3. 内容脚手架 `content-scaffold.xml`

适用：空白内容页，或只有空标题/`TBD.` 的有效空白页。只保留 3 个 H2，不写元数据、callout、相关链接、维护说明。

```xml
<title>{{TITLE}}</title>

<h2>页面定位</h2>
<p>{{ONE_LINE_POSITION}}</p>

<h2>适用对象</h2>
<p>{{AUDIENCE}}</p>

<h2>待补充说明</h2>
<checkbox done="false">待补充：{{TODO_1}}</checkbox>
<checkbox done="false">待补充：{{TODO_2}}</checkbox>
<checkbox done="false">待补充：{{TODO_3}}</checkbox>
<checkbox done="false">待补充：{{TODO_4}}</checkbox>
```

### 内容脚手架要求

- 不写具体制度条款、审批链、金额、阈值、人名、日期。
- `ONE_LINE_POSITION` 只能写标题可推导的定位，例如“本页用于汇总与项目管理工作流相关的流程与入口”。
- 不写相关链接；需要跳转时由读者走索引页。
- 如果原页只有空分节标题（如考勤制度、Figma 使用规范），保留原 H2 标题，在每个 H2 下写“待补充：具体补什么”，不要改成分组结构。

## 4. 记录页 `record-page.xml`

适用：负责人日志、近期待处理等空记录容器。只保留一句使用说明 + 两个 H2，不写元数据、callout、相关链接、维护说明。

```xml
<title>{{TITLE}}</title>

<p>{{USAGE}}</p>

<h2>本期记录</h2>
<table>
  <colgroup><col width="120"/><col width="260"/><col width="160"/><col width="220"/></colgroup>
  <thead>
    <tr>
      <th background-color="light-gray"><p>日期</p></th>
      <th background-color="light-gray"><p>事项</p></th>
      <th background-color="light-gray"><p>结果/状态</p></th>
      <th background-color="light-gray"><p>备注</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>待补充</p></td>
      <td><p>待补充：从最近一次记录开始填写</p></td>
      <td><p>待补充</p></td>
      <td><p>待补充</p></td>
    </tr>
  </tbody>
</table>

<h2>待跟进</h2>
<checkbox done="false">待补充：需要跟进的事项</checkbox>
```

### 记录页要求

- 空表必须有一行“待补充”，不要留纯空表。
- 不编造任务、日期、负责人、结果。
- 待处理页可用列：事项、负责人、截止日期、状态、备注。
- `USAGE` 写一句用途与追加规则，例如“用于记录<角色>的日常工作与交接事项，按日期倒序追加”。

## 5. 精准编辑片段

### 只替换一段文字

```bash
lark-cli docs +update --doc <OBJ> --command str_replace \
  --pattern '<旧文本>' --content '<新文本>' --as user
```

### 替换一个块（段落/表格/画板）

```bash
lark-cli docs +update --doc <OBJ> --command block_replace \
  --block-id <BLOCK_ID> --content @section.xml --as user
```

### 插入新章节

```bash
lark-cli docs +update --doc <OBJ> --command block_insert_after \
  --block-id <ANCHOR_BLOCK_ID> --content @section.xml --as user
```

### 更新已有 Mermaid 画板

```bash
lark-cli docs +whiteboard-update --whiteboard-token <TOKEN> \
  --input_format mermaid --source @mindmap.txt --overwrite --as user
```

精准编辑前用 `docs +fetch --detail with-ids --scope full` 取 block id；结构变化后旧 id 失效，需要重新 fetch。

## 6. 索引表片段生成

`render_index.py` 需要租户 wiki 根地址。二选一：

```bash
export LARK_WIKI_BASE_URL="https://<tenant>.feishu.cn/wiki/"
# 或每条命令加 --base-url "https://<tenant>.feishu.cn/wiki/"
```

```bash
python3 scripts/render_index.py \
  --manifest manifest.json \
  --target-node <NODE_TOKEN> \
  --mode directory \
  --out index.xml
```

- `mode=directory`：列出 target 的全部后代节点（纯索引页与半索引页都用全量）。
- `mode=home`：列出该空间全部非首页节点；默认按根节点分组，可用 `--groups` 指定更细的分组：

```bash
python3 scripts/render_index.py \
  --manifest manifest.json \
  --target-node <HOME_NODE> \
  --mode home \
  --groups groups.json \
  --descriptions descriptions.json \
  --out index.xml
```

未设置 `LARK_WIKI_BASE_URL` 时，请在每条命令中显式传 `--base-url "https://<tenant>.feishu.cn/wiki/"`。

`groups.json` 结构：`[{"title": "板块入口", "tokens": ["...", "..."]}, ...]`；`descriptions.json` 是 `{"<node_token>": "说明"}`。token 必须存在于 manifest，否则脚本报错。
- 输出只包含 `<tr>...</tr>`，直接替换模板里的 `{{INDEX_ROWS}}`。
- 说明列默认“查看<标题>”；可在 `descriptions.json` 或 manifest 的 `description` 字段覆盖。

### 6.1 结构图分支生成

```bash
# 首页：真实节点 ≤40
python3 scripts/render_mindmap.py \
  --manifest manifest.json --target-node <HOME_NODE> \
  --preset home --out mindmap-branches.mmd

# 纯索引页：真实节点 ≤50
python3 scripts/render_mindmap.py \
  --manifest manifest.json --target-node <NODE_TOKEN> \
  --preset pure --out mindmap-branches.mmd

# 半索引页：真实节点 ≤30、最多 3 层
python3 scripts/render_mindmap.py \
  --manifest manifest.json --target-node <NODE_TOKEN> \
  --preset semi --out mindmap-branches.mmd
```

- 可用 `--max-nodes`、`--max-children`、`--max-depth` 覆盖预设。
- stderr 会打印 `real / summaries / omitted / total / invariant`；`invariant=True` 才可写入。
- 超出预算的分支自动生成 `……（其余 N 项见索引表）` 汇总叶；索引表仍是全量。
- 脚本输出的是**分支行**，不含 `mindmap`/`root`。用于 `whiteboard +update` 前需拼成完整文档：

```text
mindmap
  root((页面标题))
<分支行>
```
