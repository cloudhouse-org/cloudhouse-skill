#!/usr/bin/env python3
"""Render index table rows from an audit manifest.

Directory mode (grouped by direct child, colored category column):
  python3 render_index.py --manifest manifest.json --target-node <NODE> \
    --mode directory --out index.xml

Home mode (optional explicit groups):
  python3 render_index.py --manifest manifest.json --target-node <HOME_NODE> \
    --mode home --groups groups.json --descriptions descriptions.json --out index.xml
"""

import argparse
import json
import sys
from html import escape

COLORS = ["light-blue", "light-orange", "light-green"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def valid(node):
    return bool(node.get("title", "").strip())


def link(node, base_url, prefix=""):
    title = escape(node["title"].strip())
    return f'{escape(prefix)}<a href="{base_url}{node["node_token"]}">{title}</a>'


def description(node, descriptions):
    if node["node_token"] in descriptions:
        return escape(descriptions[node["node_token"]])
    if node.get("has_child"):
        return "总入口"
    return f"查看{escape(node['title'].strip())}"


def directory_groups(target, nodes):
    children = [
        n for n in nodes
        if n.get("parent_node_token", "") == target["node_token"] and valid(n)
    ]
    groups = []
    for child in children:
        members = [child]
        for node in nodes:
            if node["node_token"] != child["node_token"] and valid(node) and child["node_token"] in path_of(node, nodes):
                members.append(node)
        groups.append({"title": child["title"], "tokens": [m["node_token"] for m in members]})
    return groups


def home_groups(nodes, home):
    children = [
        n for n in nodes
        if n.get("parent_node_token", "") == ""
        and n["node_token"] != home["node_token"] and valid(n)
    ]
    groups = []
    for child in children:
        members = [child]
        for node in nodes:
            if child["node_token"] in path_of(node, nodes) and valid(node):
                if node["node_token"] != child["node_token"]:
                    members.append(node)
        groups.append({"title": child["title"], "tokens": [m["node_token"] for m in members]})
    return groups


def path_of(node, nodes):
    by_token = {n["node_token"]: n for n in nodes}
    path = []
    cur = node
    seen = set()
    while cur:
        path.append(cur["node_token"])
        parent = cur.get("parent_node_token", "")
        if not parent or parent in seen:
            break
        seen.add(parent)
        cur = by_token.get(parent)
    return path


def three_col_rows(groups, nodes, descriptions, base_url):
    by_token = {n["node_token"]: n for n in nodes}
    rows = []
    for gi, group in enumerate(groups):
        missing = [t for t in group.get("tokens", []) if t not in by_token]
        if missing:
            raise SystemExit(f"group {group.get('title')!r} has unknown tokens: {missing}")
        tokens = [t for t in group.get("tokens", []) if t in by_token and valid(by_token[t])]
        if not tokens:
            continue
        color = COLORS[gi % len(COLORS)]
        min_depth = min(int(by_token[t]["depth"]) for t in tokens)
        for ri, token in enumerate(tokens):
            node = by_token[token]
            level = max(0, int(node["depth"]) - min_depth)
            prefix = "└ " * level if level else ""
            cells = []
            if ri == 0:
                cells.append(
                    f'<td rowspan="{len(tokens)}" background-color="{color}" '
                    f'vertical-align="middle"><p><b>{escape(group["title"])}</b></p></td>'
                )
            cells.append(f"<td><p>{link(node, base_url, prefix)}</p></td>")
            cells.append(f"<td><p>{description(node, descriptions)}</p></td>")
            rows.append("    <tr>" + "".join(cells) + "</tr>")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--target-node", required=True)
    ap.add_argument("--mode", choices=["directory", "home"], required=True)
    ap.add_argument("--groups", default="")
    ap.add_argument("--descriptions", default="")
    ap.add_argument("--base-url", default="https://jwo4yyi5n79.feishu.cn/wiki/")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = load(args.manifest)
    nodes = data["nodes"] if isinstance(data, dict) else data
    by_token = {n["node_token"]: n for n in nodes}
    if args.target_node not in by_token:
        raise SystemExit(f"target node not found: {args.target_node}")
    target = by_token[args.target_node]
    descriptions = load(args.descriptions) if args.descriptions else {}

    if args.mode == "directory":
        groups = directory_groups(target, nodes)
        rows = three_col_rows(groups, nodes, descriptions, args.base_url)
        if not rows:
            raise SystemExit("no descendants: use content-scaffold/record-page instead")
        count = len(rows)
    else:
        if args.groups:
            groups = load(args.groups)
        else:
            groups = home_groups(nodes, target)
        rows = three_col_rows(groups, nodes, descriptions, args.base_url)
        count = len(rows)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    print(f"wrote {args.out}: {count} rows, {len(rows)} tr", file=sys.stderr)


if __name__ == "__main__":
    main()
