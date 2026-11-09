#!/usr/bin/env python3
"""回读核验已发卡片：sender 为 bot、未撤回、body 含 expect 串。ids 与 manifest 按顺序无关，用 expect 匹配。"""
import argparse
import json
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sender-prefix", default="小云")
    a = ap.parse_args()
    ids = json.load(open(a.ids))
    entries = json.load(open(a.manifest))
    bad, checked = [], 0
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        r = subprocess.run(["lark-cli", "im", "+messages-mget", "--message-ids", ",".join(chunk),
                            "--as", "bot"], capture_output=True, text=True)
        msgs = json.loads(r.stdout)["data"]["messages"]
        for m in msgs:
            checked += 1
            body = m.get("content", "")
            hit = [e for e in entries if e.get("expect") and e["expect"] in body]
            if not (m["sender"]["name"].startswith(a.sender_prefix) and not m["deleted"]
                    and m["msg_type"] == "interactive" and hit):
                bad.append(m["message_id"])
    print(f"核验 {checked}/{len(ids)}; 异常={bad}")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()