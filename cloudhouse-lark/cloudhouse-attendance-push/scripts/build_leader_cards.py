#!/usr/bin/env python3
"""生成组长版组内考勤报告卡片：每人总时长+达标/差额。leaders.json 由运行时从考勤规则文档+名册解析。"""
import argparse
import json
from datetime import date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--leaders", required=True,
                    help="JSON 列表 [{key,group,display,leader,open_id,req}]")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--rules-url", required=True)
    a = ap.parse_args()
    summary = json.load(open(a.summary))
    start = date.fromisoformat(summary["window"]["start"])
    end = date.fromisoformat(summary["window"]["end"])
    span = f"{start.month}.{start.day}-{end.month}.{end.day}"
    leaders = json.load(open(a.leaders))
    out = []
    for meta in leaders:
        members = [p for p in summary["people"] if p["group"] == meta["group"]]
        assert members, meta["group"]
        req = meta["req"]
        lines, ok_count = [], 0
        for p in members:
            total = float(p["window_total"])
            if total >= req:
                ok_count += 1
                lines.append(f"- {p['name']}：{p['window_total']} 小时——达标")
            else:
                lines.append(f"- {p['name']}：{p['window_total']} 小时——未达标（差 {round(req - total, 1)} 小时）")
        card = {
            "schema": "2.0",
            "header": {"title": {"tag": "plain_text",
                                 "content": f"【假勤】{meta['display']}上周考勤报告（{span}）"},
                       "template": "blue"},
            "body": {"elements": [
                {"tag": "markdown",
                 "content": f"**考勤组**：{meta['group']}\n**每周要求**：{req} 小时\n**达标情况**：{ok_count}/{len(members)} 人达标"},
                {"tag": "hr"},
                {"tag": "markdown", "content": "**成员明细**\n" + "\n".join(lines)},
                {"tag": "hr"},
                {"tag": "markdown",
                 "content": f"<font color='grey'>数据来源：飞书假勤；\n考勤规则：[{a.rules_url}]({a.rules_url})；</font>"},
            ]},
        }
        assert card["schema"] == "2.0" and card["body"]["elements"]
        json.dump(card, open(f"{a.out_dir}/leader_{meta['key']}.json", "w"), ensure_ascii=False)
        out.append({**meta, "member_count": len(members), "ok_count": ok_count})
        print(f"{meta['display']} → {meta['leader']}: {ok_count}/{len(members)} 达标")
    json.dump(out, open(f"{a.out_dir}/leader_stats.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()