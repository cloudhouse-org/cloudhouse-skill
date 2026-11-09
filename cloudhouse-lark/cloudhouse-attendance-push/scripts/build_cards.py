#!/usr/bin/env python3
"""生成成员版考勤摘要卡片（schema 2.0）。文案标准见 ../references/standards.md。"""
import argparse
import json
from datetime import date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--rules-url", required=True, help="考勤规则 wiki 链接（运行时解析）")
    a = ap.parse_args()
    summary = json.load(open(a.summary))
    mapping = {m["name"]: m for m in json.load(open(a.mapping))["mapping"]}
    assert len(mapping) == len(summary["people"]), "映射不全，先补齐"
    assert len({m["open_id"] for m in mapping.values()}) == len(mapping), "open_id 重复"
    start = date.fromisoformat(summary["window"]["start"])
    end = date.fromisoformat(summary["window"]["end"])
    title = f"【假勤】上周考勤摘要（{start.month}.{start.day}-{end.month}.{end.day}）"
    period = f"{summary['window']['start']} ~ {summary['window']['end']}"
    footer = ("数据来源：飞书假勤；\n"
              f"考勤规则：[{a.rules_url}]({a.rules_url})；\n"
              "如有疑问，请联系组长，谢谢；")
    for p in summary["people"]:
        if p["zero_in_window"]:
            total_line = "**总工时**：本区间暂无打卡记录，总工时 0.0 小时；如有疑问请联系考勤负责人。"
        else:
            total_line = f"**总工时**：**{p['window_total']} 小时**"

        def daily_line(d):
            line = f"- {d['date']} {d['weekday']}：{d['hours_display']} 小时"
            if d.get("bonus_minutes", 0) > 0:
                line += f"（其中 {d['bonus_display']} 小时双倍计入）"
            return line

        card = {
            "schema": "2.0",
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
            "body": {"elements": [
                {"tag": "markdown",
                 "content": f"**姓名**：{p['name']}\n**考勤组**：{p['group']}\n**统计区间**：{period}\n{total_line}"},
                {"tag": "hr"},
                {"tag": "markdown", "content": "**每日工时**\n" + "\n".join(daily_line(d) for d in p["daily"])},
                {"tag": "hr"},
                {"tag": "markdown", "content": f"<font color='grey'>{footer}</font>"},
            ]},
        }
        assert card["schema"] == "2.0" and card["body"]["elements"]
        json.dump(card, open(f"{a.out_dir}/r{p['row']:02d}.json", "w"), ensure_ascii=False)
    print(f"OK 成员卡 {len(summary['people'])} 张 → {a.out_dir}/r<行号>.json")


if __name__ == "__main__":
    main()