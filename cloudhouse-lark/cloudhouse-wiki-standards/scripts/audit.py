#!/usr/bin/env python3
"""Read-only wiki audit: traverse nodes, measure doc bodies, classify pages.

Usage:
  python3 audit.py --space-id <SPACE_ID> --out manifest.tsv
  python3 audit.py --all-team --exclude-space-id <EXCLUDE_SPACE_ID> --out manifest.tsv
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys

LARK = os.environ.get("LARK_CLI", "lark-cli")
WIKI_LINK_RE = re.compile(r"/wiki/([A-Za-z0-9]+)")
PLACEHOLDER_MARKERS = (
    "在首页你可以对空间进行说明",
    "这里你可以描述知识空间建设的目标和意义",
)


def run(args, timeout=90):
    try:
        p = subprocess.run(
            [LARK] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    if p.returncode != 0:
        return None, (p.stderr or p.stdout or "").strip()[:500]
    try:
        return json.loads(p.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"invalid json: {exc}"


def jq_value(args):
    try:
        p = subprocess.run(
            [LARK] + args,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    if p.returncode != 0:
        return None, (p.stderr or p.stdout or "").strip()[:500]
    out = p.stdout.strip()
    if out == "null" or out == "":
        return None, "empty"
    return out, None


def list_spaces():
    data, err = run(["wiki", "+space-list", "--as", "user", "--format", "json"])
    if err:
        raise SystemExit(f"space-list failed: {err}")
    return {s["space_id"]: s for s in data.get("data", {}).get("spaces", [])}


def list_nodes(space_id, parent=""):
    args = [
        "wiki", "+node-list", "--space-id", space_id,
        "--as", "user", "--format", "json", "--page-all",
    ]
    if parent:
        args += ["--parent-node-token", parent]
    data, err = run(args)
    if err:
        raise RuntimeError(f"node-list {space_id}/{parent or 'root'} failed: {err}")
    return data.get("data", {}).get("nodes", [])


def traverse(space, nodes=None, parent="", depth=0, out=None):
    if out is None:
        out = []
    for node in nodes if nodes is not None else list_nodes(space, parent):
        item = dict(node)
        item["depth"] = depth
        item["space_id"] = space
        out.append(item)
        if node.get("has_child"):
            traverse(space, parent=node["node_token"], depth=depth + 1, out=out)
    return out


def doc_chars(node):
    token = node.get("obj_token")
    if node.get("obj_type") != "docx" or not token:
        return 0, None
    value, err = jq_value([
        "docs", "+fetch", "--doc", token, "--as", "user",
        "--doc-format", "markdown", "--format", "json",
        "--jq", ".data.document.content | length",
    ])
    if err:
        return None, err
    try:
        return int(value), None
    except ValueError:
        return None, f"unexpected length: {value[:80]}"


def doc_content(node):
    token = node.get("obj_token")
    if node.get("obj_type") != "docx" or not token:
        return ""
    value, err = jq_value([
        "docs", "+fetch", "--doc", token, "--as", "user",
        "--doc-format", "markdown", "--format", "json",
        "--jq", ".data.document.content",
    ])
    return value or "" if not err else ""


def text_without_markup(content):
    text = re.sub(r"<title>.*?</title>", " ", content, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_sentence(text):
    return bool(re.search(r"[。！？；.!?;]", text))


def classify(node, body_chars, content, descendants):
    title = node.get("title", "")
    obj_type = node.get("obj_type", "")
    if obj_type != "docx":
        return "content", "non_docx", "skip"
    if body_chars is None:
        return "unknown", "broken", "blocked"
    if any(marker in content for marker in PLACEHOLDER_MARKERS):
        return "home", "template", "overwrite"
    if body_chars <= 12:
        page_type = "directory" if node.get("has_child") else "content"
        if title == "首页":
            page_type = "home"
        return page_type, "blank", "overwrite"
    text = text_without_markup(content)
    if body_chars <= 160 and ("TBD" in content.upper() or (len(text) < 40 and not has_sentence(text))):
        page_type = "directory" if node.get("has_child") else "content"
        if title == "首页":
            page_type = "home"
        return page_type, "effectively_blank", "review"
    if title == "首页":
        return "home", "normal", "review"
    if node.get("has_child"):
        return "directory", "thin" if body_chars < 200 else "normal", "skip"
    if any(k in title for k in ("日志", "记录", "待处理")):
        return "record", "normal", "skip"
    return "content", "thin" if body_chars < 200 else "normal", "skip"


def index_status(node, content, all_nodes):
    if not content:
        return ""
    actual = set(WIKI_LINK_RE.findall(content))
    if node.get("title") == "首页":
        expected = {n["node_token"] for n in all_nodes if n.get("title") != "首页"}
    elif node.get("has_child"):
        expected = {
            n["node_token"] for n in all_nodes
            if node["node_token"] in n.get("_path", [])
            and n["node_token"] != node["node_token"]
        }
    else:
        return ""
    if actual == expected:
        return "ok"
    missing = expected - actual
    extra = actual - expected
    return f"outdated(missing={len(missing)},extra={len(extra)})"


def build_paths(nodes):
    by_token = {n["node_token"]: n for n in nodes}
    for n in nodes:
        path = []
        cur = n
        seen = set()
        while cur:
            path.append(cur["node_token"])
            parent = cur.get("parent_node_token")
            if not parent or parent in seen:
                break
            seen.add(parent)
            cur = by_token.get(parent)
        n["_path"] = path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space-id", action="append", default=[])
    ap.add_argument("--all-team", action="store_true")
    ap.add_argument("--exclude-space-id", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--check-index", action="store_true")
    args = ap.parse_args()

    spaces = list_spaces()
    if args.all_team:
        exclude = set(args.exclude_space_id)
        space_ids = [
            sid for sid, s in spaces.items()
            if sid not in exclude and "示例" not in s.get("name", "")
        ]
    else:
        space_ids = args.space_id
    if not space_ids:
        raise SystemExit("provide --space-id or --all-team")

    rows = []
    for sid in space_ids:
        space_name = spaces.get(sid, {}).get("name", sid)
        nodes = traverse(sid)
        build_paths(nodes)

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            char_results = list(pool.map(doc_chars, nodes))

        for node, (chars, err) in zip(nodes, char_results):
            content = doc_content(node) if args.check_index else ""
            page_type, status, action = classify(node, chars, content, nodes)
            rows.append({
                "space_id": sid,
                "space_name": space_name,
                "node_token": node["node_token"],
                "obj_token": node.get("obj_token", ""),
                "parent_node_token": node.get("parent_node_token", ""),
                "title": node.get("title", ""),
                "depth": node.get("depth", 0),
                "has_child": bool(node.get("has_child")),
                "obj_type": node.get("obj_type", ""),
                "body_chars": "" if chars is None else chars,
                "page_type": page_type,
                "status": status,
                "action": action,
                "description": "",
                "expected_rows": len([
                    n for n in nodes
                    if node["node_token"] in n.get("_path", [])
                    and n["node_token"] != node["node_token"]
                ]) if node.get("has_child") else 0,
                "expected_links": "",
                "index_status": index_status(node, content, nodes) if args.check_index else "",
                "revision_id": "",
                "history_anchor": "",
                "verified": "",
                "notes": err or "",
            })
        print(f"{space_name}: {len(nodes)} nodes", file=sys.stderr)

    fields = list(rows[0].keys()) if rows else []
    out_json = os.path.splitext(args.out)[0] + ".json"
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")
        for row in rows:
            f.write("\t".join(
                str(row.get(k, "")).replace("\t", " ").replace("\n", " ")
                for k in fields
            ) + "\n")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"spaces": spaces, "nodes": rows}, f, ensure_ascii=False, indent=2)
    print(f"wrote {args.out} and {out_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
