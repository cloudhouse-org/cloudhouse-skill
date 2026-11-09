#!/usr/bin/env python3
"""只读解析飞书假勤导出 xlsx：每日打卡两两配对算时长，全范围交叉验证总时长列。
口径见 ../references/standards.md。stdout 仅输出 concise 结论。"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from openpyxl import load_workbook

WEEKDAY = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def round1(minutes):
    return str((Decimal(minutes) / Decimal(60)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def day_minutes(val, d_start, d_end):
    """(分钟数, 双倍区间重叠分钟, 打卡数, 末尾孤立卡忽略)。升序两两配对求差。"""
    if val is None:
        return 0, 0, 0, False
    s = str(val).strip()
    if s in ("-", ""):
        return 0, 0, 0, False
    parts = [p.strip() for p in re.split(r"[,，]", s) if p.strip() and p.strip() != "-"]
    times = []
    for p in parts:
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", p)
        if not m:
            raise ValueError(f"非法打卡时间 {p!r}")
        times.append(int(m.group(1)) * 60 + int(m.group(2)))
    times.sort()
    total = bonus = 0
    for i in range(0, len(times) - 1, 2):
        a, b = times[i], times[i + 1]
        total += b - a
        bonus += max(0, min(b, d_end) - max(a, d_start))
    return total, bonus, len(times), len(times) % 2 == 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--start", required=True, help="窗口起 YYYY-MM-DD（周一）")
    ap.add_argument("--end", required=True, help="窗口止 YYYY-MM-DD（周日）")
    ap.add_argument("--out", default="summary.json")
    ap.add_argument("--known-correction", action="append", default=[],
                    help="姓名=小时，总时长列含无打卡记录修正时经用户确认后传入")
    ap.add_argument("--double-group", default="26软件打卡")
    ap.add_argument("--double-range", default="20:00-23:00")
    a = ap.parse_args()
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    corrections = {}
    for kv in a.known_correction:
        k, v = kv.split("=")
        corrections[k] = float(v)
    ds, de = a.double_range.split("-")
    d_start = int(ds[:2]) * 60 + int(ds[3:])
    d_end = int(de[:2]) * 60 + int(de[3:])

    wb = load_workbook(a.xlsx, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    row1, row2 = rows[0], rows[1]
    header = [b if b is not None else x for x, b in zip(row1, row2)]
    c_name, c_group = header.index("姓名"), header.index("考勤组")
    c_s, c_t = header.index("实际出勤时长(小时)"), header.index("班内工作时长(小时)")
    date_cols = {}
    for i, h in enumerate(row2):
        if isinstance(h, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", h.strip()):
            date_cols[date.fromisoformat(h.strip())] = i
    window_dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    assert all(d in date_cols for d in window_dates), "窗口日期缺列"

    people, audit, validation = [], [], []
    for r in rows[2:]:
        if r[c_name] is None:
            continue
        name, group = str(r[c_name]).strip(), str(r[c_group]).strip()
        s_val, t_val = float(r[c_s]), float(r[c_t])
        assert s_val == t_val, f"{name} 实际出勤时长!=班内工作时长"
        daily_all, full_minutes = [], 0
        for d in sorted(date_cols):
            minutes, bonus, n_punch, trailing = day_minutes(r[date_cols[d]], d_start, d_end)
            full_minutes += minutes
            if trailing:
                audit.append({"name": name, "date": d.isoformat(), "punch_count": n_punch})
            daily_all.append((d, minutes, bonus))
        full_rounded = float(round1(full_minutes))
        expected = corrections.get(name, 0.0)
        diff = abs(full_rounded + expected - s_val)
        validation.append({"name": name, "S": s_val, "full_computed": full_rounded,
                           "known_correction": expected, "diff": round(diff, 4)})
        if diff > 0.05 + 1e-9:
            print(f"交叉验证失败: {name} S={s_val} 配对={full_rounded}(+{expected})；"
                  f"先向用户确认差异原因，必要时 --known-correction", file=sys.stderr)
            sys.exit(1)
        window = [(d, m, b) for d, m, b in daily_all if start <= d <= end]
        raw = sum(m for _, m, _ in window)
        bonus = sum(b for _, _, b in window) if group == a.double_group else 0
        total = raw + bonus
        people.append({
            "row": len(people) + 3, "name": name, "group": group,
            "daily": [{"date": d.strftime("%m-%d"), "weekday": WEEKDAY[d.weekday()],
                       "minutes": m, "hours_display": round1(m),
                       "bonus_minutes": b if group == a.double_group else 0,
                       "bonus_display": round1(b if group == a.double_group else 0)}
                      for d, m, b in window],
            "window_raw_minutes": raw, "window_bonus_minutes": bonus,
            "window_bonus": round1(bonus), "window_total_minutes": total,
            "window_total": round1(total), "zero_in_window": total == 0,
            "full_total": full_rounded,
        })
    assert people, "无数据行"
    json.dump({"window": {"start": a.start, "end": a.end}, "people": people,
               "audit_odd_punches": audit, "validation": validation},
              open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"OK {len(people)}人; max_diff={max(v['diff'] for v in validation)}; "
          f"双倍加成={[(p['name'], p['window_bonus']) for p in people if p['window_bonus_minutes'] > 0]}; "
          f"零工时={[p['name'] for p in people if p['zero_in_window']]}; 奇数卡审计={len(audit)}条")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)