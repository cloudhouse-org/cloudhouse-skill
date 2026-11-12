---
name: cloudhouse-reimbursement-submit
version: 1.0.0
description: "把本地发票文件夹的发票全表查重后提交到飞书 Base『项目报销』表：金额=价税合计、报销内容不带项目名前缀、发票附件上传、回读校验；重复发票跳过并汇报。当用户给出发票文件夹或项目报销表链接，要求提交发票/报销/上报发票/录入发票，或更新、替换已提交发票时使用。"
metadata:
  requires:
    bins: ["lark-cli", "python3", "pdftotext", "unzip"]
---

# cloudhouse-reimbursement-submit — 发票报销提交

把本地发票按规范提交到飞书 Base「项目报销」表：**先全表查重、后串行提交、一切以票面为准**。查重台账构建见 [`references/dedup-playbook.md`](references/dedup-playbook.md)；更正/替换发票见 [`references/corrections.md`](references/corrections.md)。

> **前置必读：**
> 1. [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) — 认证、身份、权限与配额处置
> 2. Base 命令加载 lark-base skill；`+record-upsert` 前读 [`../lark-base/references/lark-base-record-upsert.md`](../lark-base/references/lark-base-record-upsert.md)，CellValue 写法读 [`../lark-base/references/lark-base-cell-value.md`](../lark-base/references/lark-base-cell-value.md)
> 3. Step 3 前读 [`references/dedup-playbook.md`](references/dedup-playbook.md)

## Schema 速查

默认 Base `BsXBbG1XMarbmasDJlWcKuLqnRf` / 表 `tbl4LE0c5NcmV4xP`（项目报销）；用户给其他链接时从链接解析 token，不沿用默认。

| 字段 | ID | 写规则 |
|---|---|---|
| 金额 | fld6c6lH4Q | number = 发票**价税合计（小写）**，不是文件名金额/未税金额 |
| 报销内容 | fldMk1pQfA | `品名（销售方/金额）`，如「技术服务费（mimo 261.80）」；**禁止项目名前缀** |
| 发票 | fldlh5Cej1 | attachment，发票原件，走 `+record-upload-attachment` |
| 附件 | fldP4Pq6hi | attachment，补充材料（订单/支付截图），可空 |
| 申报人 | fldr6QSIGZ | user = 当前登录用户 openId（`auth status` 取） |
| 报销状态 | fldeL3R6kg | select = 「申请中」 |
| 所属项目 | fldTasfM0J | link → 项目表 `tblvL0eAb5vXdj7k` 的 record_id |
| 提交时间 / 审核人 / 审核意见 | fldXUIhL3T / fldTZQV9Lw / fldsAV6ihx | **不写**（默认值/审核人填） |

项目映射速查（文件夹 → 项目 record_id；须以项目表真实名称核验，名称可能变化）：

| 发票文件夹 | record_id | 项目表名称 |
|---|---|---|
| 越秀电子琴 | reczz28SlhgVFuLu | 越秀区中山二路小学电子琴授课 |
| 招新系统 | recvwvxsvLqBTo | 2026招新系统研发&运营 |
| 飞书接入计划 | reczz28MVgY3vLNG | 云屋飞书接入计划 |

未知文件夹：项目表 `+record-search` 按名称找；找不到问用户，不猜。

## Step 0：身份与参数

全程 `--as user`。`lark-cli auth status` 取 `identities.user.openId` 作申报人。确认发票文件夹路径与目标表。

## Step 1：扫描文件夹

`find <文件夹> -type f ! -name '.DS_Store'` 递归列出；空文件夹直接汇报「无发票」结束。子目录名即项目归属线索。

## Step 2：提取票面台账

```bash
SKILL_DIR="${SKILL_DIR:-$HOME/.qoder-cn/skills/cloudhouse-reimbursement-submit}"  # 从仓库运行时指向仓库内 skill 目录
python3 "$SKILL_DIR/scripts/extract_invoices.py" <文件夹> --out /tmp/local-ledger.json
```

脚本只读源文件夹，输出每文件 `{invoice_no,date,seller,item,total,needs_visual,mismatch,...}`。`needs_visual` 项（图片、无文本层 PDF、解析缺失）用 Read 逐张目视补全，**不猜**。`mismatch`（文件名号码/金额/品名与票面不符）以票面为准，并在汇报中透明标注。

## Step 3：全表查重

按 [`references/dedup-playbook.md`](references/dedup-playbook.md) 构建「已提交发票号码台账」：`+record-list` 全量（limit 200、查 `has_more`）投影 金额/报销内容/所属项目/发票/附件；**表内没有发票号码字段**，必须 `+record-download-attachment` 下载全部附件提取号码（PDF 复用 extract_invoices.py，图片目视）。跨轮复用旧台账前，先重拉 record id + 附件 token 确认无新增。

## Step 4：划分已提交 / 未提交

本地号码 ∈ 台账 → 跳过，记录对应已有 record_id；否则进入提交。无号码的发票按 金额+品名+日期 组合判定并标「不确定」问用户。查重覆盖**全表所有项目**，不限当前文件夹项目。

## Step 5：串行创建记录

逐条 `+record-upsert`，批间 `sleep 1`。示例（CellValue 细节见 lark-base cell-value 文档）：

```bash
lark-cli base +record-upsert --base-token <BASE> --table-id tbl4LE0c5NcmV4xP --as user \
  --json '{"金额":31.90,"报销内容":"交换机（武汉创想天成）","所属项目":[{"id":"<项目record_id>"}],"申报人":[{"id":"<openId>"}],"报销状态":"申请中"}'
```

## Step 6：上传发票附件

lark-cli 上传路径白名单仅 **cwd、/tmp、~/files**（lark-base 未记载）；桌面文件先 `cp` 到 /tmp。创建后逐条：

```bash
lark-cli base +record-upload-attachment --base-token <BASE> --table-id tbl4LE0c5NcmV4xP \
  --record-id <rid> --field-id fldlh5Cej1 --file /tmp/<发票文件> --as user
```

## Step 7：回读校验

`+record-get` 回读全部新记录：字段值与速查表一致、附件 name/size 与本地原件一致、申报人/项目/状态正确。不一致即修复后重验。

## 更正分支

用户更新/替换发票时走 [`references/corrections.md`](references/corrections.md)：重新提取+重新查重 → 覆盖字段前 `+record-history-list` 查操作人（用户手改有冲突先 AskUserQuestion）→ upsert 改字段 → 先传新附件再 `+record-remove-attachment` 旧 token `--yes` → 回读汇报。

## 硬规则

- 票面为准：文件名号码/金额/品名都可能撒谎；金额只取价税合计小写。
- 报销内容禁项目名前缀；品名（销售方/金额）格式。
- 重复发票一律跳过并汇报已有记录，杜绝重复提交。
- 只写存储字段；提交时间/审核人/审核意见不写。
- list 类命令串行；写入串行、批间 sleep 0.5–1s。
- `99991403` 月配额耗尽立即停止；`91403` 不重试，按 lark-shared 引导。
- 用户手动改过的字段未经确认不覆盖（先查 history）。
- 解析失败不猜、不用文件名兜底，转目视或问用户。

## 脚本与参考

| 文件 | 用途 |
|---|---|
| [`scripts/extract_invoices.py`](scripts/extract_invoices.py) | 只读票面提取：pdftotext 解析、GBK zip 解压、needs_visual/mismatch 标记 |
| [`references/dedup-playbook.md`](references/dedup-playbook.md) | 已提交台账构建、跨轮复用校验、判定规则 |
| [`references/corrections.md`](references/corrections.md) | 更正/替换发票分支与历史核查 |

## 完成后汇报

提交清单（报销内容/号码/金额/record_id + 表链接）、跳过清单（号码 → 已有记录）、目视补全与 mismatch 标注、失败项原因。