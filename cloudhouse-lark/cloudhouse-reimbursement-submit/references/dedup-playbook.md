# 查重台账构建与判定（dedup playbook）

「项目报销」表**没有发票号码字段**，查重唯一可靠依据是附件票面号码。台账 = `invoice_no → {record_id, file_token, name}`，覆盖全表所有项目。

## A. 拉全表记录

```bash
lark-cli base +record-list --base-token <BASE> --table-id tbl4LE0c5NcmV4xP --as user \
  --limit 200 --format json --field-id 金额 --field-id 报销内容 --field-id 所属项目 \
  --field-id 发票 --field-id 附件 \
  --jq '{ids: .data.record_id_list, has_more: .data.has_more, rows: [.data.data[] | {amt: .[0], txt: .[1], inv: [.[3][]? | {n: .name, t: .file_token}], extra: [.[4][]? | {n: .name, t: .file_token}]}]}'
```

`has_more=true` 用 `--offset` 串行翻页直到全量。记录 id 与附件 token 集合是跨轮复用的校验键。

## B. 下载全部附件

对每个含附件的记录串行执行（无附件的记录跳过）：

```bash
mkdir -p /tmp/dupcheck/<record_id>
lark-cli base +record-download-attachment --base-token <BASE> --table-id tbl4LE0c5NcmV4xP \
  --record-id <record_id> --output /tmp/dupcheck/<record_id> --as user
```

Base 附件必须用此命令下载；`--output` 须为已存在目录。

## C. 提取号码建台账

- 对 `/tmp/dupcheck` 整体跑 `scripts/extract_invoices.py`（project_folder 会是 record_id，可作归属键），PDF 号码直接入台账。
- `needs_visual` 的图片/扫描件用 Read 逐张目视读号码入台账。
- 文件名含 20 位号码可先速比缩小范围，但**入台账必须以票面提取为准**（文件名会截断、改名、撒谎）。
- zip 内发票由脚本 GBK 解压后同样处理。
- 非发票附件（docx、电路图等）标记排除，不入台账。

## D. 跨轮复用校验

保存上轮台账时一并保存 A 步的 `ids + token 集合`。新一轮先重跑 A：

- 集合完全一致 → 直接复用台账；
- 有新增/变化 → 仅对新增记录或新 token 重跑 B/C，合并进台账；
- **token 消失**（附件被删）→ 该号码不再视为已提交（真实案例：标签纸发票从交换机记录移除后需重新提交）。

## E. 判定规则

- 本地号码 ∈ 台账 → 重复，跳过并记录对应 record_id（跨项目也算重复）。
- 本地号码 ∉ 台账 → 未提交，进入提交流程。
- 无号码发票：金额+品名+开票日期组合比对；命中相似标「不确定」，AskUserQuestion 确认，不擅自跳过或提交。
- 同一文件被改名为不同项目文件夹：以号码为准，仍判重复。

## F. 执行纪律

list/download 串行；`99991403` 立即停、`91403` 不重试（见 lark-shared）。台账与划分结果（已提交/未提交/不确定）交 SKILL.md Step 4 使用。