---
name: cloudhouse-attendance-push
version: 1.0.0
description: "大云屋每周考勤推送：解析飞书假勤导出 xlsx（打卡配对算时长、交叉验证），按自然周口径生成成员版考勤摘要与组长版组内达标报告卡片，经小云 bot 私聊推送；先样板、批准后批量。当用户给出考勤表/考勤 xlsx 并要求推送考勤、上周考勤摘要、组内达标情况给成员或组长时使用。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
---

# cloudhouse-attendance-push — 每周考勤推送

把飞书假勤导出的考勤表变成两类私聊卡片：**成员版**（考勤组/总工时/每日工时）与**组长版**（组内每人总时长+达标/差额）。口径与文案以 [`references/standards.md`](references/standards.md) 为准；计算与发送用 `scripts/` 确定性脚本。

> **前置必读：**
> 1. [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) — 认证、身份、高风险审批
> 2. [`references/standards.md`](references/standards.md) — 窗口/算法/文案/审批/陷阱

## Step 0：运行时解析（不硬编码标识符）

- **窗口**：上周自然周周一~周日，作为 `--start/--end`。
- **RULES_URL**：用户给的考勤规则 wiki 链接，或 wiki 搜"考勤规则"；`docs +fetch` 读取各组每周要求与考勤负责人。
- **名册 Base**：用户给的链接，或 `drive +search --doc-types bitable` 找含 姓名/年级/组别/负责人信息 字段的名册表；从链接提取 base token 与表 id。
- **leaders.json**：`[{key,group,display,leader,open_id,req}]`；open_id 取名册「负责人信息」（组长）或 `contact +search-user`，与规则文档考勤负责人交叉一致；req 取文档。

## Step 1：解析与交叉验证

```bash
SKILL_DIR="${SKILL_DIR:-$HOME/.qoder-cn/skills/cloudhouse-attendance-push}"
python3 "$SKILL_DIR/scripts/parse_attendance.py" <考勤.xlsx> \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> --out summary.json
```

超差中止时先问用户差异原因，确认后加 `--known-correction 姓名=小时` 重跑。核对 stdout：人数、max_diff、双倍加成、零工时、奇数卡审计。

## Step 2：姓名→open_id

```bash
lark-cli base +record-list --base-token <BASE> --table-id <TABLE> \
  --field-id <姓名字段ID> --as user --format ndjson --output roster_full.ndjson   # 省略 --view-id！
python3 "$SKILL_DIR/scripts/build_mapping.py" --summary summary.json --roster roster_full.ndjson --out mapping.json
```

missing/conflicts 用 `contact +search-user --queries` 兜底、按部门消歧；仍缺问用户。齐全才继续。

## Step 3：成员卡 + 样板闸门

```bash
python3 "$SKILL_DIR/scripts/build_cards.py" --summary summary.json --mapping mapping.json \
  --out-dir cards --rules-url <RULES_URL>
lark-cli im +messages-send --as bot --user-id <请求者open_id> --msg-type interactive \
  --content @cards/r<行号>.json --idempotency-key att-sample-<止MMDD>
```

`im +messages-mget` 回读 + 请求者目视 → **等明确批准**（AskUserQuestion）。未批准不批量。

## Step 4：成员批量 + 核验

manifest.json：每人 `{label,open_id,card:"cards/rNN.json",key:"att-<止MMDD>-rNN",expect:"**姓名**：姓名"}`。

```bash
python3 "$SKILL_DIR/scripts/send_cards.py" --manifest manifest.json --log send_log.ndjson --ids-out sent_ids.json
python3 "$SKILL_DIR/scripts/verify_cards.py" --ids sent_ids.json --manifest manifest.json
```

## Step 5：组长卡 + 样板闸门 + 批量

```bash
python3 "$SKILL_DIR/scripts/build_leader_cards.py" --summary summary.json --leaders leaders.json \
  --out-dir cards --rules-url <RULES_URL>
```

同样先发一张样板给请求者、批准后批量；manifest key=`att-leader-<止MMDD>-<key>`，expect=考勤组值；send_cards + verify_cards 复用。

## Step 6：群公告（两类推送核验通过后）

向「云屋水群」「云屋【禁】水群」发 @所有人 通知。chat_id 运行时按群名解析（bot 须在群内），不写入仓库：

```bash
lark-cli im +chat-search --query 水群 --as bot --format json   # 取两个群 chat_id
lark-cli im +messages-send --as bot --chat-id <CHAT_ID> --idempotency-key att-announce-<群key>-<止MMDD> \
  --text $'<at user_id="all"></at> 上周考勤情况已推送给各组组长和26级成员本人，请注意查收；如有疑问请联系组长。'
```

mget 核验：sender 为 bot、未撤回、content 含 `@_all`（@所有人 的服务端规范化）。

## Step 7：汇报

成功 X/N、失败名单+原因+建议、零工时名单、各组达标 X/Y、回读核验结果、日志路径、群公告结果。失败者修复后原键补发。

## 硬规则

- 两类推送各自先样板后批准；改参重走样板。
- 不加导出时点/口径/范围类标注；双倍标每日行（成员）或不标（组长）。
- 映射不齐不批量；交叉验证超差不静默；发送串行留痕；schema 必须 "2.0"。

## 脚本与参考

| 文件 | 用途 |
|---|---|
| [`scripts/parse_attendance.py`](scripts/parse_attendance.py) | 只读解析+配对算时长+交叉验证门 |
| [`scripts/build_mapping.py`](scripts/build_mapping.py) | 名册精确匹配，缺失/冲突列出 |
| [`scripts/build_cards.py`](scripts/build_cards.py) | 成员卡（标准文案） |
| [`scripts/build_leader_cards.py`](scripts/build_leader_cards.py) | 组长卡（达标/差额） |
| [`scripts/send_cards.py`](scripts/send_cards.py) | 串行发送+幂等+留痕 |
| [`scripts/verify_cards.py`](scripts/verify_cards.py) | mget 全量回读核验 |
| [`references/standards.md`](references/standards.md) | 口径权威：窗口/算法/文案/审批/陷阱 |