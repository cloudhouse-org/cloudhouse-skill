#!/usr/bin/env python3
"""生成管理群总览卡：各组达标数/总时长/人均时长（不写组长与要求标注）。"""
import argparse
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def r1(minutes):
    return str((Decimal(minutes) / Decimal(60)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--leaders", required=True)
    ap.add_argument("--out", default="cards/overview.json")
    ap.add_argument("--rules-url", required=True)
    a = ap.parse_args()
    summary = json.load(open(a.summary))
    leaders = json.load(open(a.leaders))
    start = date.fromisoformat(summary["window"]["start"])
    end = date.fromisoformat(summary["window"]["end"])
    span = f"{start.month}.{start.day}-{end.month}.{end.day}"
    lines, total_ok, total_n = [], 0, 0
    for L in leaders:
        members = [p for p in summary["people"] if p["group"] == L["group"]]
        assert members, L["group"]
        ok = sum(1 for p in members if float(p["window_total"]) >= L["req"])
        mins = sum(p["window_total_minutes"] for p in members)
        total_ok += ok
        total_n += len(members)
        lines.append(f"- {L['display']}：{ok}/{len(members)} 达标；总时长 {r1(mins)} 小时，人均 {r1(mins / len(members))} 小时")
    card = {
        "schema": "2.0",
        "header": {"title": {"tag": "plain_text",
                             "content": f"【假勤】上周各组考勤总览（{span}）"},
                   "template": "blue"},
        "body": {"elements": [
            {"tag": "markdown",
             "content": f"**统计区间**：{summary['window']['start']} ~ {summary['window']['end']}\n**全员达标**：{total_ok}/{total_n} 人"},
            {"tag": "hr"},
            {"tag": "markdown", "content": "**各组情况**\n" + "\n".join(lines)},
            {"tag": "hr"},
            {"tag": "markdown",
             "content": f"<font color='grey'>数据来源：飞书假勤；\n考勤规则：[{a.rules_url}]({a.rules_url})；</font>"},
        ]},
    }
    assert card["schema"] == "2.0" and card["body"]["elements"]
    json.dump(card, open(a.out, "w"), ensure_ascii=False)
    print(f"OK 总览卡 → {a.out}; 全员达标 {total_ok}/{total_n}")
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()