#!/usr/bin/env python3
"""姓名→open_id：名册 ndjson（姓名字段全量读取，省略 --view-id）精确匹配；缺失/冲突列出待兜底。"""
import argparse
import json
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--roster", required=True, help="base +record-list 投影姓名字段的 ndjson")
    ap.add_argument("--out", default="mapping.json")
    a = ap.parse_args()
    names = [p["name"] for p in json.load(open(a.summary))["people"]]
    roster = {}
    for line in open(a.roster):
        line = line.strip()
        if not line:
            continue
        for u in json.loads(line).get("姓名") or []:
            roster.setdefault(u["name"], set()).add(u["id"])
    mapping, missing, conflicts = [], [], []
    for p in json.load(open(a.summary))["people"]:
        ids = roster.get(p["name"], set())
        if len(ids) == 1:
            oid = next(iter(ids))
            assert re.fullmatch(r"ou_[0-9a-f]{32}", oid), oid
            mapping.append({"row": p["row"], "name": p["name"], "open_id": oid, "source": "base"})
        elif ids:
            conflicts.append({"name": p["name"], "ids": sorted(ids)})
        else:
            missing.append(p["name"])
    json.dump({"mapping": mapping, "missing": missing, "conflicts": conflicts},
              open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"base命中 {len(mapping)}/{len(names)}; missing={missing}; conflicts={conflicts}")
    if missing or conflicts:
        print("用 contact +search-user --queries 兜底并按部门消歧；仍缺问用户，不擅自跳过", file=sys.stderr)


if __name__ == "__main__":
    main()