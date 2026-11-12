# 更正/替换发票分支（corrections）

触发：用户说某张发票「有问题/已更新/替换」，或要求更正已提交记录的字段。

## 1. 重新提取与重新查重

- 重读更新后的本地文件（`extract_invoices.py` 或目视），取新票面：号码/日期/销售方/品名/价税合计。旧文件可能已被删除或改名，先 `ls` 目录确认现状。
- 新号码按 [`dedup-playbook.md`](dedup-playbook.md) 重新查重——新票可能早已在表内（换票不等于未提交）。

## 2. 历史核查（覆盖任何字段前必做）

```bash
lark-cli base +record-history-list --base-token <BASE> --table-id tbl4LE0c5NcmV4xP \
  --record-id <rid> --as user --page-size 50
```

命令细节见 [`../../lark-base/references/lark-base-record-history-list.md`](../../lark-base/references/lark-base-record-history-list.md)。看 `operator` 与 `field_changes`：

- 用户手动改过的字段（如所属项目、报销内容）与本次更正意图冲突 → **AskUserQuestion 让用户选**，不擅自覆盖或回退（真实案例：用户曾手动把项目改到云屋飞书接入计划，需确认后才改回招新系统）。
- 无冲突的字段按更正意图更新。

## 3. 更新字段

`+record-upsert --record-id <rid>` 只写约定字段：金额=新价税合计；报销内容=`品名（销售方/金额）` 禁项目前缀；所属项目按用户确认结果。不写审核人/审核意见/提交时间。

## 4. 替换附件（先新后旧）

1. `+record-get` 取旧附件 file_token；
2. 新文件 cp 到 /tmp 后 `+record-upload-attachment --field-id fldlh5Cej1`；
3. `+record-remove-attachment --field-id fldlh5Cej1 --file-token <旧token> --yes`。

先传新再删旧，避免记录中途无发票。删除属高风险写操作，用户请求更正即视为授权该替换；目标 token 必须来自当前回读，不凭记忆。

## 5. 回读与汇报

`+record-get` 校验：新号码对应附件 name/size 与原件一致、旧 token 已不在、金额/内容/项目正确。汇报 旧→新 对照（号码、金额、附件 token、项目决定）与查重结论。