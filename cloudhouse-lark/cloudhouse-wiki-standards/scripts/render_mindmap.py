#!/usr/bin/env python3
"""Render Mermaid mindmap branch lines for a directory/home subtree.

The output is inserted into a template that already contains `mindmap` and
`root((...))`, so this script only emits indented child lines.

Usage:
  python3 render_mindmap.py --manifest manifest.json \
    --target-node <NODE_TOKEN> --preset pure --out mindmap-branches.mmd

Presets (real wiki nodes; summary leaves are extra):
  home  40 nodes, 12 children per parent (space homepage)
  pure  50 nodes, 12 children per parent (pure index page)
  semi  30 nodes, 12 children per parent, max 3 levels (semi-index page)

When a branch exceeds the budget or child limit, a summary leaf is emitted:
  ……（其余 N 项见索引表）
"""

import argparse
import json
import os
import sys

ROOT = "__ROOT__"
PRESETS = {
    "home": {"max_nodes": 40, "max_children": 12, "max_depth": 0, "all_non_home": True},
    "pure": {"max_nodes": 50, "max_children": 12, "max_depth": 0, "all_non_home": False},
    "semi": {"max_nodes": 30, "max_children": 12, "max_depth": 3, "all_non_home": False},
}
DEFAULT_SUMMARY = "……（其余 {n} 项见索引表）"


def sanitize(title):
    """Keep Mermaid mindmap syntax safe without changing wiki node titles."""
    return (
        title.strip()
        .replace("&", "与")
        .replace("(", "（")
        .replace(")", "）")
        .replace('"', "”")
        .replace("[", "【")
        .replace("]", "】")
    )


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def children_map(nodes):
    children = {}
    for node in nodes:
        if node.get("title", "").strip():
            children.setdefault(node.get("parent_node_token", ""), []).append(node)
    return children


def descendant_count(token, children, cache):
    if token in cache:
        return cache[token]
    total = 0
    for child in children.get(token, []):
        total += 1 + descendant_count(child["node_token"], children, cache)
    cache[token] = total
    return total


def select_anchors(target, nodes, all_non_home):
    if all_non_home:
        return [
            n for n in nodes
            if n.get("space_id") == target.get("space_id")
            and n.get("node_token") != target.get("node_token")
            and n.get("title", "").strip()
            and n.get("parent_node_token", "") == ""
        ]
    return [
        n for n in nodes
        if n.get("parent_node_token", "") == target.get("node_token")
        and n.get("title", "").strip()
    ]


def prune(target, nodes, all_non_home, max_nodes, max_children, max_depth, summary_label):
    children = children_map(nodes)
    cache = {}
    anchors = select_anchors(target, nodes, all_non_home)
    total_named = sum(1 + descendant_count(a["node_token"], children, cache) for a in anchors)
    child_map = dict(children)
    child_map[ROOT] = anchors

    included = set()
    level = {}
    queue = [(ROOT, 0)]
    while queue:
        parent, parent_level = queue.pop(0)
        if parent == ROOT:
            kids = anchors
        else:
            if parent not in included:
                continue
            if max_depth and parent_level >= max_depth:
                continue
            kids = children.get(parent, [])
        unit = kids[:max_children] if max_children else kids
        if not unit:
            continue
        if max_nodes and len(included) + len(unit) > max_nodes:
            continue
        for child in unit:
            token = child["node_token"]
            if token in included:
                continue
            included.add(token)
            level[token] = parent_level + 1
            queue.append((token, parent_level + 1))

    omitted = {}
    for parent in [ROOT] + [n["node_token"] for n in nodes if n["node_token"] in included]:
        kids = child_map.get(parent, [])
        count = sum(
            1 + descendant_count(c["node_token"], children, cache)
            for c in kids
            if c["node_token"] not in included
        )
        if count:
            omitted[parent] = count

    emitted = []
    def emit(parent, child_level):
        kids = child_map.get(parent, [])
        for child in kids:
            if child["node_token"] not in included:
                continue
            emitted.append(" " * (2 * (child_level + 1)) + sanitize(child["title"]))
            emit(child["node_token"], child_level + 1)
        if parent in omitted:
            emitted.append(
                " " * (2 * (child_level + 1)) + summary_label.format(n=omitted[parent])
            )

    emit(ROOT, 1)

    real = len(included)
    summary = len(omitted)
    omitted_total = sum(omitted.values())
    invariant = real + omitted_total == total_named
    stats = {
        "real": real,
        "summaries": summary,
        "omitted": omitted_total,
        "total": real + summary + 1,
        "named": total_named,
        "invariant": invariant,
    }
    return emitted, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--target-node", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preset", choices=["home", "pure", "semi"], default="")
    ap.add_argument("--max-nodes", type=int, default=None,
                    help="real wiki node budget; 0 = unlimited")
    ap.add_argument("--max-children", type=int, default=None,
                    help="max children per parent; 0 = unlimited; default 12")
    ap.add_argument("--max-depth", type=int, default=None,
                    help="max levels below root; 0 = unlimited")
    ap.add_argument("--summary-label", default=DEFAULT_SUMMARY)
    ap.add_argument("--all-non-home", action="store_true",
                    help="compatibility alias for --preset home")
    args = ap.parse_args()

    data = load(args.manifest)
    nodes = data["nodes"] if isinstance(data, dict) else data
    by_token = {n["node_token"]: n for n in nodes}
    if args.target_node not in by_token:
        raise SystemExit(f"target node not found: {args.target_node}")
    target = by_token[args.target_node]

    preset = PRESETS.get(args.preset, {})
    all_non_home = bool(args.all_non_home or preset.get("all_non_home"))
    if args.all_non_home and args.preset and args.preset != "home":
        raise SystemExit("--all-non-home can only be combined with --preset home")

    max_nodes = args.max_nodes if args.max_nodes is not None else preset.get("max_nodes", 0)
    max_children = (
        args.max_children if args.max_children is not None
        else preset.get("max_children", 12)
    )
    max_depth = args.max_depth if args.max_depth is not None else preset.get("max_depth", 0)
    summary_label = sanitize(args.summary_label)

    lines, stats = prune(
        target, nodes, all_non_home, max_nodes, max_children, max_depth, summary_label
    )
    if not stats["invariant"]:
        print(f"invariant failed: {stats}", file=sys.stderr)
        raise SystemExit(1)

    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(
        "wrote {out}: real={real} summaries={summaries} omitted={omitted} "
        "total={total} named={named} invariant={invariant}".format(
            out=args.out, **stats
        ),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
