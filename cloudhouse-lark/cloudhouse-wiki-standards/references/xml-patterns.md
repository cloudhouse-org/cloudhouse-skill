# XML 模式库 — 知识库页面

> 前置：已读 [`../../lark-doc/references/lark-doc-xml.md`](../../lark-doc/references/lark-doc-xml.md)（完整语法）。本文件只收知识库场景的专用模式与踩坑规则。

## 一、Mermaid 思维导图

### 模板

```xml
<whiteboard type="mermaid">mindmap
  root((<知识库名>))
    <一级板块A>
      <二级页面A1>
        <三级文档A1a>
        <三级文档A1b>
    <一级板块B>
      <二级页面B1>
</whiteboard>
```

### 语法铁律

1. `<whiteboard type="mermaid">mindmap` **必须同行**，且 `mindmap` 顶格（第 0 列）。
2. 其后每行从**行首**开始按 **2 空格/级**缩进；层级由缩进决定，不用列表符号。
3. **禁 Tab**（从网页/文档复制最易混入，先检查 `\t`）。
4. 节点文本即 wiki 节点标题原名；**禁 ASCII 括号 `()`、方括号 `[]`、花括号 `{}`、双引号**。
5. 全角括号 （）安全；顿号、`+`、`/`、`-` 均安全。
6. 标题含 `&` 时，mindmap 用“与”代替（如“团队知识&记忆”→“团队知识与记忆”）；索引表保留原名并转义为 `&amp;`。
7. 根节点用 `root((名字))` 圆形样式；名字里不要出现括号。
8. 覆盖空间**全部**节点（root 代表首页本身，不单列）。

### 更新已有画板

```bash
lark-cli docs +whiteboard-update --whiteboard-token <TOKEN> \
  --input_format mermaid --source @mindmap.txt --overwrite --as user
```

失败时用 `block_replace` 把画板块替换为新的 `<whiteboard type="mermaid">`，记录新 token。

## 二、全量文档索引表

### 模板（rowspan 分组）

```xml
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
    <tr>
      <td rowspan="<该组行数>" background-color="light-blue" vertical-align="middle"><p><b><组名></b></p></td>
      <td><p><a href="https://<域名>/wiki/<node_token>"><组入口页></a></p></td>
      <td><p><一句话说明></p></td>
    </tr>
    <tr>
      <td><p>└ <a href="https://<域名>/wiki/<node_token>"><子文档></a></p></td>
      <td><p><一句话说明></p></td>
    </tr>
    <!-- 该组剩余行：只写 文档/说明 两列 -->
  </tbody>
</table>
```

### 规则

1. 每行一个非首页节点；组入口页本身也是一行，放组内第一行。
2. `rowspan` = 该组数据行数；**被合并的单元格在后续行中不输出**，rowspan 值必须与缺失的单元格数一致。
3. 子文档用“└ ”前缀标识层级；三级以下继续加“└ ”或全角空格前缀。
4. 链接一律 `https://<域名>/wiki/<node_token>`；不要用 obj_token。
5. 说明列保守撰写：分类页写“总入口”，叶子文档按标题功能推断，不编造具体数字/日期/负责人。
6. 组配色：`light-blue` / `light-orange` / `light-green` 轮换；表头统一 `light-gray`。
7. bitable 节点也用 `/wiki/<node_token>` 链接；不要用 `<cite>` 代替，便于批量校验。
8. 目录页索引固定三列（分类/文档/说明）；分类列按直接子页分组，`rowspan` + 颜色轮换；表头 `light-gray`：

```xml
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
    <tr>
      <td rowspan="2" background-color="light-blue" vertical-align="middle"><p><b>报销</b></p></td>
      <td><p><a href="...">报销</a></p></td><td><p>报销入口</p></td>
    </tr>
    <tr>
      <td><p>└ <a href="...">打车报销指南</a></p></td><td><p>打车报销</p></td>
    </tr>
  </tbody>
</table>
```

## 三、页面级模式

### 索引页标识（首页 / 目录页）

```xml
<title><标题></title>
<blockquote><p>本页为索引页</p></blockquote>
```

- 必须在标题后的第一个块，位于欢迎 callout / 页面指引之前。
- 只用 blockquote，不用 callout；首页、目录页加，内容页/记录页不加。
- 精准编辑时用 `block_insert_after --block-id <title_id>` 插入；写入前先检查正文是否已有该提示。

### 元数据 blockquote（不再使用）

本轮精简标准下，除首页页尾维护块外，非首页页面不写元数据、维护说明或相关链接。

### 欢迎 callout（首页顶部）

```xml
<callout emoji="📚" background-color="light-blue" border-color="blue">
  <p>欢迎来到<b><知识库名></b>。<一句话定位 + 板块枚举>。</p>
</callout>
```

可用 emoji（实测稳定）：📚 🌱 📝 💡 ✅ ❌ ⚠️ 📌 ❓ 👍 ❤️ 🏁 ⭐。**🛠️ 等不支持，会静默回落为 💡**。

### 目录页结构（不使用 callout）

目录页固定三部分：页面指引 → 子页面索引 → 页面结构；不写元数据/说明 callout/维护说明/相关链接。

```xml
<h2>页面指引</h2>
<p><1–2 句说明本页汇总什么、怎么用></p>

<h2>子页面索引</h2>
<!-- 三列彩色索引表，见上一节 -->

<h2>页面结构</h2>
<whiteboard type="mermaid">mindmap
  root((<本页标题>))
    <直接子页>
      <孙页>
</whiteboard>
```

### 内容脚手架（不使用 callout）

```xml
<title><标题></title>
<h2>页面定位</h2>
<p><一句话定位></p>
<h2>适用对象</h2>
<p><谁需要读/维护></p>
<h2>待补充说明</h2>
<checkbox done="false">待补充：<具体补什么></checkbox>
```

### 记录页使用说明（普通段落）

```xml
<p>本页用于记录<范围>，按日期倒序追加，不替代正式制度或会议纪要。</p>
```

### 待补充 checkbox

```xml
<h2>待补充说明</h2>
<checkbox done="false">待补充：页面定位与适用范围</checkbox>
<checkbox done="false">待补充：使用入口与权限</checkbox>
<checkbox done="false">待补充：常见问题与维护人</checkbox>
```

### 页尾维护块（首页/内容页）

```xml
<hr/>
<p>文档版本：20261023｜维护人：空间管理员｜节点增减后请同步更新思维导图与索引表。</p>
```

### 大索引表分表（>80 行）

单表数据行超过 80 行时拆成多张同结构表，避免 300+ 行触发 `5000000 Document engine internal error`。

- 每张表都保留完整 `<thead>`（分类 / 文档 / 说明）。
- 按分组打包，每表 ≤80 行；一个分组超过 80 行时切成多个 chunk，续表的分类单元格重复组名。
- 分类列 `rowspan` = 该组在**本表内**的行数。
- 写入时先 `block_delete` 旧表，再按逆序 `block_insert_after` 到锚点（首页=计数段落，目录页=“子页面索引”H2），最终顺序才是正序。
- 回读校验：各表数据行之和 = 预期行数；飞书会省略 `rowspan="1"`，三列且首格无 rowspan 的行按 1 计。

### 内容页追加索引（不要用 append）

末块为表格/画板时，`append` 可能清空原正文。用 `block_insert_after --block-id <最后一个块 id>` 插入索引区，并在回读时核对一个原正文关键词。

### 无标题节点

空标题节点无法生成有效链接和 Mermaid 节点：

- 索引表、mindmap 都跳过该节点。
- 首页计数句写“下表/各表收录其余 N 个已命名节点（另有 1 个未命名空白节点待整理）”。
- 在最终报告中单列该节点，不擅自删除或改名。

## 四、精准编辑

### 取 block id

```bash
lark-cli docs +fetch --doc <OBJ> --as user --doc-format xml \
  --detail with-ids --scope full --format json
```

- `<p id="...">`、`<table id="...">`、`<callout id="...">` 的 id 可用于 `str_replace` / `block_replace` / `block_insert_after`。
- 结构变化后旧 id 全部失效，必须重新 fetch。
- `whiteboard` 的 `token` 用于 `docs +whiteboard-update`，不要用 block id 更新画板。

### 常用命令

```bash
# 行内文字替换
lark-cli docs +update --doc <OBJ> --command str_replace \
  --pattern '<旧>' --content '<新>' --as user

# 整块替换（段落/表格/画板）
lark-cli docs +update --doc <OBJ> --command block_replace \
  --block-id <ID> --content @section.xml --as user

# 在锚点后插入
lark-cli docs +update --doc <OBJ> --command block_insert_after \
  --block-id <ANCHOR> --content @section.xml --as user

# 追加到文末
lark-cli docs +update --doc <OBJ> --command append \
  --content @footer.xml --as user
```

## 五、转义与自检

- 标签本身不转义；文本内的 `&` `<` `>` 才转义（`&amp;` `&lt;` `&gt;`）；中文引号无需转义。
- 写入前过一遍自检：
  - [ ] `mindmap` 顶格、无 Tab、2 空格/级
  - [ ] 节点文本无 ASCII 括号/引号/`&`
  - [ ] `rowspan` 与缺失单元格数一致
  - [ ] 链接数 = 非首页节点数 / 后代节点数
  - [ ] `<title>` 与 wiki 节点标题一致
  - [ ] 首页/目录页标题后第一个块是“本页为索引页”blockquote
  - [ ] 单表 ≤80 行；分表时各表行数之和 = 预期行数
  - [ ] callout emoji 在可用列表内
  - [ ] 正文无裸 `TBD/TODO/待定/暂无`

## 六、实战案例

### 案例 A：模板页 overwrite（团队制度库，27 节点）

首页为飞书默认模板（4 个占位章节）。策略：overwrite 全量重写——欢迎 callout + 四板块填充，思维导图放“知识空间简介”内，索引表 26 行（板块入口 rowspan=4 / 财务报销 rowspan=4 / 行政制度与项目 rowspan=7 / 行政团队成员 rowspan=3 / 行政实验室 rowspan=6 / 行政会议 rowspan=2）。验证要点：`docs +script parse` 通过、`whiteboard=1`、`tr=27`；preview 导出 jpg 后目检。

### 案例 B：有内容页精准插入（CHR 招新系统库，11 节点）

首页已有带样式章节（light-gray 表头表格 + cite 文档引用）。策略：原文不动，`block_insert_after` 插入“知识库结构”章节（锚点 = 系统简介 section 最后一个 li 的 block id），再在“帮助与反馈”末尾 li 后插入反馈表单链接段。插入后 h1 顺序验证：系统简介 → 知识库结构 → 系统入口。思维导图含全角括号节点（AI Coding考核指南（软件组））渲染正常。

### 案例 C：空白目录页补写（财务，4 个后代）

页面只有标题。策略：overwrite 为**精简目录页**——H2“子页面索引”两列表（报销 / └ 打车报销指南 / └ 打车开发票教程 / 火车票机票）+ H2“页面结构”Mermaid mindmap。不写元数据、说明 callout、维护说明或返回首页链接。验证：索引行数 4 = 实际后代数；mindmap 分支 4 个；无失效 token；`parse` 通过。

### 案例 D：330 节点首页全量索引（大云屋知识）

首页原有 24 行旧索引，实际空间 332 节点（331 个非首页，其中 1 个无标题空白节点）。策略：

- 标题后插入“本页为索引页”blockquote；计数改为 332 / 330，并注明 1 个未命名节点待整理。
- 索引按 12 个语义分组打包成 5 张表（行数 48/80/62/80/60），每表 ≤80 行、都有表头；超过 80 行的竞赛总表、课业知识各拆成两张。
- `block_delete` 旧表后，以计数段落为锚点逆序插入 5 张新表。
- `whiteboard +update` 写入 330 分支 mindmap；raw 导出校验 `mind_map` 节点数 = 331（含 root）。
- 回读：5 张表数据行之和 = 330；链接集合与全部已命名非首页节点完全一致；`rowspan=1` 被省略，校验时按 1 计。

排除的 13 个有子节点的页面（真题年份、项目归档、简历模板、竞赛总表、电赛汇总等）属于内容页，不按索引页改造；仅更新 28 个真正的导航索引页。
