#!/usr/bin/env python3
"""Render Mermaid mindmap branch lines for a directory/home subtree.

The output is inserted into a template that already contains `mindmap` and
`root((...))`, so this script only emits indented child lines.

Usage:
  python3 render_mindmap.py --manifest manifest.json \
    --target-node <NODE_TOKEN> --out mindmap-branches.mmd
"""

import argparse
import json
import os
import sys


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


def path_of(node, by_token):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--target-node", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--all-non-home", action="store_true",
                    help="render every non-home node in the space (for space homepages)")
    args = ap.parse_args()

    data = load(args.manifest)
    nodes = data["nodes"] if isinstance(data, dict) else data
    by_token = {n["node_token"]: n for n in nodes}
    if args.target_node not in by_token:
        raise SystemExit(f"target node not found: {args.target_node}")
    target = by_token[args.target_node]

    if args.all_non_home:
        selected = [
            n for n in nodes
            if n.get("space_id") == target.get("space_id")
            and n["node_token"] != target["node_token"]
            and n.get("title") != "首页"
            and n.get("title", "").strip()
        ]
    else:
        selected = [
            n for n in nodes
            if target["node_token"] in path_of(n, by_token)
            and n["node_token"] != target["node_token"]
            and n.get("title", "").strip()
        ]

    lines = []
    for node in selected:
        if args.all_non_home:
            indent = 2 * (int(node["depth"]) + 2)
        else:
            indent = 2 * (int(node["depth"]) - int(target["depth"]) + 1)
        lines.append(" " * indent + sanitize(node["title"]))

    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {args.out}: {len(selected)} nodes", file=sys.stderr)


if __name__ == "__main__":
    main()
